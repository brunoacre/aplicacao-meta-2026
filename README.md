# Eventos Institucionais – CEFET-MG Campus Varginha

Sistema web para registrar a presença de alunos nas atividades dos eventos acadêmicos
do campus (META, Semana C&T etc.). O aluno lê o QR Code na sala e preenche um
formulário curto, disponível apenas no dia da atividade. Os administradores cadastram
as atividades (ou importam de planilha), imprimem os QR Codes e exportam os relatórios
de presença.

A especificação completa está em [`docs/SPEC.md`](docs/SPEC.md).

**Stack:** Python 3.11+, Flask, Flask-SQLAlchemy (SQLite em modo WAL), Flask-Login,
Flask-WTF, Bootstrap 5 via CDN, openpyxl, qrcode, reportlab e pytest.

---

## Instalação local

```bash
git clone https://github.com/brunoacre/aplicacao-meta-2026.git app-meta
cd app-meta
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app wsgi criar-admin       # cria o primeiro administrador
flask --app wsgi run --debug       # http://127.0.0.1:5000/admin/
```

O banco é criado automaticamente em `instance/eventos.db` na primeira execução.

Para rodar os testes:

```bash
pytest
```

## Variáveis de ambiente

Todas são opcionais. Os valores padrão servem para uso local.

| Variável      | Para que serve | Padrão |
|---------------|----------------|--------|
| `URL_PUBLICA` | Endereço público do site, com `https://` (ex.: `https://usuario.pythonanywhere.com`). É usado para montar o link gravado nos QR Codes. **Defina em produção:** sem ela, o link é montado a partir da requisição e, atrás do proxy do PythonAnywhere, pode sair como `http://`. Quando começa com `https://`, os cookies passam a ser enviados só por https. | vazio |
| `SECRET_KEY`  | Chave usada para assinar a sessão e os formulários. | gerada na primeira execução e guardada em `instance/secret_key` |
| `EVENTOS_DB`  | Caminho **absoluto** do arquivo do banco SQLite. | `instance/eventos.db` na pasta do projeto |

> A pasta `instance/` (banco, chave e planilhas aguardando importação) não vai para o
> git. Não apague essa pasta no servidor.

---

## Implantação no PythonAnywhere

Nos exemplos, troque `usuario` pelo seu nome de usuário no PythonAnywhere.

### 1. Código e ambiente virtual

Em um console **Bash** do PythonAnywhere:

```bash
git clone https://github.com/brunoacre/aplicacao-meta-2026.git ~/app-meta
cd ~/app-meta
python3.11 -m venv .venv           # ou uma versão mais nova disponível
source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi criar-admin
```

### 2. Web app

Na aba **Web**:

1. **Add a new web app** → **Manual configuration** → mesma versão do Python do
   ambiente virtual.
2. **Virtualenv:** `/home/usuario/app-meta/.venv`
3. **Source code** e **Working directory:** `/home/usuario/app-meta`
4. **Static files:** URL `/static/` → diretório `/home/usuario/app-meta/app/static/`.
   Assim o `tema.css` é servido sem ocupar o web worker.
5. **Force HTTPS:** ativado.

### 3. Arquivo WSGI

Ainda na aba **Web**, abra o link do **WSGI configuration file**
(`/var/www/usuario_pythonanywhere_com_wsgi.py`), apague o conteúdo de exemplo e deixe
apenas:

```python
import os
import sys

PROJETO = "/home/usuario/app-meta"
if PROJETO not in sys.path:
    sys.path.insert(0, PROJETO)

os.environ["URL_PUBLICA"] = "https://usuario.pythonanywhere.com"

from wsgi import app as application  # noqa: E402
```

Clique em **Reload** e acesse `https://usuario.pythonanywhere.com/admin/`.

> Se definir `EVENTOS_DB` ou `SECRET_KEY` no arquivo WSGI, defina os mesmos valores no
> console (por exemplo, com `export` no `~/.bashrc`). Sem isso, comandos como
> `flask --app wsgi criar-admin` usam outro banco. Com os valores padrão, nada disso é
> necessário.

### 4. Conferir o modo WAL

O disco do PythonAnywhere é um sistema de arquivos em rede. Depois da primeira
execução, confira se o banco ficou em modo WAL:

```bash
cd ~/app-meta
python -c "import sqlite3; print(sqlite3.connect('instance/eventos.db').execute('PRAGMA journal_mode').fetchone()[0])"
```

O resultado esperado é `wal`. O teste de carga da seção "Antes do evento" confirma, na
prática, que as gravações simultâneas funcionam.

### Atualizar o sistema

Antes de atualizar, faça uma cópia do banco (seção abaixo). Depois:

```bash
cd ~/app-meta
git pull
source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi atualizar-banco
```

O comando `atualizar-banco` ajusta o banco às mudanças da nova versão (por exemplo, a
retirada da hora de término das atividades). Pode ser rodado sempre: quando não há nada
a ajustar, ele só avisa que o banco já está atualizado.

Depois, clique em **Reload** na aba **Web**.

### Cópia de segurança do banco

Por causa do modo WAL, **não copie só o arquivo `.db`**: parte dos dados pode estar no
arquivo `eventos.db-wal`. Use o comando de backup do SQLite, que gera uma cópia
consistente mesmo com o sistema no ar:

```bash
cd ~/app-meta
mkdir -p ~/backups
sqlite3 instance/eventos.db ".backup $HOME/backups/eventos-$(date +%F).db"
```

Faça uma cópia antes de cada atualização e ao fim de cada dia de evento.

---

## Antes do evento

No mês do evento, cerca de 130 atividades terminam em poucos horários, e turmas
inteiras enviam o formulário ao mesmo tempo.

1. **Plano do PythonAnywhere.**
   - Use um **plano pago com mais de um web worker** durante o mês do evento. Com um
     só worker, os envios ficam em fila e o formulário fica lento no pico.
   - Se usar o **plano gratuito**, confira na aba **Web** a data de expiração do web
     app e renove-o pelo botão da própria aba, garantindo que a data fique **depois**
     do último dia do evento.
2. **Gerar todos os PDFs de QR Code com antecedência.**
   - Em **Tipos de evento**, use o atalho de PDF do evento ou, em **Atividades**,
     filtre e gere o PDF.
   - Gere, confira e imprima antes do evento. Se reimprimir, faça isso fora dos
     horários de término das atividades: PDF, exportações e importação são operações
     pesadas.
   - Confira se o link do QR Code começa com `https://` (variável `URL_PUBLICA`).
3. **Teste de carga simples.**
   1. Cadastre um tipo de evento só para o teste (ex.: "Teste de carga 2026") e uma
      atividade com início no horário do teste. Use esse tipo separado porque
      atividades com respostas não podem ser excluídas.
   2. Imprima ou projete o QR Code da atividade.
   3. Peça a uma turma inteira que leia o QR Code e envie o formulário **ao mesmo
      tempo**.
   4. Confira:
      - em **Atividades → respostas**, se o número de respostas é igual ao de alunos
        que enviaram;
      - se nenhum aluno recebeu página de erro e se o envio foi rápido;
      - na aba **Web → Log files → error log**, se não há erros (principalmente
        `database is locked`).
   5. Depois do teste, desative o tipo de evento de teste.
4. **Cadastros.** Confira se os cursos/turmas ativos estão corretos: são as opções que
   aparecem para o aluno.
5. **Backup.** Faça uma cópia do banco (seção acima) antes do primeiro dia.
