from datetime import date, datetime, time

import pytest

from app import db
from app.models import Atividade, CursoTurma, Resposta, TipoEvento
from app.servicos.tempo import fechamento_padrao


def _texto(resposta):
    return resposta.get_data(as_text=True)


@pytest.fixture
def tipo_id(app):
    with app.app_context():
        tipo = TipoEvento(nome="META")
        db.session.add(tipo)
        db.session.commit()
        return tipo.id


def _dados_atividade(tipo_id, **extra):
    dados = {
        "tipo_evento_id": tipo_id, "titulo": "Palestra de abertura",
        "modalidade": "palestra", "data": "2026-10-20",
        "hora_inicio": "14:00", "hora_fim": "15:00",
        "local": "Auditório", "envolvidos": "Fulano", "fecha_em": "",
    }
    dados.update(extra)
    return dados


def _criar_atividade(app, tipo_id, titulo="Palestra", dia=date(2026, 10, 20),
                     modalidade="palestra"):
    with app.app_context():
        atividade = Atividade(
            tipo_evento_id=tipo_id, titulo=titulo, modalidade=modalidade, data=dia,
            hora_inicio=time(14, 0), hora_fim=time(15, 0),
            fecha_em=fechamento_padrao(dia),
        )
        db.session.add(atividade)
        db.session.commit()
        return atividade.id


def _buscar(app, modelo, id_):
    with app.app_context():
        objeto = db.session.get(modelo, id_)
        db.session.expunge_all()
        return objeto


# --- acesso ------------------------------------------------------------------

@pytest.mark.parametrize("metodo, url", [
    ("get", "/admin/tipos-evento"),
    ("get", "/admin/tipos-evento/novo"),
    ("get", "/admin/tipos-evento/1/editar"),
    ("post", "/admin/tipos-evento/1/alternar"),
    ("get", "/admin/cursos-turmas"),
    ("get", "/admin/cursos-turmas/novo"),
    ("get", "/admin/cursos-turmas/1/editar"),
    ("post", "/admin/cursos-turmas/1/alternar"),
    ("get", "/admin/atividades"),
    ("get", "/admin/atividades/nova"),
    ("get", "/admin/atividades/1/editar"),
    ("post", "/admin/atividades/1/excluir"),
])
def test_rotas_exigem_login(client, metodo, url):
    resposta = getattr(client, metodo)(url)
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]


@pytest.mark.parametrize("url", [
    "/admin/tipos-evento/1/alternar",
    "/admin/cursos-turmas/1/alternar",
    "/admin/atividades/1/excluir",
])
def test_acoes_nao_aceitam_get(cliente_logado, url):
    assert cliente_logado.get(url).status_code == 405


# --- tipos de evento ---------------------------------------------------------

def test_criar_e_editar_tipo_evento(app, cliente_logado):
    resposta = cliente_logado.post(
        "/admin/tipos-evento/novo", data={"nome": " 35ª META 2026 ", "ativo": "y"},
        follow_redirects=True,
    )
    assert "Tipo de evento salvo." in _texto(resposta)
    with app.app_context():
        tipo = db.session.execute(db.select(TipoEvento)).scalar_one()
        assert (tipo.nome, tipo.ativo) == ("35ª META 2026", True)
        tipo_id = tipo.id

    cliente_logado.post(f"/admin/tipos-evento/{tipo_id}/editar",
                        data={"nome": "Semana C&T 2027", "ativo": "y"})
    assert _buscar(app, TipoEvento, tipo_id).nome == "Semana C&T 2027"


def test_formulario_de_tipo_evento_nao_tem_ano(cliente_logado):
    texto = _texto(cliente_logado.get("/admin/tipos-evento/novo"))
    assert 'name="ano"' not in texto
    assert "35ª META 2026" in texto  # exemplo de nome no texto de ajuda


def test_tipo_evento_duplicado_pelo_nome(app, cliente_logado, tipo_id):
    resposta = cliente_logado.post(
        "/admin/tipos-evento/novo", data={"nome": "  meta ", "ativo": "y"})
    assert "Já existe um tipo de evento com este nome." in _texto(resposta)

    # Outro nome (ex.: outra edição) é permitido.
    cliente_logado.post("/admin/tipos-evento/novo", data={"nome": "META 2027", "ativo": "y"})
    with app.app_context():
        assert db.session.query(TipoEvento).count() == 2

    # Renomear para um nome já usado também é bloqueado.
    with app.app_context():
        outro_id = db.session.execute(
            db.select(TipoEvento.id).filter_by(nome="META 2027")).scalar_one()
    resposta = cliente_logado.post(f"/admin/tipos-evento/{outro_id}/editar",
                                   data={"nome": "Meta"})
    assert "Já existe um tipo de evento com este nome." in _texto(resposta)

    # Editar sem mudar o nome não acusa duplicidade com ele mesmo.
    resposta = cliente_logado.post(f"/admin/tipos-evento/{tipo_id}/editar",
                                   data={"nome": "META"})
    assert resposta.status_code == 302


