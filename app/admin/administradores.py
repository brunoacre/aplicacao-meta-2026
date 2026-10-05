"""Rotas de administradores (RF16): listar, cadastrar, redefinir senha e desativar."""
from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import Administrador
from ..servicos import administradores
from . import bp
from .formularios import AcaoForm, AdministradorForm, SenhaForm


@bp.route("/administradores", endpoint="administradores")
@login_required
def administradores_lista():
    return render_template("admin/administradores.html",
                           administradores=administradores.listar())


@bp.route("/administradores/novo", methods=["GET", "POST"])
@login_required
def administrador_form():
    form = AdministradorForm()
    if form.validate_on_submit():
        try:
            admin = administradores.criar(form.nome.data, form.email.data, form.senha.data)
        except administradores.ErroAdministrador as erro:
            getattr(form, erro.campo).errors.append(erro.mensagem)
        else:
            flash(f"Administrador {admin.email} cadastrado.", "success")
            return redirect(url_for("admin.administradores"))
    return render_template("admin/administrador_form.html", form=form)


@bp.route("/administradores/<int:id>/senha", methods=["GET", "POST"])
@login_required
def administrador_senha(id):
    admin = db.get_or_404(Administrador, id)
    form = SenhaForm()
    if form.validate_on_submit():
        try:
            administradores.redefinir_senha(admin, form.senha.data)
        except administradores.ErroAdministrador as erro:
            form.senha.errors.append(erro.mensagem)
        else:
            flash(f"Senha de {admin.email} redefinida.", "success")
            return redirect(url_for("admin.administradores"))
    return render_template("admin/administrador_senha.html", form=form, admin=admin)


@bp.route("/administradores/<int:id>/alternar", methods=["POST"])
@login_required
def administrador_alternar(id):
    admin = db.get_or_404(Administrador, id)
    if AcaoForm().validate_on_submit():
        try:
            administradores.alternar(admin, current_user)
        except administradores.ErroAdministrador as erro:
            flash(erro.mensagem, "danger")
        else:
            flash(f"Administrador {'reativado' if admin.ativo else 'desativado'}.", "success")
    return redirect(url_for("admin.administradores"))
