from flask_wtf import FlaskForm


class FormularioBase(FlaskForm):
    class Meta:
        # Mensagens padrão do WTForms (ex.: data inválida) em português.
        locales = ["pt"]
