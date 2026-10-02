"""Rotas de relatórios (RF09, RF10), pesquisa por aluno (RF11) e respostas (RF12)."""
from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from .. import db
from ..models import Atividade, TipoEvento
from ..servicos import cadastros, relatorios
from . import bp

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@bp.route("/relatorios")
@login_required
def relatorios_inicio():
    termo = request.args.get("q", "").strip()
    alunos, mais_resultados = relatorios.pesquisar_alunos(termo) if termo else ([], False)
    return render_template(
        "admin/relatorios.html",
        tipos=cadastros.listar_tipos_evento(),
        termo=termo, alunos=alunos, mais_resultados=mais_resultados,
        maximo=relatorios.MAX_ALUNOS_PESQUISA,
    )


@bp.route("/relatorios/consolidado.xlsx")
@login_required
def relatorio_consolidado():
    tipo_id = request.args.get("tipo_evento", type=int)
    tipo = db.session.get(TipoEvento, tipo_id) if tipo_id else None
    turmas = relatorios.consolidar_por_turma(tipo.id if tipo else None)
    if not turmas:
        flash("Nenhuma presença registrada para gerar o relatório.", "warning")
        return redirect(url_for("admin.relatorios_inicio"))
    return send_file(relatorios.exportar_consolidado(turmas, tipo), mimetype=TIPO_XLSX,
                     as_attachment=True,
                     download_name=relatorios.nome_arquivo_consolidado(tipo))


@bp.route("/atividades/<int:id>/respostas")
@login_required
def atividade_respostas(id):
    atividade = db.get_or_404(Atividade, id)
    return render_template("admin/respostas.html", atividade=atividade,
                           respostas=relatorios.respostas_da_atividade(atividade))


@bp.route("/atividades/<int:id>/respostas.xlsx")
@login_required
def atividade_respostas_xlsx(id):
    atividade = db.get_or_404(Atividade, id)
    planilha = relatorios.exportar_respostas(
        atividade, relatorios.respostas_da_atividade(atividade))
    return send_file(planilha, mimetype=TIPO_XLSX, as_attachment=True,
                     download_name=relatorios.nome_arquivo_respostas(atividade))
