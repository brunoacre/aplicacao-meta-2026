from datetime import datetime

from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from ..formularios import FormularioBase
from ..models import MODALIDADES


class LoginForm(FormularioBase):
    email = StringField("E-mail", validators=[DataRequired("Informe o e-mail.")])
    senha = PasswordField("Senha", validators=[DataRequired("Informe a senha.")])


class SairForm(FormularioBase):
    """Formulário vazio, só para o token CSRF do botão Sair."""


class AcaoForm(FormularioBase):
    """Formulário vazio, só para o token CSRF dos botões de ação (desativar, excluir)."""


class TipoEventoForm(FormularioBase):
    nome = StringField("Nome", validators=[
        DataRequired("Informe o nome."), Length(max=120)],
        description="Inclua a edição e o ano no nome, ex.: 35ª META 2026.")
    ativo = BooleanField("Ativo", default=True)


class CursoTurmaForm(FormularioBase):
    nome = StringField("Nome", validators=[
        DataRequired("Informe o nome."), Length(max=120)])
    ativo = BooleanField("Ativo", default=True)


class AtividadeForm(FormularioBase):
    tipo_evento_id = SelectField(
        "Tipo de evento", coerce=int,
        validators=[DataRequired("Selecione o tipo de evento.")])
    titulo = StringField("Título", validators=[
        DataRequired("Informe o título."), Length(max=300)])
    modalidade = SelectField(
        "Modalidade", choices=list(MODALIDADES.items()),
        validators=[DataRequired("Selecione a modalidade.")])
    data = DateField("Data", validators=[DataRequired("Informe a data.")])
    hora_inicio = TimeField(
        "Hora de início", validators=[DataRequired("Informe a hora de início.")])
    hora_fim = TimeField(
        "Hora de término", validators=[DataRequired("Informe a hora de término.")])
    local = StringField("Local", validators=[Optional(), Length(max=120)])
    envolvidos = TextAreaField("Pessoas envolvidas", validators=[Optional()])
    fecha_em = DateTimeLocalField(
        "Formulário fecha em", format="%Y-%m-%dT%H:%M", validators=[Optional()],
        description="Sugestão: 23h59 do dia da atividade. Pode ser alterado para "
                    "prorrogar o prazo.")

    def validate_hora_fim(self, campo):
        if self.hora_inicio.data and campo.data and campo.data <= self.hora_inicio.data:
            raise ValidationError("A hora de término deve ser posterior à de início.")

    def validate_fecha_em(self, campo):
        if campo.data and self.data.data and self.hora_inicio.data:
            inicio = datetime.combine(self.data.data, self.hora_inicio.data)
            if campo.data < inicio:
                raise ValidationError(
                    "O fechamento não pode ser anterior ao início da atividade.")


class ImportarPlanilhaForm(FormularioBase):
    arquivo = FileField("Planilha (.xlsx)", validators=[
        FileRequired("Selecione a planilha."),
        FileAllowed(["xlsx"], "Envie uma planilha no formato .xlsx.")])


class ConfirmarImportacaoForm(FormularioBase):
    identificador = HiddenField(validators=[DataRequired()])
