"""Regras do formulário de presença do aluno (RN01–RN06, RN09).

A rota pública faz no máximo duas consultas (atividade e cursos/turmas ativos),
mais o INSERT da resposta (SPEC seção 8).
"""
import re
from datetime import datetime, time, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .. import db
from ..models import Atividade, CursoTurma, Resposta

NAO_ABERTO = "nao_aberto"
ABERTO = "aberto"
ENCERRADO = "encerrado"

REGISTRADA = "registrada"
DUPLICADA = "duplicada"
FORA_DA_JANELA = "fora_da_janela"

# Espaços, pontos e traços (incluindo os traços tipográficos que o celular insere).
_SEPARADORES_MATRICULA = re.compile(r"[\s.\-‐-―]+")


def normalizar_matricula(texto):
    """RN05: remove espaços, pontos e traços."""
    return _SEPARADORES_MATRICULA.sub("", texto or "")


def abertura(atividade):
    """RN01: o formulário abre à 00h00 da data da atividade."""
    return datetime.combine(atividade.data, time.min)


def situacao_janela(atividade, momento):
    """RN01–RN03: situação do formulário no momento dado (hora local, sem fuso)."""
    if momento < abertura(atividade):
        return NAO_ABERTO
    # "Fecha às 23h59" vale até o fim desse minuto (23:59:59).
    limite = atividade.fecha_em.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if momento >= limite:
        return ENCERRADO
    return ABERTO


def carregar_atividade(token):
    """Atividade pelo token público (RN08), com o tipo de evento, numa só consulta.

    Os objetos são desanexados da sessão: são só leitura aqui, e assim o commit
    da resposta não os expira (o que causaria novas consultas ao exibir a página).
    """
    atividade = db.session.execute(
        db.select(Atividade)
        .options(joinedload(Atividade.tipo_evento))
        .filter_by(token=token)
    ).scalar_one_or_none()
    if atividade is not None:
        db.session.expunge(atividade.tipo_evento)
        db.session.expunge(atividade)
    return atividade


def cursos_ativos():
    """Lista (id, nome) dos cursos/turmas exibidos no formulário."""
    return db.session.execute(
        db.select(CursoTurma.id, CursoTurma.nome)
        .filter_by(ativo=True)
        .order_by(CursoTurma.nome)
    ).all()


def registrar_presenca(atividade, nome, matricula, curso_turma_id, email, descricao,
                       ip, momento):
    """Grava a resposta. Retorna REGISTRADA, DUPLICADA ou FORA_DA_JANELA."""
    # RN03: a janela é conferida de novo no envio.
    if situacao_janela(atividade, momento) != ABERTO:
        return FORA_DA_JANELA
    db.session.add(Resposta(
        atividade_id=atividade.id,
        nome=nome,
        matricula=normalizar_matricula(matricula),
        curso_turma_id=curso_turma_id,
        email=email,
        descricao=descricao,
        enviado_em=momento,
        ip=ip or "",
    ))
    try:
        db.session.commit()
    except IntegrityError:
        # RN04: a restrição única (atividade, matrícula) barra a segunda resposta,
        # inclusive em envios simultâneos.
        db.session.rollback()
        return DUPLICADA
    return REGISTRADA
