# Sistema de Presença em Eventos Acadêmicos – CEFET-MG Campus Varginha

Documento de requisitos para desenvolvimento. O sistema registra a presença de alunos
em atividades (palestras, apresentações de trabalho, minicursos) dos eventos acadêmicos
do campus, como a META e a Semana de Ciência e Tecnologia. O aluno lê um QR Code na sala
e preenche um formulário curto, disponível somente no dia da atividade.

Princípio geral: **simplicidade**. Nada de filas, tarefas agendadas, APIs externas ou
dependências que exijam configuração especial no servidor.

---

## 1. Tecnologia e implantação

- Python 3.11+ com Flask
- Flask-SQLAlchemy com SQLite (um único arquivo `.db`)
- Flask-Login para autenticação dos administradores (senhas com hash)
- Flask-WTF para formulários e proteção CSRF
- Templates Jinja2 com Bootstrap 5 via CDN; interface responsiva, pensada para celular
  (tema e layout na seção 7)
- `openpyxl` para importar e exportar planilhas
- `qrcode[pil]` para gerar os QR Codes e `reportlab` para o PDF de impressão
- Hospedagem no **PythonAnywhere**, sem Docker:
  - aplicação exposta via WSGI (`wsgi.py` com o objeto `app`)
  - caminho do banco definido por variável de ambiente, com padrão absoluto relativo à pasta do projeto
  - atualização por `git pull` + botão "Reload" no painel
- Fuso horário: `America/Sao_Paulo`. O servidor roda em UTC, então toda comparação de
  data/hora deve usar `zoneinfo` explicitamente.
- Nenhum processo em segundo plano: a janela de abertura/fechamento é verificada no
  momento de cada requisição.
- SQLite preparado para gravações simultâneas (a aplicação pode rodar com mais de um
  web worker): em cada nova conexão, executar `PRAGMA journal_mode=WAL` e
  `PRAGMA busy_timeout=5000`, via evento `connect` do SQLAlchemy. Transações de escrita
  curtas, com commit imediato após gravar a resposta.

## 2. Perfis de usuário

- **Aluno**: não faz login. Acessa o formulário pelo QR Code da atividade.
- **Administrador**: faz login. Todos os administradores têm o mesmo nível de acesso.
  - O primeiro administrador é criado por comando de linha: `flask criar-admin`.
  - Depois disso, qualquer administrador pode cadastrar, desativar e redefinir a senha
    de outros administradores pela interface.

## 3. Requisitos funcionais

### Área do administrador

- **RF01 – Login e logout** de administradores.
- **RF02 – Tipos de evento**: cadastrar, editar e desativar (ex.: META, Semana C&T).
  Campos: nome, ativo. O evento é identificado apenas pelo nome, que deve incluir a
  edição e o ano (ex.: "35ª META 2026"); não pode haver dois tipos com o mesmo nome.
- **RF03 – Cursos/turmas**: cadastrar, editar e desativar os itens que aparecem na
  lista do formulário do aluno. Campos: nome, ativo.
- **RF04 – Atividades**: cadastrar, editar, listar e excluir. Campos: tipo de evento,
  título, modalidade (palestra, apresentação de trabalho, minicurso, outra), data,
  hora de início, local, pessoas envolvidas (texto livre). Não há hora de término (A3);
  a hora de início é apenas informativa e serve para ordenar as listagens.
  - Listagem com filtros por tipo de evento, data e modalidade.
  - Atividade que já possui respostas não pode ser excluída, apenas editada.
- **RF05 – Prorrogação de prazo**: na edição da atividade, o administrador pode alterar
  a data/hora de fechamento do formulário.
- **RF06 – Importação de planilha XLSX** com atividades (formato na seção 6):
  - botão para baixar o modelo em branco;
  - pré-visualização com validação linha a linha antes de gravar;
  - linhas com erro são listadas com o motivo; o administrador confirma a importação
    apenas das linhas válidas;
  - tipo de evento inexistente é criado automaticamente na importação.
