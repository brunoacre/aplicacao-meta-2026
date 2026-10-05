"""Tela de administradores (RF16): cadastrar, redefinir senha e desativar."""
import pytest

from app import db
from app.models import Administrador


def _texto(resposta):
    return resposta.get_data(as_text=True)


def _admin(app, email):
    with app.app_context():
        return db.session.execute(
            db.select(Administrador).filter_by(email=email)).scalar_one_or_none()


def _id(app, email):
    return _admin(app, email).id


def _cadastrar(cliente, **extra):
    dados = {"nome": "Ana Souza", "email": " Ana@CEFETMG.br ",
             "senha": "senha-da-ana", "confirmacao": "senha-da-ana"}
    dados.update(extra)
    return cliente.post("/admin/administradores/novo", data=dados, follow_redirects=True)


@pytest.mark.parametrize("url, metodo", [
    ("/admin/administradores", "get"),
    ("/admin/administradores/novo", "get"),
    ("/admin/administradores/1/senha", "get"),
    ("/admin/administradores/1/alternar", "post"),
])
def test_rotas_exigem_login(client, url, metodo):
    resposta = getattr(client, metodo)(url)
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]


def test_menu_e_listagem(cliente_logado):
    texto = _texto(cliente_logado.get("/admin/administradores"))
    assert 'href="/admin/administradores"' in texto
    assert "admin@cefetmg.br" in texto
    assert "(você)" in texto
    assert "Cadastrar administrador" in texto


def test_cadastrar_administrador(app, cliente_logado):
    texto = _texto(_cadastrar(cliente_logado))
    assert "Administrador ana@cefetmg.br cadastrado." in texto
    admin = _admin(app, "ana@cefetmg.br")
    assert admin.nome == "Ana Souza" and admin.ativo
    assert admin.verificar_senha("senha-da-ana")


def test_novo_administrador_consegue_entrar(app, cliente_logado):
    _cadastrar(cliente_logado)
    novo = app.test_client()
    novo.post("/admin/login", data={"email": "ana@cefetmg.br", "senha": "senha-da-ana"})
    assert novo.get("/admin/").status_code == 200


@pytest.mark.parametrize("extra, mensagem", [
    ({"email": "admin@cefetmg.br"}, "Já existe um administrador com este e-mail."),
    ({"email": "ana-sem-arroba"}, "E-mail inválido."),
    ({"senha": "curta", "confirmacao": "curta"}, "A senha deve ter pelo menos 8 caracteres."),
    ({"confirmacao": "outra-senha"}, "As senhas não conferem."),
    ({"nome": ""}, "Informe o nome."),
])
def test_cadastro_invalido(app, cliente_logado, extra, mensagem):
    assert mensagem in _texto(_cadastrar(cliente_logado, **extra))
    with app.app_context():
        assert db.session.query(Administrador).count() == 1


def test_redefinir_senha(app, cliente_logado):
    _cadastrar(cliente_logado)
    id_ = _id(app, "ana@cefetmg.br")
    texto = _texto(cliente_logado.post(
        f"/admin/administradores/{id_}/senha",
        data={"senha": "nova-senha-1", "confirmacao": "nova-senha-1"},
        follow_redirects=True))
    assert "Senha de ana@cefetmg.br redefinida." in texto
    admin = _admin(app, "ana@cefetmg.br")
    assert admin.verificar_senha("nova-senha-1")
    assert not admin.verificar_senha("senha-da-ana")


@pytest.mark.parametrize("senha, confirmacao, mensagem", [
    ("curta", "curta", "A senha deve ter pelo menos 8 caracteres."),
    ("nova-senha-1", "nova-senha-2", "As senhas não conferem."),
])
def test_redefinir_senha_invalida(app, cliente_logado, senha, confirmacao, mensagem):
    id_ = _id(app, "admin@cefetmg.br")
    texto = _texto(cliente_logado.post(f"/admin/administradores/{id_}/senha",
                                       data={"senha": senha, "confirmacao": confirmacao}))
    assert mensagem in texto
    assert _admin(app, "admin@cefetmg.br").verificar_senha("senha-segura")


def test_redefinir_senha_de_inexistente(cliente_logado):
    assert cliente_logado.get("/admin/administradores/999/senha").status_code == 404


def test_desativar_e_reativar(app, cliente_logado):
    _cadastrar(cliente_logado)
    id_ = _id(app, "ana@cefetmg.br")
    texto = _texto(cliente_logado.post(f"/admin/administradores/{id_}/alternar",
                                       follow_redirects=True))
    assert "Administrador desativado." in texto
    assert _admin(app, "ana@cefetmg.br").ativo is False
    cliente_logado.post(f"/admin/administradores/{id_}/alternar")
    assert _admin(app, "ana@cefetmg.br").ativo is True


def test_nao_pode_desativar_a_si_mesmo(app, cliente_logado):
    id_ = _id(app, "admin@cefetmg.br")
    texto = _texto(cliente_logado.post(f"/admin/administradores/{id_}/alternar",
                                       follow_redirects=True))
    assert "Você não pode desativar a si mesmo." in texto
    assert _admin(app, "admin@cefetmg.br").ativo is True


def test_desativado_perde_o_acesso_na_hora(app, cliente_logado):
    # Ana entra; depois o admin a desativa e a sessão dela deixa de valer.
    _cadastrar(cliente_logado)
    ana = app.test_client()
    ana.post("/admin/login", data={"email": "ana@cefetmg.br", "senha": "senha-da-ana"})
    assert ana.get("/admin/").status_code == 200
    cliente_logado.post(f"/admin/administradores/{_id(app, 'ana@cefetmg.br')}/alternar")
    resposta = ana.get("/admin/")
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]
