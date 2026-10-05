"""PDF de QR Codes (RF07 e RF08): uma atividade por página, em A4."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import KeepInFrame, Paragraph

from .qr import gerar_imagem
from .tempo import formatar_data
from .validacao import slug

AZUL = HexColor("#1F4E79")
CINZA_TEXTO = HexColor("#2F3A45")
CINZA_APOIO = HexColor("#6B7785")

LARGURA, ALTURA = A4
MARGEM = 2 * cm
ALTURA_MAXIMA_TEXTO = 8 * cm  # evento, título e data, acima do QR
ESPACO = 1 * cm  # entre a data e o QR
TAMANHO_QR = 15 * cm

_ESTILOS = {
    "evento": ParagraphStyle("evento", fontName="Helvetica", fontSize=18, leading=22,
                             textColor=CINZA_APOIO, alignment=TA_CENTER, spaceAfter=12),
    "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=26, leading=31,
                             textColor=AZUL, alignment=TA_CENTER, spaceAfter=14),
    "data": ParagraphStyle("data", fontName="Helvetica", fontSize=18, leading=22,
                           textColor=CINZA_TEXTO, alignment=TA_CENTER),
}


def textos_da_pagina(atividade):
    """Textos impressos acima do QR Code (RF08), na ordem em que aparecem."""
    return {
        "evento": atividade.tipo_evento.nome,
        "titulo": atividade.titulo,
        "data": formatar_data(atividade.data),
    }


def _paragrafo(texto, estilo):
    # Escapa o texto (Paragraph interpreta marcação) e mantém as quebras de linha.
    return Paragraph(escape(texto).replace("\n", "<br/>"), _ESTILOS[estilo])


def _desenhar_pagina(canvas, atividade):
    # Textos e QR formam um bloco centralizado na página; títulos longos são
    # reduzidos para caber em ALTURA_MAXIMA_TEXTO.
    largura = LARGURA - 2 * MARGEM
    blocos = [_paragrafo(texto, estilo) for estilo, texto in textos_da_pagina(atividade).items()]
    cabecalho = KeepInFrame(largura, ALTURA_MAXIMA_TEXTO, blocos, mode="shrink")
    _, altura_texto = cabecalho.wrapOn(canvas, largura, ALTURA_MAXIMA_TEXTO)

    topo = (ALTURA + altura_texto + ESPACO + TAMANHO_QR) / 2
    cabecalho.drawOn(canvas, MARGEM, topo - altura_texto)
    canvas.drawImage(ImageReader(gerar_imagem(atividade)), (LARGURA - TAMANHO_QR) / 2,
                     topo - altura_texto - ESPACO - TAMANHO_QR, TAMANHO_QR, TAMANHO_QR)


def gerar_pdf(atividades):
    """PDF com uma página por atividade (na ordem recebida)."""
    saida = BytesIO()
    canvas = Canvas(saida, pagesize=A4)
    canvas.setTitle("QR Codes das atividades")
    canvas.setAuthor("CEFET-MG Campus Varginha")
    for atividade in atividades:
        _desenhar_pagina(canvas, atividade)
        canvas.showPage()
    canvas.save()
    saida.seek(0)
    return saida


def nome_arquivo_atividade(atividade):
    """Ex.: qrcode-palestra-de-abertura.pdf (título limitado a 60 caracteres)."""
    return f"qrcode-{slug(atividade.titulo, 'atividade')[:60].strip('-')}.pdf"


def nome_arquivo(tipo_evento=None):
    """Ex.: qrcodes-35a-meta-2026.pdf; sem filtro de evento, qrcodes-atividades.pdf."""
    if tipo_evento is None:
        return "qrcodes-atividades.pdf"
    return f"qrcodes-{slug(tipo_evento.nome, 'evento')}.pdf"
