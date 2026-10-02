from datetime import date, time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Atividade, CursoTurma, Resposta, TipoEvento
from app.servicos.tempo import fechamento_padrao


def test_pragmas_sqlite(app):
    with app.app_context():
        conexao = db.session.connection()
        assert conexao.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conexao.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def _nova_atividade(tipo, titulo="Palestra de abertura"):
    dia = date(2026, 10, 20)
    return Atividade(
        tipo_evento=tipo, titulo=titulo, modalidade="palestra", data=dia,
        hora_inicio=time(14, 0), fecha_em=fechamento_padrao(dia),
    )


def test_token_gerado_e_unico(app):
    with app.app_context():
        tipo = TipoEvento(nome="META")
        a1, a2 = _nova_atividade(tipo), _nova_atividade(tipo, "Outra")
        db.session.add_all([a1, a2])
        db.session.commit()
        assert len(a1.token) == 36
        assert a1.token != a2.token
        assert a1.fecha_em.hour == 23 and a1.fecha_em.minute == 59


def test_resposta_unica_por_matricula(app):
    with app.app_context():
        atividade = _nova_atividade(TipoEvento(nome="META"))
        curso = CursoTurma(nome="Informática 1A")
        db.session.add_all([atividade, curso])
        db.session.commit()

        def resposta():
            return Resposta(
                atividade=atividade, nome="Aluno", matricula="20261234",
                curso_turma=curso, email="aluno@exemplo.com", descricao="x",
            )

        db.session.add(resposta())
        db.session.commit()
        db.session.add(resposta())
        with pytest.raises(IntegrityError):
            db.session.commit()
