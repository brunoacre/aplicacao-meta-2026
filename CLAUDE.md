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

- [ ] 1. Estrutura, base.html, tema.css, modelos, criar-admin e login
- [ ] 2. CRUD de tipos de evento, cursos/turmas e atividades
- [ ] 3. Formulário público com janela de tempo e regras RN01–RN06
- [ ] 4. QR Code individual e PDF de impressão
- [ ] 5. Importação de planilha com pré-visualização
- [ ] 6. Relatórios e pesquisa por aluno
- [ ] 7. README e ajustes para o PythonAnywhere
