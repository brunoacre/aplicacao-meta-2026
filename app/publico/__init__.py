from flask import Blueprint

# Formulário do aluno em /presenca/<token>.
bp = Blueprint("publico", __name__)

from . import rotas  # noqa: E402,F401
