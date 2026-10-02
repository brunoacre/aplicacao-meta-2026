# Sistema de Presença em Eventos – CEFET-MG Campus Varginha

Sistema web para registrar a presença de alunos em atividades dos eventos acadêmicos
do campus (META, Semana C&T etc.) por meio de QR Code e formulário curto.

**A especificação completa está em `docs/SPEC.md`.** Leia as seções relevantes antes
de iniciar qualquer etapa e siga-a como fonte da verdade. Se algo no código precisar
divergir do SPEC, pergunte antes.

## Stack (não trocar sem perguntar)

- Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- SQLite em modo WAL (ver SPEC seção 1)
- Jinja2 + Bootstrap 5 via CDN + `static/tema.css` (ver SPEC seção 7)
- openpyxl, qrcode[pil], reportlab
- pytest
- Implantação no PythonAnywhere via WSGI. **Sem Docker.**

## Estrutura do projeto

```
app/
  __init__.py        # create_app(), configuração, extensões, pragmas do SQLite
  models.py
  publico/           # blueprint do formulário do aluno (/presenca/<token>)
  admin/             # blueprint da área administrativa
  servicos/          # janela de tempo, normalização, importação, QR, PDF, relatórios
  templates/         # base.html + templates por blueprint
  static/tema.css
tests/
docs/SPEC.md
wsgi.py
requirements.txt
```

## Comandos

- Ambiente: `python -m venv .venv` e `pip install -r requirements.txt`
- Rodar localmente: `flask --app wsgi run --debug`
- Criar administrador: `flask --app wsgi criar-admin`
- Testes: `pytest`

## Convenções

- Nomes de modelos, campos, rotas, templates e mensagens em português, como no SPEC.
- Regras de negócio ficam em `app/servicos/`, nunca espalhadas nas rotas.
- Datas e horas sempre com `zoneinfo.ZoneInfo("America/Sao_Paulo")`; nunca
  `datetime.now()` sem fuso.
- Toda rota do admin exige login.
- Textos da interface em sentence case e com verbo nos botões ("Registrar presença").
- Não adicionar dependências fora da stack sem perguntar; manter `requirements.txt`
  com versões fixadas.

## Forma de trabalho

- Seguir a ordem da seção 10 do SPEC, **uma etapa por vez**.
- Antes de codificar uma etapa, apresentar um plano curto e aguardar aprovação.
- Ao terminar uma etapa: rodar `pytest`, garantir que tudo passa e atualizar o
  status abaixo.

## Status das etapas

- [x] 1. Estrutura, base.html, tema.css, modelos, criar-admin e login
- [x] 2. CRUD de tipos de evento, cursos/turmas e atividades
- [x] 3. Formulário público com janela de tempo e regras RN01–RN06
- [x] 4. QR Code individual e PDF de impressão
  - PDF por filtros da listagem (atalho por evento na tela de tipos de evento);
    página com evento, título, data/horário, local, envolvidos e QR Code.
- [x] 5. Importação de planilha com pré-visualização
  - O evento é identificado só pelo **nome** (ex.: "35ª META 2026"); o modelo
    não tem campo de ano. Nome de tipo de evento é único (sem diferenciar
    maiúsculas e espaços extras).
  - Duplicidade (cadastro e importação): nome do evento + título da atividade,
    sem diferenciar maiúsculas e espaços extras (`servicos/cadastros.py`).
- [x] 6. Relatórios e pesquisa por aluno (inclui o RF12, adiado da etapa 2)
  - Consolidado (RF10): aluno identificado pela matrícula; quem informou turmas
    diferentes aparece em cada aba, contando só as atividades daquela turma
    (validar manualmente com dados reais). Nome/e-mail da resposta mais recente.
- [x] 7. README e ajustes para o PythonAnywhere
  - README documenta `URL_PUBLICA` (endereço https usado nos QR Codes; sem ela o
    link pode sair como http atrás do proxy), `SECRET_KEY` e `EVENTOS_DB`.
  - Sem `SECRET_KEY`, a chave é gerada e guardada em `instance/secret_key`.
  - `URL_PUBLICA` com https ativa cookies seguros (sessão e "lembrar-me").
