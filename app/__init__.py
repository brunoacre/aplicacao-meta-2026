import os
import secrets
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import event
from sqlalchemy.engine import Engine

PASTA_PROJETO = Path(__file__).resolve().parent.parent

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _configurar_sqlite(conexao_dbapi, _registro):
    """Ativa WAL e busy_timeout em cada nova conexão SQLite (SPEC seção 1)."""
    if conexao_dbapi.__class__.__module__.startswith("sqlite3"):
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def carregar_chave_secreta(pasta):
    """Chave guardada em <pasta>/secret_key, criada na primeira execução.

    Usada quando a variável SECRET_KEY não está definida. A criação com "x"
    evita que dois web workers gravem chaves diferentes ao mesmo tempo.
    """
    arquivo = Path(pasta) / "secret_key"
    try:
        with open(arquivo, "x", encoding="utf-8") as saida:
            saida.write(secrets.token_hex(32))
        arquivo.chmod(0o600)
    except FileExistsError:
        pass
    chave = arquivo.read_text(encoding="utf-8").strip()
    if not chave:
        raise RuntimeError(f"Arquivo de chave vazio: {arquivo}. Apague-o e reinicie.")
    return chave


class Config:
    # Sem a variável, a chave é gerada e guardada em instance/secret_key.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.environ.get(
        "EVENTOS_DB", str(PASTA_PROJETO / "instance" / "eventos.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Endereço público usado nos QR Codes (ex.: https://usuario.pythonanywhere.com).
    # Sem ele, usa o endereço da requisição, que atrás do proxy pode sair como http.
    URL_PUBLICA = os.environ.get("URL_PUBLICA", "")
    # RN06: número mínimo de caracteres da descrição no formulário do aluno.
    MIN_CARACTERES_DESCRICAO = 100
    MAX_CARACTERES_DESCRICAO = 2000
    # O aluno pode abrir o formulário no início de uma atividade longa e enviar
    # horas depois: o token CSRF vale enquanto durar a sessão do navegador.
    WTF_CSRF_TIME_LIMIT = None
    # Tamanho máximo do envio (planilha de importação).
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    # Planilhas aguardando confirmação da importação (padrão: instance/importacoes).
    PASTA_IMPORTACOES = None


def create_app(config=None):
    app = Flask(__name__, instance_path=str(PASTA_PROJETO / "instance"))
    # PythonAnywhere fica atrás de um proxy: IP real do aluno vem em X-Forwarded-For (RN09).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = carregar_chave_secreta(app.instance_path)
    if app.config["URL_PUBLICA"].lower().startswith("https://"):
        # Site só em https: o navegador não envia os cookies por http.
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["REMEMBER_COOKIE_SECURE"] = True
    if not app.config["PASTA_IMPORTACOES"]:
        app.config["PASTA_IMPORTACOES"] = str(Path(app.instance_path) / "importacoes")

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    from . import models  # noqa: F401  (registra os modelos)
    from .admin import bp as admin_bp
    from .publico import bp as publico_bp
    from .comandos import registrar_comandos

    app.register_blueprint(admin_bp)
    app.register_blueprint(publico_bp)
    registrar_comandos(app)

    from .servicos.tempo import (
        formatar_data, formatar_data_hora, formatar_hora, formatar_hora_extenso,
    )
    app.jinja_env.filters.update(
        data=formatar_data, hora=formatar_hora, data_hora=formatar_data_hora,
        hora_h=formatar_hora_extenso,
    )

    with app.app_context():
        db.create_all()

    return app
