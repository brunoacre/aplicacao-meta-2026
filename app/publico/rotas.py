from flask import abort, current_app, render_template, request
from flask_wtf.csrf import CSRFError

from ..servicos import presenca as servico
from ..servicos.tempo import agora
from . import bp
from .formularios import PresencaForm


def _carregar_ou_404(token):
    atividade = servico.carregar_atividade(token)
    if atividade is None:
        abort(404)
    return atividade


def _pagina_indisponivel(atividade, situacao):
    return render_template("publico/indisponivel.html", atividade=atividade,
                           situacao=situacao, abre_em=servico.abertura(atividade))


def _pagina_formulario(atividade, form, momento, aviso=None):
    return render_template(
        "publico/formulario.html", atividade=atividade, form=form, momento=momento,
        aviso=aviso,
        minimo=current_app.config["MIN_CARACTERES_DESCRICAO"],
        maximo=current_app.config["MAX_CARACTERES_DESCRICAO"],
    )


def _montar_formulario(cursos, **kwargs):
    form = PresencaForm(**kwargs)
    form.curso_turma_id.choices = [("", "Selecione")] + [
        (str(id_), nome) for id_, nome in cursos]
    return form


@bp.route("/presenca/<token>", methods=["GET", "POST"])
def presenca(token):
    atividade = _carregar_ou_404(token)
    momento = agora()
    situacao = servico.situacao_janela(atividade, momento)
    if situacao != servico.ABERTO:
        return _pagina_indisponivel(atividade, situacao)

    cursos = servico.cursos_ativos()
    form = _montar_formulario(cursos)
    if form.validate_on_submit():
        curso_id = int(form.curso_turma_id.data)
        resultado = servico.registrar_presenca(
            atividade, nome=form.nome.data, matricula=form.matricula.data,
            curso_turma_id=curso_id, email=form.email.data,
            descricao=form.descricao.data, ip=request.remote_addr, momento=momento,
        )
        if resultado == servico.DUPLICADA:
            return _pagina_indisponivel(atividade, "duplicada")
        if resultado == servico.FORA_DA_JANELA:
            return _pagina_indisponivel(atividade, servico.ENCERRADO)
        return render_template(
            "publico/confirmacao.html", atividade=atividade, form=form,
            matricula=servico.normalizar_matricula(form.matricula.data),
            curso=dict(cursos)[curso_id], enviado_em=momento,
        )
    return _pagina_formulario(atividade, form, momento)


@bp.errorhandler(CSRFError)
def _sessao_expirada(_erro):
    """Devolve o formulário preenchido em vez de um erro 400."""
    atividade = _carregar_ou_404(request.view_args.get("token"))
    momento = agora()
    situacao = servico.situacao_janela(atividade, momento)
    if situacao != servico.ABERTO:
        return _pagina_indisponivel(atividade, situacao)
    form = _montar_formulario(servico.cursos_ativos(), formdata=request.form)
    return _pagina_formulario(
        atividade, form, momento,
        aviso="Sua sessão expirou. Confira os dados e envie novamente.")


@bp.errorhandler(404)
def _nao_encontrada(_erro):
    return render_template("publico/nao_encontrada.html"), 404
