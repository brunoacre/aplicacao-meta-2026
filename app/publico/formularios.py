from flask import current_app
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from ..formularios import FormularioBase
from ..servicos.presenca import normalizar_matricula
from ..servicos.validacao import email_valido, normalizar_email


def _limpar_espacos(texto):
    return " ".join(texto.split()) if texto else texto


def _aparar(texto):
    return texto.strip() if texto else texto


class PresencaForm(FormularioBase):
    nome = StringField("Nome completo", filters=[_limpar_espacos], validators=[
        DataRequired("Informe seu nome completo."), Length(max=200)])
    matricula = StringField("Matrícula", validators=[
        DataRequired("Informe sua matrícula."), Length(max=40)])
    # Valores como texto para aceitar a opção vazia "Selecione"; a lista é
    # preenchida na rota com os cursos/turmas ativos.
    curso_turma_id = SelectField("Curso/turma", validators=[
        DataRequired("Selecione seu curso/turma.")])
    email = StringField("E-mail", filters=[normalizar_email], validators=[
        DataRequired("Informe seu e-mail."), Length(max=200)])
    descricao = TextAreaField("O que você achou da atividade?", filters=[_aparar],
                              validators=[DataRequired("Descreva o que achou da atividade.")])

    def validate_matricula(self, campo):
        if not normalizar_matricula(campo.data):
            raise ValidationError("Informe sua matrícula.")

    def validate_email(self, campo):
        if not email_valido(campo.data):
            raise ValidationError("Informe um e-mail válido.")

    def validate_descricao(self, campo):
        # RN06: mínimo configurável em um único lugar (Config).
        minimo = current_app.config["MIN_CARACTERES_DESCRICAO"]
        maximo = current_app.config["MAX_CARACTERES_DESCRICAO"]
        if len(campo.data) < minimo:
            raise ValidationError(
                f"Escreva pelo menos {minimo} caracteres (você escreveu {len(campo.data)}).")
        if len(campo.data) > maximo:
            raise ValidationError(f"Escreva no máximo {maximo} caracteres.")
