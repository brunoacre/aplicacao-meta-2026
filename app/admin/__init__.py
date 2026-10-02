from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import cadastros, importacao, qr, relatorios, rotas  # noqa: E402,F401