- **RF07 – QR Code individual**: baixar a imagem PNG do QR Code de uma atividade.
- **RF08 – Folha de QR Codes em PDF** (A1): gerar um PDF com as atividades filtradas
  (ex.: todas de um evento), uma atividade por página A4. Cada página traz, de cima
  para baixo: nome do evento (ex.: "35ª META 2026"), título da atividade (ex.:
  "Palestra XXXXX"), data da atividade e, abaixo, o QR Code em tamanho grande. Nada
  mais é impresso (sem horário, local, envolvidos, instrução ou link).
- **RF09 – Relatório de presença por atividade** (exportado em XLSX): nome, matrícula,
  curso/turma, e-mail, descrição e data/hora do envio.
- **RF10 – Relatório consolidado por curso/turma** (exportado em XLSX, A2): com filtro
  opcional por tipo de evento; uma aba por curso/turma com a lista de todos os alunos
  que registraram presença, em ordem alfabética de nome. Colunas: nome, matrícula,
  evento, atividades (texto único com as atividades em ordem de data, no formato
  "DD/MM/AAAA – Título", separadas por "; ") e quantidade de atividades. Uma linha
  por aluno e evento: a quantidade conta só as atividades daquele evento.
- **RF11 – Pesquisa por aluno** (tela, sem exportação): busca por nome ou matrícula;
  exibe as atividades em que o aluno registrou presença, com data e tipo de evento.
- **RF12 – Visualização de respostas**: o administrador pode ver as respostas de cada
  atividade, mas **não pode editá-las nem excluí-las**.

### Área pública (aluno)

- **RF13 – Formulário de presença** em `/presenca/<token>`, exibindo tipo de evento,
  título, data, hora de início e local da atividade. Campos, todos obrigatórios:
  - nome completo;
  - matrícula;
  - curso/turma (lista com os itens ativos do RF03);
  - e-mail;
  - descrição do que achou da atividade.
- **RF14 – Confirmação** após o envio, com mensagem de sucesso e resumo do que foi
  registrado.
- **RF15 – Mensagens de indisponibilidade**: "Formulário ainda não aberto" (antes do
  dia da atividade, informando a data em que abre) ou "Prazo encerrado" (após o
  fechamento).

## 4. Regras de negócio

- **RN01** – O formulário abre à 00h00 da data da atividade (A3), independentemente
  da hora de início. O "fecha em" deve ser posterior a esse momento.
- **RN02** – Por padrão, o formulário fecha às 23h59 do dia da atividade. O campo
  "fecha em" é preenchido automaticamente no cadastro e na importação e pode ser
  alterado pelo administrador (RF05).
- **RN03** – A janela de tempo é validada no servidor no envio, e não apenas ao exibir
  a página.
- **RN04** – Apenas uma resposta por matrícula em cada atividade. Uma segunda tentativa
  exibe aviso amigável de que a presença já foi registrada.
- **RN05** – A matrícula é normalizada antes de gravar e comparar (remover espaços,
  pontos e traços).
- **RN06** – A descrição exige um número mínimo de caracteres, configurável em um
  único lugar (padrão: 100). O formulário mostra um contador de caracteres.
- **RN07** – A matrícula não é validada contra lista de alunos; o sistema aceita o que
  for digitado.
- **RN08** – Cada atividade tem um token público aleatório (UUID) usado na URL do QR
  Code. O ID interno do banco nunca aparece na URL pública.
- **RN09** – Cada resposta registra data/hora do envio e endereço IP (apenas para
  consulta, sem bloqueio).

## 5. Modelo de dados

```
Administrador: id, nome, email (único), senha_hash, ativo
TipoEvento:    id, nome, ativo
CursoTurma:    id, nome, ativo
Atividade:     id, tipo_evento_id, titulo, modalidade, data, hora_inicio,
               local, envolvidos, token (único), fecha_em
Resposta:      id, atividade_id, nome, matricula, curso_turma_id, email,
               descricao, enviado_em, ip
               restrição única: (atividade_id, matricula)
```

## 6. Planilha de importação de atividades (XLSX)

Primeira linha com os cabeçalhos exatamente como abaixo; uma atividade por linha.

```
tipo_evento | atividade | modalidade   | data       | hora_inicio | local   | envolvidos
META        | Ecoara... | apresentacao | 20/10/2026 | 14:00       | Sala 12 | Fulano, Beltrana
```

