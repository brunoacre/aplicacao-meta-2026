from datetime import date, datetime, time

import pytest
from sqlalchemy import event

from app import create_app, db
from app.models import Atividade, CursoTurma, Resposta, TipoEvento
from app.servicos import presenca as servico
from app.servicos.presenca import normalizar_matricula, situacao_janela
from app.servicos.tempo import fechamento_padrao

DIA = date(2026, 10, 20)
DESCRICAO = "Gostei muito da atividade. " * 4  # 108 caracteres


def _texto(resposta):
    return resposta.get_data(as_text=True)


@pytest.fixture
def relogio(monkeypatch):
    """Fixa a hora "agora" vista pela rota pública."""
    def _ajustar(momento):
        monkeypatch.setattr("app.publico.rotas.agora", lambda: momento)
    _ajustar(datetime(2026, 10, 20, 15, 0))
    return _ajustar


@pytest.fixture
def dados(app):
    """Atividade de 20/10/2026, 14h–15h, e dois cursos (um inativo)."""
    with app.app_context():
        tipo = TipoEvento(nome="META")
        atividade = Atividade(
            tipo_evento=tipo, titulo="Palestra de abertura", modalidade="palestra",
            data=DIA, hora_inicio=time(14, 0), hora_fim=time(15, 0), local="Auditório",
            fecha_em=fechamento_padrao(DIA),
        )
        ativo = CursoTurma(nome="Informática 1A")
        inativo = CursoTurma(nome="Turma antiga", ativo=False)
        db.session.add_all([atividade, ativo, inativo])
        db.session.commit()
        return {"token": atividade.token, "atividade_id": atividade.id,
                "curso_id": ativo.id, "curso_inativo_id": inativo.id}


def _formulario(dados, **extra):
    campos = {
        "nome": "  Maria   da Silva ", "matricula": "2026.123-4",
        "curso_turma_id": str(dados["curso_id"]), "email": " Maria@Exemplo.com ",
        "descricao": DESCRICAO,
    }
    campos.update(extra)
    return campos


def _enviar(client, dados, **extra):
    return client.post(f"/presenca/{dados['token']}", data=_formulario(dados, **extra))


def _respostas(app):
    with app.app_context():
        lista = db.session.execute(db.select(Resposta)).scalars().all()
        db.session.expunge_all()
        return lista


# --- RN05: normalização da matrícula -----------------------------------------

@pytest.mark.parametrize("entrada, esperado", [
    ("20261234", "20261234"),
    ("2026.123-4", "20261234"),
    (" 2026 1234 ", "20261234"),
    ("2026–123—4", "20261234"),  # traços tipográficos
    ("2026\t12.3-4\n", "20261234"),
    ("AB-12.3", "AB123"),
    ("", ""),
    (None, ""),
])
def test_normalizar_matricula(entrada, esperado):
    assert normalizar_matricula(entrada) == esperado


# --- RN01–RN02: janela de tempo (serviço) ------------------------------------

def _atividade(fecha_em=None):
    return Atividade(data=DIA, hora_inicio=time(14, 0), hora_fim=time(15, 0),
                     fecha_em=fecha_em or fechamento_padrao(DIA))


@pytest.mark.parametrize("momento, esperado", [
    (datetime(2026, 10, 19, 23, 0), "nao_aberto"),
    (datetime(2026, 10, 20, 13, 59, 59), "nao_aberto"),
    (datetime(2026, 10, 20, 14, 0), "aberto"),
    (datetime(2026, 10, 20, 15, 30), "aberto"),
    (datetime(2026, 10, 20, 23, 59, 0), "aberto"),
    (datetime(2026, 10, 20, 23, 59, 59), "aberto"),
    (datetime(2026, 10, 21, 0, 0), "encerrado"),
    (datetime(2026, 10, 25, 10, 0), "encerrado"),
])
def test_situacao_janela(momento, esperado):
    assert situacao_janela(_atividade(), momento) == esperado


def test_situacao_janela_com_prazo_prorrogado():
    atividade = _atividade(fecha_em=datetime(2026, 10, 22, 18, 0))
    assert situacao_janela(atividade, datetime(2026, 10, 22, 17, 59)) == "aberto"
    assert situacao_janela(atividade, datetime(2026, 10, 22, 18, 0, 59)) == "aberto"
    assert situacao_janela(atividade, datetime(2026, 10, 22, 18, 1)) == "encerrado"


# --- RF13/RF15: páginas públicas ---------------------------------------------

def test_formulario_aberto(client, dados, relogio):
    texto = _texto(client.get(f"/presenca/{dados['token']}"))
    assert "Palestra de abertura" in texto
    assert '<div class="text-body-secondary small">META</div>' in texto
    assert "Auditório" in texto
    assert "Formulário disponível até hoje às 23h59." in texto
    assert "Registrar presença" in texto
    assert "Informática 1A" in texto
    assert "Turma antiga" not in texto
    assert "Mínimo de 100 caracteres." in texto


