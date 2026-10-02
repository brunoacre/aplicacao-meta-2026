"""Rotas da importação de atividades por planilha (RF06)."""
from flask import current_app, flash, redirect, render_template, send_file, url_for
from flask_login import login_required
from werkzeug.exceptions import RequestEntityTooLarge

from ..models import MODALIDADES
from ..servicos import importacao
from . import bp
from .formularios import ConfirmarImportacaoForm, ImportarPlanilhaForm

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _pasta():
    return current_app.config["PASTA_IMPORTACOES"]


@bp.errorhandler(RequestEntityTooLarge)
def _arquivo_grande(_erro):
    flash("O arquivo passa do tamanho máximo de 2 MB.", "danger")
    return redirect(url_for("admin.importar"))


@bp.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    form = ImportarPlanilhaForm()
    if form.validate_on_submit():
        identificador = importacao.guardar_arquivo(form.arquivo.data, _pasta())
        caminho = importacao.caminho_arquivo(_pasta(), identificador)
        try:
            resultado = importacao.ler_planilha(caminho)
        except importacao.ErroPlanilha as erro:
            caminho.unlink(missing_ok=True)
            form.arquivo.errors.append(str(erro))
        else:
            return render_template(
                "admin/importar_previa.html",
                resultado=resultado,
                form=ConfirmarImportacaoForm(formdata=None, identificador=identificador),
                modalidades=MODALIDADES,
            )
    return render_template("admin/importar.html", form=form)


@bp.route("/importar/modelo")
@login_required
def importar_modelo():
    return send_file(importacao.gerar_modelo(), mimetype=TIPO_XLSX,
                     as_attachment=True, download_name="modelo_atividades.xlsx")


@bp.route("/importar/confirmar", methods=["POST"])
@login_required
def importar_confirmar():
    form = ConfirmarImportacaoForm()
    caminho = (importacao.caminho_arquivo(_pasta(), form.identificador.data)
               if form.validate_on_submit() else None)
    if caminho is None:
        flash("A pré-visualização expirou. Envie a planilha novamente.", "warning")
        return redirect(url_for("admin.importar"))

    # Valida de novo: o banco pode ter mudado desde a pré-visualização.
    try:
        resultado = importacao.ler_planilha(caminho)
    except importacao.ErroPlanilha as erro:
        flash(str(erro), "danger")
        return redirect(url_for("admin.importar"))
    finally:
        caminho.unlink(missing_ok=True)

    quantidade, criados = importacao.importar(resultado)
    flash(f"{quantidade} atividade{'s' if quantidade != 1 else ''} "
          f"importada{'s' if quantidade != 1 else ''}.", "success")
    if criados:
        flash("Tipos de evento criados: " + ", ".join(criados) + ".", "info")
    if resultado.com_erro:
        flash(f"{len(resultado.com_erro)} linha(s) com erro não foram importadas.", "warning")
    return redirect(url_for("admin.atividades"))