- `modalidade`: palestra, apresentacao, minicurso ou outra (sem diferenciar maiúsculas
  e acentos).
- `data`: DD/MM/AAAA ou célula de data do Excel.
- `hora_inicio`: HH:MM ou célula de hora do Excel.
- `local` e `envolvidos` podem ficar em branco; os demais são obrigatórios.
- Planilhas antigas com a coluna `hora_fim` continuam aceitas: a coluna é ignorada (A3).

## 7. Layout e identidade visual

Visual simples, limpo e institucional: fundo branco, azul como cor principal, cinza para
textos e bordas e laranja apenas como detalhe. Nenhum gradiente, sombra decorativa ou
animação de entrada.

### Paleta

```
Branco (fundo)            #FFFFFF
Azul (principal)          #1F4E79   nome do sistema, botões, links, foco dos campos
Azul escuro (hover)       #173D60   estado hover/ativo dos botões
Azul suave (apoio)        #EEF3F8   fundo do bloco de informações da atividade
Cinza texto               #2F3A45   texto principal
Cinza apoio               #6B7785   textos secundários, rodapé, legendas
Cinza borda               #DDE2E8   bordas de campos, divisórias, borda do rodapé
Laranja (detalhe)         #D9822B   linha sob o cabeçalho e borda do aviso de prazo
```

Regras de uso das cores:

- O laranja **nunca** é usado como cor de texto, porque não tem contraste suficiente
  sobre fundo branco. Aparece só em linhas e bordas, e em no máximo dois elementos:
  a linha inferior do cabeçalho e a borda lateral do aviso de prazo no formulário.
- Botões principais em azul com texto branco; botões secundários com contorno azul.
- Mensagens de erro e sucesso usam os alertas padrão do Bootstrap.

### Tipografia

- Fonte **Source Sans 3** (Google Fonts, pesos 400, 600 e 700), com fallback
  `"Segoe UI", Roboto, Arial, sans-serif`.
- Texto base de 16px no celular e no computador; títulos em azul, peso 600.
- Textos de botões e títulos com inicial maiúscula apenas na primeira palavra
  (ex.: "Registrar presença"), sem caixa alta.

### Estrutura comum a todas as páginas

Todas as páginas herdam de um único template `base.html` com:

- **Cabeçalho** com fundo branco e linha inferior laranja de 3px, contendo em duas
  linhas: "CEFET-MG Campus Varginha" (azul, negrito) e "Eventos Institucionais" (cinza).
  Na área do administrador, o cabeçalho também traz o menu de navegação à direita,
  que vira menu recolhível no celular (navbar do Bootstrap).
- **Conteúdo** com espaçamento vertical generoso.
- **Rodapé** com borda superior cinza, texto pequeno em cinza apoio:
  - Av. dos Imigrantes, 1000 - Bairro Vargem - Varginha - MG - Brasil - Cep: 37.022-560
  - Telefone: +55 (35) 3690-4200 (com link `tel:` para ligar direto do celular)
- O rodapé fica sempre no fim da tela, mesmo em páginas curtas.

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block titulo %}Eventos Institucionais{% endblock %} - CEFET-MG Campus Varginha</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap">
  <link rel="stylesheet" href="{{ url_for('static', filename='tema.css') }}">
</head>
<body class="d-flex flex-column min-vh-100">
  <header class="site-header">
    <div class="container d-flex justify-content-between align-items-center flex-wrap gap-2">
      <div class="marca">
        <span class="marca-instituicao">CEFET-MG Campus Varginha</span>
        <span class="marca-sistema">Eventos Institucionais</span>
      </div>
      {% block navegacao %}{% endblock %}
    </div>
  </header>

  <main class="flex-grow-1 py-4">
    <div class="container">
      {% block conteudo %}{% endblock %}
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>Av. dos Imigrantes, 1000 - Bairro Vargem - Varginha - MG - Brasil - Cep: 37.022-560</p>
      <p>Telefone: <a href="tel:+553536904200">+55 (35) 3690-4200</a></p>
    </div>
  </footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

### Arquivo de tema (`static/tema.css`)

Personaliza o Bootstrap por variáveis, sem sobrescrever componentes inteiros.

