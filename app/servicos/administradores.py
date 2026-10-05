"""Gestão de administradores (SPEC seção 2 e RF16): cadastro, senha e desativação.

Usado pela tela de administradores e pelo comando `flask criar-admin`.
Não há exclusão: o administrador é apenas desativado.
"""
from .. import db
from ..models import Administrador
from .cadastros import alternar_ativo
from .validacao import SENHA_MINIMA, email_valido, normalizar_email


class ErroAdministrador(Exception):
    """Dado inválido; `campo` indica onde mostrar a mensagem no formulário."""

    def __init__(self, campo, mensagem):
        super().__init__(mensagem)
        self.campo = campo
        self.mensagem = mensagem


def listar():
    return db.session.execute(
        db.select(Administrador).order_by(Administrador.nome, Administrador.email)
    ).scalars().all()


def _validar_senha(senha):
    if len(senha or "") < SENHA_MINIMA:
        raise ErroAdministrador(
            "senha", f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres.")


def criar(nome, email, senha):
    """Cadastra um administrador ativo. Levanta ErroAdministrador se algo for inválido."""
    nome = (nome or "").strip()
    email = normalizar_email(email)
    if not nome:
        raise ErroAdministrador("nome", "Informe o nome.")
    if not email_valido(email):
        raise ErroAdministrador("email", "E-mail inválido.")
    _validar_senha(senha)
    if db.session.execute(
        db.select(Administrador.id).filter_by(email=email)
    ).first() is not None:
        raise ErroAdministrador("email", "Já existe um administrador com este e-mail.")

    admin = Administrador(nome=nome, email=email)
    admin.definir_senha(senha)
    db.session.add(admin)
    db.session.commit()
    return admin


def redefinir_senha(admin, senha):
    _validar_senha(senha)
    admin.definir_senha(senha)
    db.session.commit()


def alternar(admin, atual):
    """Desativa ou reativa `admin`. Quem está logado não pode desativar a si mesmo,
    o que garante que sempre reste ao menos um administrador ativo."""
    if admin.id == atual.id and admin.ativo:
        raise ErroAdministrador("ativo", "Você não pode desativar a si mesmo.")
    alternar_ativo(admin)
