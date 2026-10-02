import pytest

from app import carregar_chave_secreta, create_app


def test_chave_secreta_criada_e_reutilizada(tmp_path):
    chave = carregar_chave_secreta(tmp_path)
    assert len(chave) == 64
    assert (tmp_path / "secret_key").read_text().strip() == chave
    assert carregar_chave_secreta(tmp_path) == chave


def test_chave_secreta_vazia_gera_erro(tmp_path):
    (tmp_path / "secret_key").write_text("")
    with pytest.raises(RuntimeError):
        carregar_chave_secreta(tmp_path)


def _app(tmp_path, **extra):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "teste",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'teste.db'}",
        "PASTA_IMPORTACOES": str(tmp_path / "importacoes"),
        **extra,
    })


def test_cookies_seguros_com_url_publica_https(tmp_path):
    app = _app(tmp_path, URL_PUBLICA="https://eventos.pythonanywhere.com")
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True


def test_cookies_comuns_sem_url_publica(tmp_path):
    app = _app(tmp_path, URL_PUBLICA="")
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert not app.config.get("REMEMBER_COOKIE_SECURE")