```css
:root {
  --cor-azul: #1F4E79;
  --cor-azul-escuro: #173D60;
  --cor-azul-suave: #EEF3F8;
  --cor-cinza-texto: #2F3A45;
  --cor-cinza-apoio: #6B7785;
  --cor-cinza-borda: #DDE2E8;
  --cor-laranja: #D9822B;

  --bs-body-bg: #FFFFFF;
  --bs-body-color: var(--cor-cinza-texto);
  --bs-body-font-family: "Source Sans 3", "Segoe UI", Roboto, Arial, sans-serif;
  --bs-border-color: var(--cor-cinza-borda);
  --bs-link-color-rgb: 31, 78, 121;
  --bs-link-hover-color-rgb: 23, 61, 96;
}

h1, h2, h3 { color: var(--cor-azul); font-weight: 600; }

.site-header {
  background: #FFFFFF;
  border-bottom: 3px solid var(--cor-laranja);
  padding: 0.85rem 0;
}
.marca { display: flex; flex-direction: column; line-height: 1.25; }
.marca-instituicao { color: var(--cor-azul); font-weight: 700; font-size: 1.1rem; }
.marca-sistema { color: var(--cor-cinza-apoio); font-size: 0.95rem; }

.site-footer {
  border-top: 1px solid var(--cor-cinza-borda);
  color: var(--cor-cinza-apoio);
  font-size: 0.875rem;
  padding: 1.25rem 0;
}
.site-footer p { margin: 0.15rem 0; }
.site-footer a { color: var(--cor-cinza-apoio); }

.btn-primary {
  --bs-btn-bg: var(--cor-azul);
  --bs-btn-border-color: var(--cor-azul);
  --bs-btn-hover-bg: var(--cor-azul-escuro);
  --bs-btn-hover-border-color: var(--cor-azul-escuro);
  --bs-btn-active-bg: var(--cor-azul-escuro);
  --bs-btn-active-border-color: var(--cor-azul-escuro);
}
.btn-outline-primary {
  --bs-btn-color: var(--cor-azul);
  --bs-btn-border-color: var(--cor-azul);
  --bs-btn-hover-bg: var(--cor-azul);
  --bs-btn-hover-border-color: var(--cor-azul);
}

.form-control:focus,
.form-select:focus {
  border-color: var(--cor-azul);
  box-shadow: 0 0 0 0.2rem rgba(31, 78, 121, 0.2);
}

/* Área pública: coluna única e estreita */
.conteudo-publico { max-width: 640px; margin: 0 auto; }

/* Bloco com título, data, horário e local da atividade */
.info-atividade {
  background: var(--cor-azul-suave);
  border-radius: 6px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
}

/* Aviso "Formulário disponível até hoje às 23h59" */
.aviso-prazo {
  border-left: 3px solid var(--cor-laranja);
  padding: 0.5rem 0.9rem;
  color: var(--cor-cinza-texto);
  margin-bottom: 1.5rem;
}

.contador-caracteres { color: var(--cor-cinza-apoio); font-size: 0.875rem; }
.contador-caracteres.ok { color: var(--cor-azul); }
```

### Páginas públicas (aluno)

- Coluna única centralizada, com largura máxima de 640px; no celular ocupa a tela toda.
- Ordem no formulário: bloco de informações da atividade (tipo de evento, título, data,
  hora de início e local), aviso de prazo, campos, contador de caracteres sob a descrição,
  botão "Registrar presença" com largura total no celular.
- Aviso de privacidade (LGPD) em texto pequeno cinza, logo acima do botão.
- Páginas de confirmação, "ainda não aberto" e "prazo encerrado" seguem o mesmo
  layout, com o bloco de informações da atividade no topo.

### Páginas do administrador

- Container padrão do Bootstrap, alinhado à esquerda.
- Menu: Atividades, Tipos de evento, Cursos/turmas, Importar planilha, Relatórios,
  Administradores, Sair.
- Listagens em tabelas simples (`table table-sm table-hover`) dentro de
  `table-responsive`, com filtros acima da tabela.
- A tela de login usa o mesmo layout estreito das páginas públicas.

## 8. Requisitos não funcionais

