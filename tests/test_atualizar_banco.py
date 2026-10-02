"""Comando atualizar-banco: ajusta bancos criados por versões anteriores (SPEC seção 11)."""
from datetime import date, datetime, time

from sqlalchemy import inspect, text

from app import db
from app.models import Atividade, TipoEvento


def _colunas_atividade(app):
    with app.app_context():
        return {c["name"] for c in inspect(db.engine).get_columns("atividade")}


def _banco_da_versao_anterior(app):
    """Banco com a coluna hora_fim obrigatória e uma atividade gravada."""
    with app.app_context():
        with db.engine.begin() as conexao:
            conexao.execute(text(
                "ALTER TABLE atividade ADD COLUMN hora_fim TIME NOT NULL DEFAULT '15:00:00'"))
        db.session.add(Atividade(
            tipo_evento=TipoEvento(nome="35ª META 2026"), titulo="Palestra",
            modalidade="palestra", data=date(2026, 10, 20), hora_inicio=time(14),
            fecha_em=datetime(2026, 10, 20, 23, 59)))
        db.session.commit()


def test_remove_hora_fim_e_mantem_atividades(app):
    _banco_da_versao_anterior(app)
    resultado = app.test_cli_runner().invoke(args=["atualizar-banco"])
    assert resultado.exit_code == 0, resultado.output
    assert "Coluna hora_fim removida" in resultado.output
    assert "hora_fim" not in _colunas_atividade(app)
    with app.app_context():
        assert db.session.execute(db.select(Atividade)).scalar_one().titulo == "Palestra"


def test_pode_rodar_de_novo(app):
    _banco_da_versao_anterior(app)
    runner = app.test_cli_runner()
    runner.invoke(args=["atualizar-banco"])
    resultado = runner.invoke(args=["atualizar-banco"])
    assert resultado.exit_code == 0, resultado.output
    assert "O banco já está atualizado." in resultado.output
