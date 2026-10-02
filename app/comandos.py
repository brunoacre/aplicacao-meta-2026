import sqlite3

import click
from sqlalchemy import inspect, text

from . import db
from .models import Administrador
from .servicos.validacao import SENHA_MINIMA, email_valido, normalizar_email


def registrar_comandos(app):
    @app.cli.command("criar-admin")
    @click.option("--nome", prompt="Nome")
    @click.option("--email", prompt="E-mail")
    @click.password_option(
        "--senha", prompt="Senha", confirmation_prompt="Repita a senha"
    )
    def criar_admin(nome, email, senha):
        """Cria um administrador."""
        nome = nome.strip()
        email = normalizar_email(email)
        if not nome:
            raise click.ClickException("Informe o nome.")
        if not email_valido(email):
            raise click.ClickException("E-mail inválido.")
        if len(senha) < SENHA_MINIMA:
            raise click.ClickException(
                f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres."
            )
        if db.session.execute(
            db.select(Administrador).filter_by(email=email)
        ).scalar_one_or_none():
            raise click.ClickException("Já existe um administrador com este e-mail.")

        admin = Administrador(nome=nome, email=email)
        admin.definir_senha(senha)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrador {email} criado.")

    @app.cli.command("atualizar-banco")
    def atualizar_banco():
        """Ajusta um banco criado por versão anterior (SPEC seção 11). Pode rodar de novo."""
        colunas = {c["name"] for c in inspect(db.engine).get_columns("atividade")}
        if "hora_fim" in colunas:
            # A3: a hora de término saiu do sistema. DROP COLUMN exige SQLite 3.35+.
            if sqlite3.sqlite_version_info < (3, 35):
                raise click.ClickException(
                    f"SQLite {sqlite3.sqlite_version} não remove colunas (exige 3.35 ou "
                    "mais novo). Use uma versão mais nova do Python no ambiente virtual.")
            with db.engine.begin() as conexao:
                conexao.execute(text("ALTER TABLE atividade DROP COLUMN hora_fim"))
            click.echo("Coluna hora_fim removida da tabela atividade.")
        else:
            click.echo("O banco já está atualizado.")