def test_desativar_e_reativar_tipo_evento(app, cliente_logado, tipo_id):
    cliente_logado.post(f"/admin/tipos-evento/{tipo_id}/alternar")
    assert _buscar(app, TipoEvento, tipo_id).ativo is False
    cliente_logado.post(f"/admin/tipos-evento/{tipo_id}/alternar")
    assert _buscar(app, TipoEvento, tipo_id).ativo is True


def test_editar_tipo_inexistente(cliente_logado):
    assert cliente_logado.get("/admin/tipos-evento/999/editar").status_code == 404


# --- cursos/turmas -----------------------------------------------------------

def test_criar_editar_e_desativar_curso(app, cliente_logado):
    cliente_logado.post("/admin/cursos-turmas/novo",
                        data={"nome": "Informática 1A", "ativo": "y"})
    with app.app_context():
        curso_id = db.session.execute(db.select(CursoTurma.id)).scalar_one()

    cliente_logado.post(f"/admin/cursos-turmas/{curso_id}/editar",
                        data={"nome": "Informática 2A", "ativo": "y"})
    assert _buscar(app, CursoTurma, curso_id).nome == "Informática 2A"

    cliente_logado.post(f"/admin/cursos-turmas/{curso_id}/alternar")
    assert _buscar(app, CursoTurma, curso_id).ativo is False


def test_curso_duplicado(cliente_logado):
    cliente_logado.post("/admin/cursos-turmas/novo", data={"nome": "Informática 1A"})
    resposta = cliente_logado.post("/admin/cursos-turmas/novo",
                                   data={"nome": "INFORMÁTICA  1A"})
    assert "Já existe um curso/turma com este nome." in _texto(resposta)


# --- atividades: cadastro e edição -------------------------------------------

def test_criar_atividade_usa_fechamento_padrao(app, cliente_logado, tipo_id):
    resposta = cliente_logado.post("/admin/atividades/nova",
                                   data=_dados_atividade(tipo_id), follow_redirects=True)
    assert "Atividade salva." in _texto(resposta)
    with app.app_context():
        atividade = db.session.execute(db.select(Atividade)).scalar_one()
        assert atividade.fecha_em == datetime(2026, 10, 20, 23, 59)
        assert atividade.hora_inicio == time(14, 0)
        assert len(atividade.token) == 36


def test_criar_atividade_com_fechamento_informado(app, cliente_logado, tipo_id):
    cliente_logado.post("/admin/atividades/nova",
                        data=_dados_atividade(tipo_id, fecha_em="2026-10-22T18:00"))
    with app.app_context():
        atividade = db.session.execute(db.select(Atividade)).scalar_one()
        assert atividade.fecha_em == datetime(2026, 10, 22, 18, 0)


@pytest.mark.parametrize("hora_fim", ["14:00", "13:30"])
def test_hora_fim_deve_ser_posterior(app, cliente_logado, tipo_id, hora_fim):
    resposta = cliente_logado.post("/admin/atividades/nova",
                                   data=_dados_atividade(tipo_id, hora_fim=hora_fim))
    assert "A hora de término deve ser posterior à de início." in _texto(resposta)
    with app.app_context():
        assert db.session.query(Atividade).count() == 0


def test_fechamento_nao_pode_ser_antes_do_inicio(cliente_logado, tipo_id):
    resposta = cliente_logado.post(
        "/admin/atividades/nova",
        data=_dados_atividade(tipo_id, fecha_em="2026-10-20T13:59"))
    assert "O fechamento não pode ser anterior ao início da atividade." in _texto(resposta)


def test_campos_obrigatorios_da_atividade(cliente_logado, tipo_id):
    resposta = cliente_logado.post(
        "/admin/atividades/nova",
        data=_dados_atividade(tipo_id, titulo="", data="", local="", envolvidos=""))
    texto = _texto(resposta)
    assert "Informe o título." in texto
    assert "Informe a data." in texto


def test_editar_atividade_prorroga_prazo(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id)
    cliente_logado.post(
        f"/admin/atividades/{atividade_id}/editar",
        data=_dados_atividade(tipo_id, titulo="Palestra",
                              fecha_em="2026-10-25T12:00"))
    assert _buscar(app, Atividade, atividade_id).fecha_em == datetime(2026, 10, 25, 12, 0)


