"""QR Code de cada atividade, apontando para o formulário público (RN08)."""
import qrcode
from flask import current_app, url_for
from qrcode.constants import ERROR_CORRECT_M


def url_publica(atividade):
    """Endereço absoluto do formulário da atividade, sempre pelo token público.

    Usa URL_PUBLICA quando configurada; atrás do proxy do PythonAnywhere o
    endereço da requisição pode sair com http em vez de https.
    """
    base = current_app.config.get("URL_PUBLICA")
    if base:
        return base.rstrip("/") + url_for("publico.presenca", token=atividade.token)
    return url_for("publico.presenca", token=atividade.token, _external=True)


def gerar_imagem(atividade, box_size=10):
    """Imagem PIL do QR Code. Correção de erro média: resiste a manchas na impressão."""
    codigo = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=box_size, border=4)
    codigo.add_data(url_publica(atividade))
    codigo.make(fit=True)
    return codigo.make_image(fill_color="black", back_color="white").get_image()