- Formulário do aluno leve, legível e utilizável em celular com tela pequena.
- Aviso curto no formulário sobre a finalidade da coleta dos dados (LGPD): registro de
  presença e emissão de certificados/comprovação de participação.
- Testes automatizados (pytest) para: janela de tempo (RN01–RN03), unicidade da
  resposta (RN04), normalização da matrícula (RN05) e importação da planilha (RF06).
- **Desempenho no pico**: o sistema deve suportar cerca de 130 atividades e várias
  turmas enviando respostas ao mesmo tempo ao fim das atividades. Para isso:
  - a rota pública (exibir e enviar formulário) faz no máximo duas consultas simples ao
    banco e nenhum processamento pesado;
  - Bootstrap e fonte vêm de CDN; o `tema.css` é servido pelo mapeamento de arquivos
    estáticos do PythonAnywhere (aba Web > Static files), sem passar pelo web worker;
  - nenhuma operação da área pública depende de gerar PDF, planilha ou imagem.
- **Operações pesadas** (PDF de QR Codes, exportações XLSX, importação de planilha) são
  feitas pelo administrador fora do horário de término das atividades. A tela que dispara
  essas operações exibe um aviso curto recomendando isso.
- `README.md` com passo a passo de instalação local e de implantação no PythonAnywhere,
  incluindo uma seção "Antes do evento" com:
  - recomendação de usar um plano pago com mais de um web worker durante o mês do evento
    e, se usar o plano gratuito, conferir a data de expiração do web app e renová-lo;
  - geração antecipada de todos os PDFs de QR Code;
  - teste de carga simples: uma turma inteira acessa e envia o formulário de uma
    atividade de teste ao mesmo tempo.
- `requirements.txt` com versões fixadas.

## 9. Fora do escopo

- Login de alunos ou validação de matrícula contra lista oficial.
- Emissão de certificados.
- Cálculo de carga horária (os relatórios mostram apenas a contagem de atividades).
- Perfis de administrador com permissões diferentes.
- Edição ou exclusão de respostas de alunos.
- QR Code rotativo ou código de sala.

## 10. Ordem sugerida de desenvolvimento

1. Estrutura do projeto, `base.html` e `tema.css` (seção 7), modelos, comando
   `flask criar-admin` e login.
2. CRUD de tipos de evento, cursos/turmas e atividades.
3. Formulário público com janela de tempo e regras RN01–RN06, com testes.
4. QR Code individual e PDF de impressão.
5. Importação de planilha com pré-visualização.
6. Relatórios e pesquisa por aluno.
7. README e ajustes para o PythonAnywhere.
8. Alterações após a implantação (seção 11).

## 11. Alterações após a implantação

Pedidas depois da primeira implantação. As seções acima já estão atualizadas; esta
lista registra o que mudou em relação à versão implantada.

- **A1 – PDF de QR Codes (RF08)**: uma atividade por página A4 com nome do evento,
  título da atividade, data e o QR Code abaixo. Saem da página o horário, o local, os
  envolvidos, a instrução de leitura e o link.
- **A2 – Consolidado por curso/turma (RF10)**: em vez de uma coluna por atividade
  marcada com "X", cada aba (uma por curso/turma) lista os alunos com nome, matrícula,
  evento, atividades em uma única coluna de texto concatenado e quantidade de
  atividades. Sem filtro de evento, o aluno tem uma linha para cada evento em que
  registrou presença. O e-mail sai deste relatório (continua no RF09). A aba "Resumo"
  permanece.
- **A3 – Fim da hora de término**:
  - o campo `hora_fim` sai do cadastro, da edição, da listagem, do formulário público,
    do PDF, da planilha modelo e da importação;
  - o formulário passa a abrir à 00h00 da data da atividade (RN01); o fechamento
    padrão continua às 23h59 do mesmo dia (RN02);
  - a importação aceita e ignora a coluna `hora_fim` em planilhas antigas;
  - o banco em produção já tem a coluna `hora_fim` (obrigatória). Um comando
    `flask --app wsgi atualizar-banco` remove a coluna (`ALTER TABLE ... DROP
    COLUMN`); é idempotente e deve ser rodado após o `git pull`, depois de uma cópia
    de segurança do banco. O README documenta esse passo.
