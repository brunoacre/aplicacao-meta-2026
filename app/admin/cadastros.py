"""Rotas de cadastro: tipos de evento, cursos/turmas e atividades."""
from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from .. import db
from ..models import MODALIDADES, Atividade, CursoTurma, TipoEvento
from ..servicos import cadastros
from . import bp
from .formularios import AcaoForm, AtividadeForm, CursoTurmaForm, TipoEventoForm


# --- Tipos de evento ---------------------------------------------------------

@bp.route("/tipos-evento")
@login_required
def tipos_evento():
    return render_template(
        "admin/tipos_evento.html",
        tipos=cadastros.listar_tipos_evento(),
    )


@bp.route("/tipos-evento/novo", methods=["GET", "POST"])
@bp.route("/tipos-evento/<int:id>/editar", methods=["GET", "POST"])
@login_required
def tipo_evento_form(id=None):
    tipo = db.get_or_404(TipoEvento, id) if id else TipoEvento()
    form = TipoEventoForm(obj=tipo if id else None)
    if form.validate_on_submit():
        if cadastros.tipo_evento_duplicado(form.nome.data, ignorar_id=id):
            form.nome.errors.append("Já existe um tipo de evento com este nome.")
        else:
            form.populate_obj(tipo)
            tipo.nome = tipo.nome.strip()
            db.session.add(tipo)
            db.session.commit()
            flash("Tipo de evento salvo.", "success")
            return redirect(url_for("admin.tipos_evento"))
    return render_template("admin/tipo_evento_form.html", form=form, tipo=tipo)


@bp.route("/tipos-evento/<int:id>/alternar", methods=["POST"])
@login_required
def tipo_evento_alternar(id):
    tipo = db.get_or_404(TipoEvento, id)
    if AcaoForm().validate_on_submit():
        cadastros.alternar_ativo(tipo)
        flash(f"Tipo de evento {'reativado' if tipo.ativo else 'desativado'}.", "success")
    return redirect(url_for("admin.tipos_evento"))


# --- Cursos/turmas -----------------------------------------------------------

@bp.route("/cursos-turmas")
@login_required
def cursos_turmas():
    return render_template(
        "admin/cursos_turmas.html",
        cursos=cadastros.listar_cursos_turmas(),
    )


@bp.route("/cursos-turmas/novo", methods=["GET", "POST"])
@bp.route("/cursos-turmas/<int:id>/editar", methods=["GET", "POST"])
@login_required
def curso_turma_form(id=None):
    curso = db.get_or_404(CursoTurma, id) if id else CursoTurma()
    form = CursoTurmaForm(obj=curso if id else None)
    if form.validate_on_submit():
        if cadastros.curso_turma_duplicado(form.nome.data, ignorar_id=id):
            form.nome.errors.append("Já existe um curso/turma com este nome.")
        else:
            form.populate_obj(curso)
            curso.nome = curso.nome.strip()
            db.session.add(curso)
            db.session.commit()
            flash("Curso/turma salvo.", "success")
            return redirect(url_for("admin.cursos_turmas"))
    return render_template("admin/curso_turma_form.html", form=form, curso=curso)


@bp.route("/cursos-turmas/<int:id>/alternar", methods=["POST"])
@login_required
def curso_turma_alternar(id):
    curso = db.get_or_404(CursoTurma, id)
    if AcaoForm().validate_on_submit():
        cadastros.alternar_ativo(curso)
        flash(f"Curso/turma {'reativado' if curso.ativo else 'desativado'}.", "success")
    return redirect(url_for("admin.cursos_turmas"))


# --- Atividades --------------------------------------------------------------

def filtros_da_url():
    """Lê os filtros da listagem; valores inválidos são ignorados."""
    tipo_id = request.args.get("tipo_evento", type=int)
    try:
        dia = date.fromisoformat(request.args.get("data", ""))
    except ValueError:
        dia = None
    modalidade = request.args.get("modalidade")
    if modalidade not in MODALIDADES:
        modalidade = None
    return {"tipo_evento_id": tipo_id, "data": dia, "modalidade": modalidade}


@bp.route("/atividades")
@login_required
def atividades():
    filtros = filtros_da_url()
    lista = cadastros.filtrar_atividades(**filtros)
    return render_template(
        "admin/atividades.html",
        atividades=lista,
        com_respostas=cadastros.ids_com_respostas(lista),
        filtros=filtros,
        tipos=cadastros.listar_tipos_evento(),
        modalidades=MODALIDADES,
    )


@bp.route("/atividades/nova", methods=["GET", "POST"])
@bp.route("/atividades/<int:id>/editar", methods=["GET", "POST"])
@login_required
def atividade_form(id=None):
    atividade = db.get_or_404(Atividade, id) if id else Atividade()
    form = AtividadeForm(obj=atividade if id else None)
    form.tipo_evento_id.choices = cadastros.opcoes_tipo_evento(atividade.tipo_evento_id)
    if form.validate_on_submit():
        tipo = db.session.get(TipoEvento, form.tipo_evento_id.data)
        if cadastros.atividade_duplicada(tipo.nome, form.titulo.data, ignorar_id=id):
            form.titulo.errors.append(
                "Já existe uma atividade com este título em um evento com este nome.")
        else:
            form.populate_obj(atividade)
            atividade.titulo = atividade.titulo.strip()
            atividade.local = (atividade.local or "").strip()
            atividade.envolvidos = (atividade.envolvidos or "").strip()
            cadastros.salvar_atividade(atividade)
            flash("Atividade salva.", "success")
            return redirect(url_for("admin.atividades"))
    return render_template("admin/atividade_form.html", form=form, atividade=atividade)


@bp.route("/atividades/<int:id>/excluir", methods=["POST"])
@login_required
def atividade_excluir(id):
    atividade = db.get_or_404(Atividade, id)
    if AcaoForm().validate_on_submit():
        if cadastros.excluir_atividade(atividade):
            flash("Atividade excluída.", "success")
        else:
            flash("Esta atividade já possui respostas e não pode ser excluída, "
                  "apenas editada.", "warning")
    return redirect(url_for("admin.atividades"))