def test_edicao_mostra_fechamento_atual(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id)
    texto = _texto(cliente_logado.get(f"/admin/atividades/{atividade_id}/editar"))
    assert 'value="2026-10-20T23:59"' in texto


def test_atividade_duplicada_no_mesmo_evento(app, cliente_logado, tipo_id):
    _criar_atividade(app, tipo_id, titulo="Palestra de abertura")
    resposta = cliente_logado.post(
        "/admin/atividades/nova",
        data=_dados_atividade(tipo_id, titulo=" palestra  de ABERTURA "))
    assert ("Já existe uma atividade com este título em um evento com este nome."
            in _texto(resposta))

    with app.app_context():
        outro_nome = TipoEvento(nome="Semana C&T")
        db.session.add(outro_nome)
        db.session.commit()
        outro_nome_id = outro_nome.id

    # O mesmo título em um evento com outro nome é permitido.
    resposta = cliente_logado.post(
        "/admin/atividades/nova",
        data=_dados_atividade(outro_nome_id, titulo="Palestra de abertura"))
    assert resposta.status_code == 302


def test_editar_atividade_mantendo_titulo(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id, titulo="Palestra")
    resposta = cliente_logado.post(f"/admin/atividades/{atividade_id}/editar",
                                   data=_dados_atividade(tipo_id, titulo="Palestra"))
    assert resposta.status_code == 302


def test_lista_de_tipos_mostra_so_ativos(app, cliente_logado, tipo_id):
    with app.app_context():
        db.session.add(TipoEvento(nome="Evento antigo", ativo=False))
        db.session.commit()
    texto = _texto(cliente_logado.get("/admin/atividades/nova"))
    assert ">META</option>" in texto
    assert "Evento antigo" not in texto


def test_edicao_mantem_tipo_inativo_da_atividade(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id)
    cliente_logado.post(f"/admin/tipos-evento/{tipo_id}/alternar")
    texto = _texto(cliente_logado.get(f"/admin/atividades/{atividade_id}/editar"))
    assert ">META</option>" in texto


# --- atividades: listagem e filtros ------------------------------------------

def test_filtros_da_listagem(app, cliente_logado, tipo_id):
    with app.app_context():
        outro = TipoEvento(nome="Semana C&T")
        db.session.add(outro)
        db.session.commit()
        outro_id = outro.id
    _criar_atividade(app, tipo_id, "Atividade A", date(2026, 10, 20), "palestra")
    _criar_atividade(app, tipo_id, "Atividade B", date(2026, 10, 21), "minicurso")
    _criar_atividade(app, outro_id, "Atividade C", date(2026, 10, 20), "minicurso")

    def titulos(**params):
        texto = _texto(cliente_logado.get("/admin/atividades", query_string=params))
        return {t for t in ("Atividade A", "Atividade B", "Atividade C") if t in texto}

    assert titulos() == {"Atividade A", "Atividade B", "Atividade C"}
    assert titulos(tipo_evento=tipo_id) == {"Atividade A", "Atividade B"}
    assert titulos(data="2026-10-20") == {"Atividade A", "Atividade C"}
    assert titulos(modalidade="minicurso") == {"Atividade B", "Atividade C"}
    assert titulos(tipo_evento=tipo_id, modalidade="minicurso") == {"Atividade B"}
    # Filtros inválidos são ignorados.
    assert len(titulos(data="ontem", modalidade="xyz")) == 3


# --- atividades: exclusão ----------------------------------------------------

def test_excluir_atividade_sem_respostas(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id)
    resposta = cliente_logado.post(f"/admin/atividades/{atividade_id}/excluir",
                                   follow_redirects=True)
    assert "Atividade excluída." in _texto(resposta)
    assert _buscar(app, Atividade, atividade_id) is None


def test_nao_exclui_atividade_com_respostas(app, cliente_logado, tipo_id):
    atividade_id = _criar_atividade(app, tipo_id)
    with app.app_context():
        curso = CursoTurma(nome="Informática 1A")
        db.session.add(curso)
        db.session.flush()
        db.session.add(Resposta(
            atividade_id=atividade_id, nome="Aluno", matricula="20261234",
            curso_turma_id=curso.id, email="aluno@exemplo.com", descricao="x"))
        db.session.commit()

    resposta = cliente_logado.post(f"/admin/atividades/{atividade_id}/excluir",
                                   follow_redirects=True)
    assert "não pode ser excluída" in _texto(resposta)
    assert _buscar(app, Atividade, atividade_id) is not None
    assert "apenas edição" in _texto(cliente_logado.get("/admin/atividades"))
