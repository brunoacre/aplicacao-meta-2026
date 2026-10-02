from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .. import db
from ..models import Administrador
from ..servicos.validacao import normalizar_email
from . import bp
from .formularios import LoginForm, SairForm


def _destino_seguro(destino):
    """Aceita apenas caminhos internos, evitando redirecionamento aberto."""
    if not destino:
        return None
    partes = urlsplit(destino)
    if partes.scheme or partes.netloc or not destino.startswith("/"):
        return None
    if destino.startswith("//") or "\\" in destino:
        return None
    return destino


@bp.context_processor
def _formulario_sair():
    return {"form_sair": SairForm()}


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.inicio"))

    form = LoginForm()
    if form.validate_on_submit():
        admin = db.session.execute(
            db.select(Administrador).filter_by(email=normalizar_email(form.email.data))
        ).scalar_one_or_none()
        if admin and admin.ativo and admin.verificar_senha(form.senha.data):
            login_user(admin)
            destino = _destino_seguro(request.args.get("next"))
            return redirect(destino or url_for("admin.inicio"))
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("admin/login.html", form=form)


@bp.route("/sair", methods=["POST"])
@login_required
def sair():
    if SairForm().validate_on_submit():
        logout_user()
        flash("Você saiu do sistema.", "success")
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def inicio():
    return render_template("admin/inicio.html")
