import pytest

from app import create_app, db
from app.models import Administrador


@pytest.fixture
def app(tmp_path):
    # Arquivo em disco (e não :memory:) para que o modo WAL seja aplicado.
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "teste",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'teste.db'}",
        "PASTA_IMPORTACOES": str(tmp_path / "importacoes"),
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def criar_admin(app):
    def _criar(email="admin@cefetmg.br", senha="senha-segura", ativo=True):
        with app.app_context():
            admin = Administrador(nome="Admin Teste", email=email, ativo=ativo)
            admin.definir_senha(senha)
            db.session.add(admin)
            db.session.commit()
    return _criar


@pytest.fixture
def cliente_logado(client, criar_admin):
    criar_admin()
    client.post("/admin/login", data={"email": "admin@cefetmg.br", "senha": "senha-segura"})
    return client
