"""Regras de negócio dos cadastros: tipos de evento, cursos/turmas e atividades."""
from sqlalchemy.orm import joinedload

from .. import db
from ..models import Atividade, CursoTurma, Resposta, TipoEvento
from .tempo import fechamento_padrao


def chave_nome(texto):
    """Forma usada para comparar nomes: sem espaços extras e sem diferenciar maiúsculas."""
    return " ".join((texto or "").split()).casefold()


# --- Duplicidade -------------------------------------------------------------

def tipo_evento_duplicado(nome, ignorar_id=None):
    """Já existe outro tipo de evento com o mesmo nome?"""
    candidatos = db.session.execute(db.select(TipoEvento)).scalars()
    return any(
        t.id != ignorar_id and chave_nome(t.nome) == chave_nome(nome) for t in candidatos
    )


def curso_turma_duplicado(nome, ignorar_id=None):
    """Já existe outro curso/turma com o mesmo nome?"""
    candidatos = db.session.execute(db.select(CursoTurma)).scalars()
    return any(
        c.id != ignorar_id and chave_nome(c.nome) == chave_nome(nome) for c in candidatos
    )


def chaves_atividades(ignorar_id=None):
    """Pares (nome do evento, título) já cadastrados, na forma de comparação."""
    linhas = db.session.execute(
        db.select(Atividade.id, TipoEvento.nome, Atividade.titulo)
        .join(Atividade.tipo_evento)
    )
    return {(chave_nome(n), chave_nome(t)) for id_, n, t in linhas if id_ != ignorar_id}


def atividade_duplicada(nome_evento, titulo, ignorar_id=None):
    """Já existe outra atividade com o mesmo título num evento com o mesmo nome?

    O evento é identificado só pelo nome (ex.: "35ª META 2026"); a regra vale
    tanto para o cadastro quanto para a importação de planilha.
    """
    return (chave_nome(nome_evento), chave_nome(titulo)) in chaves_atividades(ignorar_id)


def tipo_evento_por_nome(nome):
    """Tipo de evento com este nome (sem diferenciar maiúsculas e espaços extras)."""
    return next((
        t for t in db.session.execute(db.select(TipoEvento).order_by(TipoEvento.id)).scalars()
        if chave_nome(t.nome) == chave_nome(nome)
    ), None)


# --- Tipos de evento e cursos/turmas -----------------------------------------

def listar_tipos_evento():
    return db.session.execute(
        db.select(TipoEvento).order_by(TipoEvento.nome)
    ).scalars().all()


def opcoes_tipo_evento(incluir_id=None):
    """Tipos ativos para a lista da atividade; inclui o tipo atual mesmo se inativo."""
    consulta = db.select(TipoEvento).order_by(TipoEvento.nome)
    if incluir_id:
        consulta = consulta.where(
            db.or_(TipoEvento.ativo.is_(True), TipoEvento.id == incluir_id)
        )
    else:
        consulta = consulta.filter_by(ativo=True)
    return [(t.id, t.nome) for t in db.session.execute(consulta).scalars()]


def listar_cursos_turmas():
    return db.session.execute(
        db.select(CursoTurma).order_by(CursoTurma.nome)
    ).scalars().all()


def alternar_ativo(objeto):
    """Desativa um item ativo ou reativa um inativo."""
    objeto.ativo = not objeto.ativo
    db.session.commit()


# --- Atividades --------------------------------------------------------------

def filtrar_atividades(tipo_evento_id=None, data=None, modalidade=None):
    consulta = (
        db.select(Atividade)
        .options(joinedload(Atividade.tipo_evento))
        .order_by(Atividade.data, Atividade.hora_inicio, Atividade.titulo)
    )
    if tipo_evento_id:
        consulta = consulta.filter_by(tipo_evento_id=tipo_evento_id)
    if data:
        consulta = consulta.filter_by(data=data)
    if modalidade:
        consulta = consulta.filter_by(modalidade=modalidade)
    return db.session.execute(consulta).scalars().all()


def ids_com_respostas(atividades):
    """IDs das atividades (da lista dada) que já têm respostas, numa só consulta."""
    ids = [a.id for a in atividades]
    if not ids:
        return set()
    return set(db.session.execute(
        db.select(Resposta.atividade_id).where(Resposta.atividade_id.in_(ids)).distinct()
    ).scalars())


def tem_respostas(atividade):
    return db.session.execute(
        db.select(Resposta.id).filter_by(atividade_id=atividade.id).limit(1)
    ).first() is not None


def salvar_atividade(atividade):
    """Grava a atividade. Sem fechamento informado, usa o padrão (RN02)."""
    if atividade.fecha_em is None:
        atividade.fecha_em = fechamento_padrao(atividade.data)
    db.session.add(atividade)
    db.session.commit()


def excluir_atividade(atividade):
    """Exclui a atividade se ela não tiver respostas (RF04). Retorna se excluiu."""
    if tem_respostas(atividade):
        return False
    db.session.delete(atividade)
    db.session.commit()
    return True
