import uuid

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .servicos.tempo import agora

MODALIDADES = {
    "palestra": "Palestra",
    "apresentacao": "Apresentação de trabalho",
    "minicurso": "Minicurso",
    "outra": "Outra",
}


def _novo_token():
    return str(uuid.uuid4())


class Administrador(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def is_active(self):
        return self.ativo

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


@login_manager.user_loader
def carregar_administrador(id_admin):
    return db.session.get(Administrador, int(id_admin))


class TipoEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Identifica o evento sozinho, sem ano separado (ex.: "35ª META 2026").
    nome = db.Column(db.String(120), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    atividades = db.relationship("Atividade", back_populates="tipo_evento")


class CursoTurma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)


class Atividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_evento_id = db.Column(
        db.Integer, db.ForeignKey("tipo_evento.id"), nullable=False
    )
    titulo = db.Column(db.String(300), nullable=False)
    modalidade = db.Column(db.String(20), nullable=False)
    data = db.Column(db.Date, nullable=False)
    # Só informativa e para ordenar: o formulário abre à 00h00 da data (RN01).
    hora_inicio = db.Column(db.Time, nullable=False)
    local = db.Column(db.String(120), nullable=False, default="")
    envolvidos = db.Column(db.Text, nullable=False, default="")
    token = db.Column(
        db.String(36), nullable=False, unique=True, default=_novo_token
    )
    # Hora local de São Paulo, sem fuso (ver servicos/tempo.py).
    fecha_em = db.Column(db.DateTime, nullable=False)

    tipo_evento = db.relationship("TipoEvento", back_populates="atividades")
    respostas = db.relationship("Resposta", back_populates="atividade")

    @property
    def modalidade_rotulo(self):
        return MODALIDADES.get(self.modalidade, self.modalidade)


class Resposta(db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            "atividade_id", "matricula", name="uq_resposta_atividade_matricula"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    atividade_id = db.Column(
        db.Integer, db.ForeignKey("atividade.id"), nullable=False
    )
    nome = db.Column(db.String(200), nullable=False)
    matricula = db.Column(db.String(40), nullable=False)
    curso_turma_id = db.Column(
        db.Integer, db.ForeignKey("curso_turma.id"), nullable=False
    )
    email = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    # Hora local de São Paulo, sem fuso (ver servicos/tempo.py).
    enviado_em = db.Column(db.DateTime, nullable=False, default=agora)
    ip = db.Column(db.String(45), nullable=False, default="")

    atividade = db.relationship("Atividade", back_populates="respostas")
    curso_turma = db.relationship("CursoTurma")