def test_aviso_de_prazo_prorrogado_mostra_data(app, client, dados, relogio):
    with app.app_context():
        db.session.get(Atividade, dados["atividade_id"]).fecha_em = datetime(2026, 10, 22, 18, 0)
        db.session.commit()
    texto = _texto(client.get(f"/presenca/{dados['token']}"))
    assert "Formulário disponível até 22/10/2026 às 18h00." in texto


def test_formulario_ainda_nao_aberto(client, dados, relogio):
    relogio(datetime(2026, 10, 20, 13, 0))
    texto = _texto(client.get(f"/presenca/{dados['token']}"))
    assert "Formulário ainda não aberto" in texto
    assert "abre em 20/10/2026 às 14h00" in texto
    assert "Registrar presença" not in texto


def test_prazo_encerrado(client, dados, relogio):
    relogio(datetime(2026, 10, 21, 0, 0))
    texto = _texto(client.get(f"/presenca/{dados['token']}"))
    assert "Prazo encerrado" in texto
    assert "Registrar presença" not in texto


def test_token_inexistente(client, dados, relogio):
    resposta = client.get("/presenca/00000000-0000-0000-0000-000000000000")
    assert resposta.status_code == 404
    assert "Atividade não encontrada" in _texto(resposta)


def test_id_interno_nao_funciona_na_url(client, dados, relogio):
    # RN08: só o token público dá acesso ao formulário.
    assert client.get(f"/presenca/{dados['atividade_id']}").status_code == 404


# --- RN03: validação da janela no envio --------------------------------------

def test_envio_antes_da_abertura_e_recusado(app, client, dados, relogio):
    relogio(datetime(2026, 10, 20, 13, 59))
    assert "Formulário ainda não aberto" in _texto(_enviar(client, dados))
    assert _respostas(app) == []


def test_envio_apos_fechamento_e_recusado(app, client, dados, relogio):
    # O aluno abre o formulário dentro do prazo e envia depois do fechamento.
    relogio(datetime(2026, 10, 20, 23, 50))
    assert "Registrar presença" in _texto(client.get(f"/presenca/{dados['token']}"))
    relogio(datetime(2026, 10, 21, 0, 0, 5))
    assert "Prazo encerrado" in _texto(_enviar(client, dados))
    assert _respostas(app) == []


def test_servico_confere_janela_no_registro(app, dados):
    with app.app_context():
        atividade = servico.carregar_atividade(dados["token"])
        resultado = servico.registrar_presenca(
            atividade, nome="A", matricula="1", curso_turma_id=dados["curso_id"],
            email="a@b.br", descricao="x", ip="", momento=datetime(2026, 10, 21, 0, 1))
        assert resultado == servico.FORA_DA_JANELA


# --- RF14: registro e confirmação --------------------------------------------

def test_registrar_presenca(app, client, dados, relogio):
    relogio(datetime(2026, 10, 20, 15, 10, 30))
    resposta = client.post(
        f"/presenca/{dados['token']}", data=_formulario(dados),
        environ_base={"REMOTE_ADDR": "10.0.0.1"},
        headers={"X-Forwarded-For": "200.10.20.30"},
    )
    texto = _texto(resposta)
    assert "Presença registrada com sucesso." in texto
    assert "Maria da Silva" in texto
    assert "20261234" in texto
    assert "Informática 1A" in texto
    assert "maria@exemplo.com" in texto

    (salva,) = _respostas(app)
    assert salva.atividade_id == dados["atividade_id"]
    assert salva.nome == "Maria da Silva"
    assert salva.matricula == "20261234"
    assert salva.email == "maria@exemplo.com"
    assert salva.descricao == DESCRICAO.strip()
    assert salva.enviado_em == datetime(2026, 10, 20, 15, 10, 30)
    assert salva.ip == "200.10.20.30"  # RN09, IP real atrás do proxy


# --- RN04: uma resposta por matrícula ----------------------------------------

def test_segunda_resposta_da_mesma_matricula(app, client, dados, relogio):
    _enviar(client, dados, matricula="2026.123-4")
    texto = _texto(_enviar(client, dados, matricula=" 2026 1234", nome="Outro nome"))
    assert "Presença já registrada" in texto
    assert "já foi registrada" in texto
    assert len(_respostas(app)) == 1


def test_matriculas_diferentes_registram(app, client, dados, relogio):
    _enviar(client, dados, matricula="111")
    _enviar(client, dados, matricula="222")
    assert len(_respostas(app)) == 2


