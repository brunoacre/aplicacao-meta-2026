from app import db
from app.models import Administrador


def _entrar(client, email="admin@cefetmg.br", senha="senha-segura", **kwargs):
    return client.post(
        "/admin/login", data={"email": email, "senha": senha}, **kwargs
    )


# --- comando criar-admin ---------------------------------------------------

def test_criar_admin(app):
    runner = app.test_cli_runner()
    resultado = runner.invoke(
        args=["criar-admin", "--nome", "Maria", "--email", " Maria@CEFETMG.br ",
              "--senha", "senha-segura"]
    )
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        admin = db.session.execute(db.select(Administrador)).scalar_one()
        assert admin.email == "maria@cefetmg.br"
        assert admin.senha_hash != "senha-segura"
        assert admin.verificar_senha("senha-segura")


def test_criar_admin_recusa_email_duplicado(app, criar_admin):
    criar_admin()
    resultado = app.test_cli_runner().invoke(
        args=["criar-admin", "--nome", "Outro", "--email", "admin@cefetmg.br",
              "--senha", "senha-segura"]
    )
    assert resultado.exit_code != 0
    assert "Já existe" in resultado.output


def test_criar_admin_recusa_senha_curta(app):
    resultado = app.test_cli_runner().invoke(
        args=["criar-admin", "--nome", "Ana", "--email", "ana@cefetmg.br",
              "--senha", "curta"]
    )
    assert resultado.exit_code != 0


# --- login e logout --------------------------------------------------------

def test_admin_exige_login(client):
    resposta = client.get("/admin/")
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]


def test_login_com_sucesso(client, criar_admin):
    criar_admin()
    resposta = _entrar(client, email="ADMIN@cefetmg.br", follow_redirects=True)
    assert resposta.status_code == 200
    assert "Olá, Admin Teste" in resposta.get_data(as_text=True)


def test_login_senha_errada(client, criar_admin):
    criar_admin()
    resposta = _entrar(client, senha="errada")
    assert "E-mail ou senha inválidos." in resposta.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302


def test_login_admin_inativo(client, criar_admin):
    criar_admin(ativo=False)
    resposta = _entrar(client)
    assert "E-mail ou senha inválidos." in resposta.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302


def test_login_redireciona_para_next_interno(client, criar_admin):
    criar_admin()
    resposta = client.post(
        "/admin/login?next=/admin/",
        data={"email": "admin@cefetmg.br", "senha": "senha-segura"},
    )
    assert resposta.headers["Location"] == "/admin/"


def test_login_ignora_next_externo(client, criar_admin):
    criar_admin()
    for destino in ["https://malicioso.com", "//malicioso.com", "/\\malicioso.com"]:
        resposta = client.post(
            f"/admin/login?next={destino}",
            data={"email": "admin@cefetmg.br", "senha": "senha-segura"},
        )
        assert resposta.headers["Location"] in ("/admin/", "http://localhost/admin/")
        client.post("/admin/sair")


def test_logout(client, criar_admin):
    criar_admin()
    _entrar(client)
    assert client.get("/admin/").status_code == 200
    resposta = client.post("/admin/sair", follow_redirects=True)
    assert "Você saiu do sistema." in resposta.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302


def test_logout_nao_aceita_get(client, criar_admin):
    criar_admin()
    _entrar(client)
    assert client.get("/admin/sair").status_code == 405
