import re
from datetime import date, time
from io import BytesIO

import pytest
from PIL import Image

from app import db
from app.models import Atividade, TipoEvento
from app.servicos import pdf_qr, qr
from app.servicos.tempo import fechamento_padrao


def _criar(app, nome_evento="35ª META 2026", titulo="Palestra", dia=date(2026, 10, 20),
           modalidade="palestra", local="Sala 12", envolvidos="Fulano, Beltrana"):
    with app.app_context():
        tipo = db.session.execute(
            db.select(TipoEvento).filter_by(nome=nome_evento)).scalar_one_or_none()
        tipo = tipo or TipoEvento(nome=nome_evento)
        atividade = Atividade(
            tipo_evento=tipo, titulo=titulo, modalidade=modalidade, data=dia,
            hora_inicio=time(14), hora_fim=time(14, 20), local=local,
            envolvidos=envolvidos, fecha_em=fechamento_padrao(dia))
        db.session.add(atividade)
        db.session.commit()
        return atividade.id, tipo.id


def _paginas(pdf_bytes):
    return len(re.findall(rb"/Type /Page\b(?!s)", pdf_bytes))


# --- acesso ------------------------------------------------------------------

@pytest.mark.parametrize("url", ["/admin/atividades/1/qrcode.png", "/admin/atividades/qrcodes.pdf"])
def test_rotas_exigem_login(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]


# --- endereço do QR Code -----------------------------------------------------

def test_url_publica_usa_token_e_configuracao(app):
    id_, _ = _criar(app)
    app.config["URL_PUBLICA"] = "https://meta.exemplo.br/"
    with app.test_request_context():
        atividade = db.session.get(Atividade, id_)
        assert qr.url_publica(atividade) == (
            f"https://meta.exemplo.br/presenca/{atividade.token}")


def test_url_publica_sem_configuracao_usa_a_requisicao(app):
    id_, _ = _criar(app)
    with app.test_request_context(base_url="https://servidor.br"):
        atividade = db.session.get(Atividade, id_)
        assert qr.url_publica(atividade) == f"https://servidor.br/presenca/{atividade.token}"
        assert f"/{atividade.id}" not in qr.url_publica(atividade).split("/presenca")[1]


# --- QR Code individual ------------------------------------------------------

def test_baixar_png(app, cliente_logado):
    id_, _ = _criar(app)
    resposta = cliente_logado.get(f"/admin/atividades/{id_}/qrcode.png")
    assert resposta.status_code == 200
    assert resposta.mimetype == "image/png"
    assert f"qrcode-atividade-{id_}.png" in resposta.headers["Content-Disposition"]
    imagem = Image.open(BytesIO(resposta.data))
    assert imagem.format == "PNG"
    assert imagem.width == imagem.height >= 250


def test_png_de_atividade_inexistente(cliente_logado):
    assert cliente_logado.get("/admin/atividades/999/qrcode.png").status_code == 404


# --- PDF ---------------------------------------------------------------------

def test_textos_da_pagina(app):
    id_, _ = _criar(app, titulo="Ecoara", envolvidos="Fulano, Beltrana")
    app.config["URL_PUBLICA"] = "https://meta.exemplo.br"
    with app.test_request_context():
        atividade = db.session.get(Atividade, id_)
        textos = pdf_qr.textos_da_pagina(atividade)
        assert textos["evento"] == "35ª META 2026"
        assert textos["titulo"] == "Ecoara"
        assert textos["data"] == "20/10/2026, das 14h00 às 14h20"
        assert textos["local"] == "Local: Sala 12"
        assert textos["envolvidos"] == "Envolvidos: Fulano, Beltrana"
        assert textos["url"] == f"https://meta.exemplo.br/presenca/{atividade.token}"


def test_textos_sem_local_e_envolvidos(app):
    id_, _ = _criar(app, local="", envolvidos="")
    with app.test_request_context():
        textos = pdf_qr.textos_da_pagina(db.session.get(Atividade, id_))
        assert "local" not in textos and "envolvidos" not in textos


def test_pdf_uma_pagina_por_atividade_do_evento(app, cliente_logado):
    _, tipo_id = _criar(app, titulo="A")
    _criar(app, titulo="B")
    _criar(app, titulo="C", envolvidos="Pessoa, " * 300)  # texto longo não quebra o PDF
    _criar(app, nome_evento="Semana C&T 2026", titulo="Outra")
    resposta = cliente_logado.get(f"/admin/atividades/qrcodes.pdf?tipo_evento={tipo_id}")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/pdf"
    assert resposta.data.startswith(b"%PDF")
    assert _paginas(resposta.data) == 3
    assert "qrcodes-35a-meta-2026.pdf" in resposta.headers["Content-Disposition"]


def test_pdf_respeita_filtros_de_data_e_modalidade(app, cliente_logado):
    _criar(app, titulo="A", dia=date(2026, 10, 20))
    _criar(app, titulo="B", dia=date(2026, 10, 21))
    _criar(app, titulo="C", dia=date(2026, 10, 21), modalidade="minicurso")
    resposta = cliente_logado.get(
        "/admin/atividades/qrcodes.pdf?data=2026-10-21&modalidade=palestra")
    assert _paginas(resposta.data) == 1
    assert "qrcodes-atividades.pdf" in resposta.headers["Content-Disposition"]
    assert _paginas(cliente_logado.get("/admin/atividades/qrcodes.pdf").data) == 3


def test_pdf_sem_atividades(cliente_logado):
    resposta = cliente_logado.get("/admin/atividades/qrcodes.pdf?modalidade=outra",
                                  follow_redirects=True)
    assert "Nenhuma atividade encontrada para gerar o PDF." in resposta.get_data(as_text=True)


@pytest.mark.parametrize("nome, arquivo", [
    ("35ª META 2026", "qrcodes-35a-meta-2026.pdf"),
    ("Semana C&T – Ciência", "qrcodes-semana-c-t-ciencia.pdf"),
    ("***", "qrcodes-evento.pdf"),
])
def test_nome_do_arquivo(nome, arquivo):
    assert pdf_qr.nome_arquivo(TipoEvento(nome=nome)) == arquivo


def test_listagens_mostram_os_botoes(app, cliente_logado):
    id_, tipo_id = _criar(app)
    texto = cliente_logado.get("/admin/atividades").get_data(as_text=True)
    assert f"/admin/atividades/{id_}/qrcode.png" in texto
    assert "Gerar PDF dos QR Codes" in texto
    texto = cliente_logado.get("/admin/tipos-evento").get_data(as_text=True)
    assert f"/admin/atividades/qrcodes.pdf?tipo_evento={tipo_id}" in texto
