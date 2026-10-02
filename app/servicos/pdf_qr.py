"""Folha de QR Codes em PDF (RF08): uma atividade por página, em A4."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Frame, KeepInFrame, Paragraph

from .qr import gerar_imagem, url_publica
from .tempo import formatar_data, formatar_hora_extenso
from .validacao import slug

AZUL = HexColor("#1F4E79")
CINZA_TEXTO = HexColor("#2F3A45")
CINZA_APOIO = HexColor("#6B7785")

LARGURA, ALTURA = A4
MARGEM = 2 * cm
TAMANHO_QR = 12 * cm
ALTURA_RODAPE = 2.2 * cm  # link e identificação do campus, abaixo do QR

_ESTILOS = {
    "evento": ParagraphStyle("evento", fontName="Helvetica", fontSize=16, leading=20,
                             textColor=CINZA_APOIO, alignment=TA_CENTER, spaceAfter=10),
    "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=24, leading=29,
                             textColor=AZUL, alignment=TA_CENTER, spaceAfter=14),
    "info": ParagraphStyle("info", fontName="Helvetica", fontSize=14, leading=18,
                           textColor=CINZA_TEXTO, alignment=TA_CENTER, spaceAfter=4),
    "envolvidos": ParagraphStyle("envolvidos", fontName="Helvetica", fontSize=12,
                                 leading=15, textColor=CINZA_TEXTO, alignment=TA_CENTER,
                                 spaceBefore=8),
    "instrucao": ParagraphStyle("instrucao", fontName="Helvetica", fontSize=12, leading=15,
                                textColor=CINZA_TEXTO, alignment=TA_CENTER, spaceAfter=4),
    "rodape": ParagraphStyle("rodape", fontName="Helvetica", fontSize=9, leading=12,
                             textColor=CINZA_APOIO, alignment=TA_CENTER),
}


def textos_da_pagina(atividade):
    """Textos impressos na página da atividade, na ordem em que aparecem."""
    textos = {
        "evento": atividade.tipo_evento.nome,
        "titulo": atividade.titulo,
        "data": (f"{formatar_data(atividade.data)}, das "
                 f"{formatar_hora_extenso(atividade.hora_inicio)} às "
                 f"{formatar_hora_extenso(atividade.hora_fim)}"),
    }
    if atividade.local:
        textos["local"] = f"Local: {atividade.local}"
    if atividade.envolvidos:
        textos["envolvidos"] = f"Envolvidos: {atividade.envolvidos}"
    textos["instrucao"] = "Leia o QR Code com a câmera do celular para registrar sua presença."
    textos["url"] = url_publica(atividade)
    return textos


def _paragrafo(texto, estilo):
    # Escapa o texto (Paragraph interpreta marcação) e mantém as quebras de linha.
    return Paragraph(escape(texto).replace("\n", "<br/>"), _ESTILOS[estilo])


def _desenhar_pagina(canvas, atividade):
    textos = textos_da_pagina(atividade)
    topo_qr = MARGEM + ALTURA_RODAPE + TAMANHO_QR

    # Cabeçalho: ocupa o espaço acima do QR; textos longos são reduzidos para caber.
    blocos = [_paragrafo(textos["evento"], "evento"), _paragrafo(textos["titulo"], "titulo"),
              _paragrafo(textos["data"], "info")]
    if "local" in textos:
        blocos.append(_paragrafo(textos["local"], "info"))
    if "envolvidos" in textos:
        blocos.append(_paragrafo(textos["envolvidos"], "envolvidos"))
    altura_cabecalho = ALTURA - MARGEM - topo_qr - 0.5 * cm
    Frame(MARGEM, topo_qr + 0.5 * cm, LARGURA - 2 * MARGEM, altura_cabecalho,
          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0).addFromList(
        [KeepInFrame(LARGURA - 2 * MARGEM, altura_cabecalho, blocos, mode="shrink")],
        canvas)

    canvas.drawImage(ImageReader(gerar_imagem(atividade)), (LARGURA - TAMANHO_QR) / 2,
                     MARGEM + ALTURA_RODAPE, TAMANHO_QR, TAMANHO_QR)

    rodape = [_paragrafo(textos["instrucao"], "instrucao"), _paragrafo(textos["url"], "rodape"),
              _paragrafo("CEFET-MG Campus Varginha", "rodape")]
    Frame(MARGEM, MARGEM, LARGURA - 2 * MARGEM, ALTURA_RODAPE,
          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0).addFromList(
        [KeepInFrame(LARGURA - 2 * MARGEM, ALTURA_RODAPE, rodape, mode="shrink")], canvas)


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


def nome_arquivo(tipo_evento=None):
    """Ex.: qrcodes-35a-meta-2026.pdf; sem filtro de evento, qrcodes-atividades.pdf."""
    if tipo_evento is None:
        return "qrcodes-atividades.pdf"
    return f"qrcodes-{slug(tipo_evento.nome, 'evento')}.pdf"
