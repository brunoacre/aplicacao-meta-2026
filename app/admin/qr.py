"""Rotas do PDF de QR Code: individual (RF07) e por filtros (RF08)."""
from flask import flash, redirect, request, send_file, url_for
from flask_login import login_required

from .. import db
from ..models import Atividade, TipoEvento
from ..servicos import cadastros, pdf_qr
from . import bp
from .cadastros import filtros_da_url


@bp.route("/atividades/<int:id>/qrcode.pdf")
@login_required
def atividade_qrcode(id):
    atividade = db.get_or_404(Atividade, id)
    return send_file(pdf_qr.gerar_pdf([atividade]), mimetype="application/pdf",
                     as_attachment=True,
                     download_name=pdf_qr.nome_arquivo_atividade(atividade))


@bp.route("/atividades/qrcodes.pdf")
@login_required
def atividades_qrcodes_pdf():
    filtros = filtros_da_url()
    atividades = cadastros.filtrar_atividades(**filtros)
    if not atividades:
        flash("Nenhuma atividade encontrada para gerar o PDF.", "warning")
        return redirect(url_for("admin.atividades", **request.args))
    tipo = db.session.get(TipoEvento, filtros["tipo_evento_id"]) \
        if filtros["tipo_evento_id"] else None
    return send_file(pdf_qr.gerar_pdf(atividades), mimetype="application/pdf",
                     as_attachment=True, download_name=pdf_qr.nome_arquivo(tipo))