def test_mesma_matricula_em_outra_atividade(app, client, dados, relogio):
    with app.app_context():
        tipo = db.session.execute(db.select(TipoEvento)).scalar_one()
        outra = Atividade(tipo_evento=tipo, titulo="Outra", modalidade="minicurso",
                          data=DIA, hora_inicio=time(14, 0), hora_fim=time(16, 0),
                          fecha_em=fechamento_padrao(DIA))
        db.session.add(outra)
        db.session.commit()
        outro_token = outra.token
    _enviar(client, dados)
    client.post(f"/presenca/{outro_token}", data=_formulario(dados))
    assert len(_respostas(app)) == 2


# --- RN06 e validação dos campos ---------------------------------------------

def test_descricao_abaixo_do_minimo(app, client, dados, relogio):
    texto = _texto(_enviar(client, dados, descricao="a" * 99))
    assert "Escreva pelo menos 100 caracteres (você escreveu 99)." in texto
    assert _respostas(app) == []


def test_descricao_no_minimo(app, client, dados, relogio):
    _enviar(client, dados, descricao="a" * 100)
    assert len(_respostas(app)) == 1


def test_espacos_nas_pontas_nao_contam(app, client, dados, relogio):
    _enviar(client, dados, descricao="   " + "a" * 98 + "   ")
    assert _respostas(app) == []


def test_minimo_vem_da_configuracao(app, client, dados, relogio):
    app.config["MIN_CARACTERES_DESCRICAO"] = 10
    _enviar(client, dados, descricao="a" * 10)
    assert len(_respostas(app)) == 1


def test_descricao_acima_do_maximo(app, client, dados, relogio):
    texto = _texto(_enviar(client, dados, descricao="a" * 2001))
    assert "Escreva no máximo 2000 caracteres." in texto


def test_campos_obrigatorios(app, client, dados, relogio):
    texto = _texto(_enviar(client, dados, nome=" ", matricula="", curso_turma_id="",
                           email="", descricao=""))
    for mensagem in ["Informe seu nome completo.", "Informe sua matrícula.",
                     "Selecione seu curso/turma.", "Informe seu e-mail.",
                     "Descreva o que achou da atividade."]:
        assert mensagem in texto
    assert _respostas(app) == []


def test_matricula_so_com_separadores(app, client, dados, relogio):
    assert "Informe sua matrícula." in _texto(_enviar(client, dados, matricula=" .-. "))
    assert _respostas(app) == []


def test_email_invalido(app, client, dados, relogio):
    assert "Informe um e-mail válido." in _texto(_enviar(client, dados, email="maria@"))
    assert _respostas(app) == []


@pytest.mark.parametrize("chave", ["curso_inativo_id", None])
def test_curso_inativo_ou_inexistente(app, client, dados, relogio, chave):
    curso = str(dados[chave]) if chave else "999"
    _enviar(client, dados, curso_turma_id=curso)
    assert _respostas(app) == []


# --- desempenho: no máximo duas consultas ------------------------------------

@pytest.fixture
def contar_consultas(app):
    consultas = []

    def _registrar(_con, _cursor, sql, *_args):
        if sql.lstrip().upper().startswith("SELECT"):
            consultas.append(sql)

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", _registrar)
    yield consultas
    event.remove(engine, "before_cursor_execute", _registrar)


def test_exibir_formulario_faz_no_maximo_duas_consultas(client, dados, relogio,
                                                        contar_consultas):
    client.get(f"/presenca/{dados['token']}")
    assert len(contar_consultas) <= 2


def test_enviar_formulario_faz_no_maximo_duas_consultas(app, client, dados, relogio,
                                                        contar_consultas):
    texto = _texto(_enviar(client, dados))
    assert "Presença registrada com sucesso." in texto
    assert len(contar_consultas) <= 2


# --- sessão expirada (CSRF) ----------------------------------------------------

def test_token_csrf_invalido_devolve_formulario_preenchido(tmp_path, relogio):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "teste",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
    })
    assert app.config["WTF_CSRF_TIME_LIMIT"] is None
    with app.app_context():
        atividade = Atividade(
            tipo_evento=TipoEvento(nome="META"), titulo="Palestra",
            modalidade="palestra", data=DIA, hora_inicio=time(14, 0),
            hora_fim=time(15, 0), fecha_em=fechamento_padrao(DIA))
        curso = CursoTurma(nome="Informática 1A")
        db.session.add_all([atividade, curso])
        db.session.commit()
        token, curso_id = atividade.token, curso.id

    resposta = app.test_client().post(f"/presenca/{token}", data={
        "csrf_token": "expirado", "nome": "Maria", "matricula": "123",
        "curso_turma_id": str(curso_id), "email": "m@b.br", "descricao": DESCRICAO})
    texto = _texto(resposta)
    assert resposta.status_code == 200
    assert "Sua sessão expirou. Confira os dados e envie novamente." in texto
    assert 'value="Maria"' in texto
    assert DESCRICAO.strip() in texto
    with app.app_context():
        assert db.session.query(Resposta).count() == 0
        db.session.remove()
        db.engine.dispose()
