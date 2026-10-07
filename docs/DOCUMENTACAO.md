# SISTEMA DE ENVIO PORTO SEGURO

Documentação para desenvolvedores. Última atualização: 21/08/2026.

## 1. O que é

Sistema desktop (Python + customtkinter) do Grupo Fedcorp que reúne, num
menu único, as rotinas de geração e envio de planilhas relacionadas à
Porto Seguro. Hoje tem dois módulos:

| Módulo | Objetivo |
|---|---|
| **SUBGRUPOS DE VIDA** | Gerar o relatório Excel de segurados de Vida por subgrupo/vigência e conferir inconsistências de apólices sem subgrupo. |
| **PORTO ASSISTÊNCIA** | Gerar a relação mensal de segurados dos produtos Residencial (1), Auto (2) e Empresarial (3) e enviá-la por SFTP para a Porto Seguro. |

Estes módulos migrarão no futuro para o **FedHub-Backend**
(github.com/Fedcorp-Desenvolvimentos/FedHub-Backend), rodando na web como
um módulo FastAPI (decisão do usuário, 08/2026: migrar tudo — inclusive os
placeholders Dental — com uma página simples servida pelo próprio backend).
Como preparação, a camada de conexão local já foi alinhada ao modelo do
FedHub (ver §6): credenciais em `.env` e pool de conexões em `db.py`. Os
módulos chamam `db.conectar()` e não dependem de detalhes da conexão.
O passo a passo da migração web está em `docs/PLANO-WEB.md`.

## 2. Como rodar

```
cd U:\--2021\04-EnvioPorto
pip install -r requirements.txt
python main.py
```

Requisitos: Python 3.12+ (desenvolvido no 3.14), acesso à rede interna
(Firebird em 192.168.0.6) e, para o envio, saída para a internet na porta
2022. O `fdb` precisa do client do Firebird (`fbclient.dll`) instalado na
máquina — já presente nas estações que rodam os sistemas Delphi.

## 3. Estrutura de pastas

```
04-EnvioPorto\
│  main.py                  ← menu principal (ponto de entrada)
│  .env                     ← credenciais reais (NÃO versionar/copiar)
│  .env.exemplo             ← modelo do .env para clones novos
│  config.py                ← lê o .env e monta DB_CONFIG / SFTP_CONFIG
│  db.py                    ← db.conectar() com pool (modelo FedHub)
│  requirements.txt
│  porto_assistencia.json   ← preferências da tela (criado no 1º uso)
│
├─ modulos\
│    subgrupos_vida.py      ← módulo SUBGRUPOS DE VIDA (tela + lógica)
│    porto_assistencia.py   ← módulo PORTO ASSISTÊNCIA (tela)
│    gerador_porto.py       ← núcleo de geração do xlsx (sem tela)
│    envio_sftp.py          ← upload para o SFTP da Porto
│
├─ queries\                 ← SQLs do Porto Assistência (editáveis sem
│    codigo1_residencial.sql   mexer em código)
│    codigo2_auto.sql
│    codigo3_empresarial.sql
│
└─ docs\DOCUMENTACAO.md     ← este arquivo
```

## 4. Módulo SUBGRUPOS DE VIDA (`modulos/subgrupos_vida.py`)

Origem: era o sistema independente `U:\--2021\02-gerador_planilhas_firebird\main.py`.
Foi trazido para cá como janela filha do menu, com a lógica **intacta** —
só a classe virou `CTkToplevel` e a conexão passou a vir de `db.conectar()`.

Ajuste de tela a pedido do usuário (28/08/2026): os checkboxes de subgrupo
mostram o **código entre colchetes** no fim — `NOME DO SUBGRUPO [1234567]`
(a listagem passou a trazer também a coluna `SUBGRUPO`). É só informação
visual: antes da busca `WHERE NOME_SUBGRP = ?` o sufixo ` [código]` é
removido (regex em `processar`), então o critério de geração continua o
mesmo. Validado contra o banco: os 18 subgrupos resolvem para o código
correto após a limpeza.

### Fluxo "Gerar Planilha Excel" (`processar`)

1. Usuário escolhe a **data de vigência** no calendário (pré-preenchida com
   o dia 01 do mês anterior, editável) e marca um ou mais **subgrupos**
   (tabela `SUBGRUPOSEGURADORA`).
2. Limpa as tabelas temporárias `TEMP_RELATORIO_VIDA` e `TEMP_RELATORIO_VIDA2`.
3. Para cada subgrupo: busca as faturas ativas (`FATURAS` × `APOLICES`,
   `status='A'`, vigência cobrindo a data, `apo.subporto = subgrupo`) e,
   para cada fatura, executa a procedure **`GERA_REL_PLA_SISTEMA`**, que
   preenche `TEMP_RELATORIO_VIDA`; o resultado é acumulado em
   `TEMP_RELATORIO_VIDA2`.
4. Lê `TEMP_RELATORIO_VIDA2` junto com `VIDA_POSTOS` (nome do posto),
   formata as datas em dd/mm/aaaa e salva o Excel via "Salvar como"
   (nome sugerido: `Subgrupo_{id}_Relatorio_{data}.xlsx`).

Desde 07/10/2026 os passos 2 a 4 (menos o "Salvar como") vivem em
`_montar_dataframe`, reaproveitado pelo robô descrito abaixo.

### Robô noturno "Agendar Robô (todos os subgrupos)" (07/10/2026)

Botão roxo abaixo de "Ver Inconsistências". Abre uma janela onde o usuário
escolhe **data de vigência**, **pasta de destino** (`askdirectory`) e
**horário HH:MM**. Botões: *Agendar* (verde), *Executar agora* e *Cancelar
agendamento*. Se o horário já passou hoje, agenda para amanhã.

Como funciona:

- O miolo da geração (temp tables + procedure + leitura do DataFrame) foi
  extraído de `processar` para `_montar_dataframe(conn, data_firebird,
  nomes)`, **sem nenhuma janela**. O botão manual continua usando essa
  mesma função e depois abre o "Salvar como" — a lógica das queries está
  intacta, só mudou de lugar.
- O disparo usa `self.after(ms, ...)`; o id fica em `_id_after_robo` para
  cancelar. Na hora marcada, `_iniciar_robo` desabilita os botões e sobe
  uma `threading.Thread` com `_executar_robo` para a tela não congelar.
- A thread abre a própria conexão e, para **cada subgrupo da lista**
  (todos, independentemente dos checkboxes), chama `_montar_dataframe`
  com um único nome e salva `Subgrupo_{id}_Relatorio_{dd-mm-aaaa}.xlsx`
  na pasta. Subgrupo sem dados é só registrado; erro em um subgrupo faz
  `rollback` e segue para o próximo.
- Ao final grava/anexa `robo_log.txt` na pasta (início, fim, OK/VAZIO/ERRO
  por subgrupo) e deposita o resumo em `_fila_robo` (`queue.Queue`).
  `_vigiar_robo`, que roda na thread principal via `after(500)`, lê a fila
  e chama `_finalizar_robo` (reabilita botões, mostra o resumo). A thread
  **não toca em widgets nem chama `self.after()`** — isso foi testado e
  falha com "main thread is not in main loop" (tkinter não é thread-safe).
- Nome de subgrupo que não existe em `SUBGRUPOSEGURADORA` conta como ERRO
  no log (o `_montar_dataframe` devolve id "Varios" nesse caso).

Teste de 07/10/2026 (vigência 01/09/2026, janela oculta, 4 subgrupos:
CRASE SIGMA, CIPA, AP DE INCENDIO e um nome inexistente): 2 arquivos
gerados, 1 vazio, 1 erro, em 8 s; o Excel do robô tem as mesmas linhas
que o botão manual para o mesmo subgrupo. Script em
`scratchpad/teste_robo.py` da sessão (não versionado).

Limitações (avisadas na própria janela): o programa precisa ficar aberto e
o computador ligado, sem hibernar — `after()` não dispara com o PC dormindo.
Como as tabelas TEMP_* são compartilhadas, ninguém pode usar o módulo Vida
em outra máquina enquanto o robô roda. Se um dia precisar rodar com o
programa fechado, a saída é um script de linha de comando chamando
`_montar_dataframe` agendado pelo Agendador de Tarefas do Windows.

### Fluxo "Ver Inconsistências (Tela)" (`abrir_relatorio_tela`)

Lista em uma grade (Treeview) as faturas de Vida ativas do mês **sem
subgrupo preenchido** (`apo.subporto` nulo ou vazio), ignorando apólices
`C%` e `VR0001`. Serve para conferir cadastro antes de gerar o relatório.

> Correção de 07/10/2026: a query vinha do gerador antigo com um parêntese
> a menos na condição `((apo.subporto is null) or (apo.subporto=''))`, o que
> fazia o Firebird falhar com "Token unknown ... group" (SQLCODE -104).
> Foi só fechar o parêntese; a lógica não mudou.

### Observações técnicas

- As datas são passadas ao Firebird no formato `MM/DD/YYYY` (padrão que o
  servidor 2.5 aceita em literais).
- As tabelas TEMP_* são compartilhadas: **não rodar duas gerações ao mesmo
  tempo** em máquinas diferentes, pois uma limpa os dados da outra.
- As queries usam f-string (interpolação direta). Funciona, mas ao evoluir
  o módulo prefira parâmetros `?` como já é feito no SELECT de subgrupo.

## 5. Módulo PORTO ASSISTÊNCIA (`modulos/porto_assistencia.py`)

Substitui o processo manual de montar a planilha
`relacao-envio-porto-MMYYYY.xlsx` e subi-la por SFTP.

### Tela única

- **Pasta onde salvar** a planilha (persistida entre aberturas).
- **Data de início de vigência** — pré-preenchida com o **dia 01 do mês
  anterior**, editável. Alimenta o parâmetro `:inivig` de todas as queries
  e define a competência do nome do arquivo (`relacao-envio-porto-MMYYYY.xlsx`
  usa mês/ano dessa data).
- **Por produto** (Código 1 - Residencial, 2 - Auto, 3 - Empresarial):
  incluir ou não, e **Base toda** × **Quantidade N** — com N informado,
  somente as N primeiras linhas do resultado da query entram na aba.
- Checkbox **enviar por SFTP** após gerar.
- **Log em tela** com o total de linhas geradas por produto e o total geral.

As escolhas ficam em `porto_assistencia.json`. A geração roda em thread
para a janela não travar; o log é entregue por `queue.Queue`.

### Núcleo de geração (`modulos/gerador_porto.py`)

- A lista `PRODUTOS` define, por produto: código, **nome exato da aba** e
  colunas esperadas. **ATENÇÃO:** os nomes das abas reproduzem o modelo
  manual byte a byte — `"Código 2 - Auto "` tem espaço no final e
  `"Código 3 -  Empresarial"` tem espaço duplo. Não "corrigir": a Porto
  pode depender disso.
- As queries ficam em `queries/*.sql` e podem ser ajustadas sem tocar no
  código (fonte original: `querys-porto-assit.sql`, na raiz do projeto).
  Mapeamento query → aba:
  - `codigo1_residencial_1.sql` (residenciais sem a apólice 15008) e
    `codigo1_residencial_2.sql` (apólice 15008) → aba **Código 1 - Residencial**
    (as duas alimentam a mesma aba, em sequência);
  - `codigo2_auto.sql` (apólices `BOAT%` de `vida_segurados_mov`) → aba
    **Código 2 - Auto**;
  - `codigo3_empresarial.sql` (empresariais de `segurados_inc`) → aba
    **Código 3 - Empresarial**.
- **As três abas usam o mesmo layout de 12 colunas** (a pedido do usuário,
  08/2026): `ENDERECO`, `NUMERO`, `COMPLEMENTO`, `CEP`, `BAIRRO`, `CIDADE`,
  `SIGLAESTADO`, `NOME`, `CPF_CNPJ`, `DATANASCIMENTO`, `NOMEINQUILINO`,
  `CPFCNPJINQUILINO`. Colunas extras que as queries retornam (`PRODUTO`,
  `APOLICE`, `ADMINISTRADORA`, `ADM`) são ignoradas pelo gerador.
- Toda query usa o parâmetro **`:inivig`** (data de início de vigência).
  O gerador troca `:inivig` por `?` (estilo do driver fdb) e passa a data
  escolhida na tela. Cada query pode retornar colunas extras além das da
  aba; o gerador valida os aliases obrigatórios e reordena. Se o arquivo
  tiver o marcador `TODO`, a geração é recusada com mensagem clara.
- Com limite N e mais de uma query no produto, o limite vale para a soma:
  a segunda query só roda se ainda houver saldo.
- O Excel é escrito com `openpyxl` em modo `write_only` (rápido e leve
  mesmo com centenas de milhares de linhas); leitura do banco em blocos
  de 2.000 linhas (`FETCH_BLOCO`).
- Conexão com charset **WIN1252** (nomes/endereços têm acento).

### Envio SFTP (`modulos/envio_sftp.py`)

- Servidor: `sftp.portoseguro.com.br`, porta **2022**, destino
  `/Porto/Remessa` (dados em `SFTP_CONFIG`, no `config.py`).
- **DNS:** a rede local não resolve o hostname. O código testa o DNS e,
  se falhar, usa o IP de fallback (`131.161.97.122`, resolvido via DNS
  público — alias `mft.lb.portoseguro.com.br`). Se a Porto trocar o IP um
  dia, atualizar `SFTP_FALLBACK_IP` no `.env` (resolver com
  `nslookup sftp.portoseguro.com.br 8.8.8.8`).
- O upload sobe como `arquivo.part`, confere o tamanho e só então renomeia
  para o nome final — a Porto nunca vê arquivo incompleto. Qualquer falha
  vira exceção mostrada no log da tela.

### Estado atual

Queries reais instaladas e testadas contra o banco em 21/08/2026 (amostra
de 5 linhas por produto conferida contra a planilha manual de referência
`U:\PORTO SEGURO VIDA\relacao-envio-porto-042026.xlsx` — layout idêntico).

## 6. Banco de dados e camada de conexão

- Firebird **2.5** em `192.168.0.6`, arquivo `E:\SISTEMA\BASE_CHEQUE\BASE\FATURA.GDB`
  (mesmo banco dos sistemas Delphi legados).
- **Credenciais no `.env`** (27/08/2026 — modelo alinhado ao FedHub-Backend,
  `src/shared/database/connection_firebird.py` + `settings.py`). Os nomes
  das variáveis Firebird são os mesmos do FedHub (`FB_HOST`, `FB_PORT`,
  `FB_DATABASE`, `FB_USER`, `FB_PASSWORD`), para o mesmo `.env` servir na
  migração futura. O `config.py` (sem segredos) lê o `.env` e continua
  exportando `DB_CONFIG`/`SFTP_CONFIG` — a interface para os módulos não
  mudou. Variável ausente derruba o boot com mensagem clara (sem defaults
  para credenciais). Clone novo: `copy .env.exemplo .env` e preencher.
  **O `.env` está no `.gitignore` — nunca commitar.**
- **Pool de conexões** em `db.py`, copiado do FedHub: conexões ociosas
  ficam retidas (até `FB_POOL_SIZE`, padrão 5) e são reaproveitadas;
  `close()` devolve ao pool (com rollback) em vez de fechar; conexão ociosa
  é validada com `SELECT 1 FROM RDB$DATABASE` antes do reuso. Diferença em
  relação ao FedHub: como aqui os módulos usam charsets diferentes, existe
  **um pool por charset**.
- Charset: módulo Vida usa `ASCII` (comportamento herdado e validado);
  Porto Assistência usa `WIN1252`. `db.conectar(charset=...)` permite a
  escolha por chamada; o padrão vem de `FB_CHARSET` no `.env`.

## 7. Módulo GERA PORTO DENTAL (`modulos/porto_dental.py` + `modulos/gerador_dental.py`)

Spec completa (requisitos EARS com evidências, ajustes das queries e
validação): `docs/SPEC-PORTO-DENTAL.md`.

Fluxo em **duas etapas com ordem obrigatória** (decisão do usuário, 08/2026):

1. **Consultar Vidas** — o usuário define a pasta e a vigência (calendário
   pré-preenchido com o dia 01 do mês anterior) e roda a **query 1**
   (`queries/portodental_1.sql`, parâmetro `:inivig`). O log mostra cada
   linha retornada e o **TOTAL DE VIDAS A ENVIAR**. Contrato da query 1:
   deve retornar a coluna `FATURA` (alimenta a query 2); se houver coluna
   `VIDAS`, o totalizador soma essa coluna, senão conta as linhas.
2. **Gerar Planilha Final** — botão **liberado somente após a consulta**
   bem-sucedida. A **query 2** (`queries/portodental_2.sql`) roda alimentada
   pelos números de fatura da etapa 1: o marcador `:faturas` dentro de um
   `IN` é substituído em blocos de 1.000 (limite do `IN` no Firebird 2.5).
   A planilha segue **exatamente o formato da query 2** — as colunas do
   resultado viram o cabeçalho, na ordem da query. Colunas atuais: FATURA,
   APOLICE (código da apólice, `VSM.apolice`, incluída em 11/09/2026 a
   pedido do usuário), ADMINISTRADORA, NOME, NOME_POSTO, NOME_SEGURADO,
   CPF_CNPJ, SEXO, NASCIMENTO, NOME_MAE. Arquivo:
   `portodental-MMYYYY.xlsx` (competência da vigência), salvo na pasta
   escolhida (persistida em `porto_dental.json`).

A geração usa a vigência e as faturas **da consulta feita** (mudar o
calendário depois da etapa 1 não muda a etapa 2 — consulte de novo).
Conexão charset WIN1252. Queries reais instaladas em 27/08/2026 (fonte:
usuário; ajustes documentados no cabeçalho de cada `.sql`).

## 7b. Módulo GERAR DENTAL SEMPRE ODONTO (`modulos/dental_sempre_odonto.py`)

Idêntico ao GERA PORTO DENTAL (decisão do usuário, 28/08/2026): a classe
`JanelaDentalSempreOdonto` herda `JanelaPortoDental` trocando apenas os
parâmetros de produto (atributos de classe): título, `sempre_odonto.json`,
queries `sempreodonto_1.sql`/`sempreodonto_2.sql`, prefixo do arquivo
(`sempreodonto-MMYYYY.xlsx`) e nome da aba (`SEMPRE ODONTO`). A única
diferença de SQL é `AP.tipo_dental = 'S'` na query 1 (a query 2 é
idêntica — inclusive a coluna APOLICE acrescentada em 11/09/2026 nas duas). O motor é o mesmo `gerador_dental.py`, agora parametrizado
por `query_file`/`prefixo`/`aba`.

## 8. Como adicionar um novo módulo

1. Criar `modulos/nome_do_modulo.py` com uma classe `ctk.CTkToplevel`
   (usar `porto_assistencia.py` como referência de estrutura).
2. Usar `db.conectar()` para acessar o banco — nunca `fdb.connect` direto.
3. Registrar um botão no `main.py` chamando a nova janela.
4. Documentar o módulo neste arquivo (objetivo, fluxo, tabelas usadas).

## 9. Histórico

- **28/08/2026** — GERAR DENTAL SEMPRE ODONTO implementado como clone
  parametrizado do Porto Dental (`tipo_dental = 'S'`; nome SEMPRE ODONTO
  no título, aba e arquivo). Testado contra o banco (01/07/2026): 236
  faturas, 41.172 vidas; amostra de 2 faturas (48+4) gerou 52 linhas —
  fechamento exato. Regressão do Porto Dental confirmada (20/7.080).
  No mesmo dia: checkboxes do SUBGRUPOS DE VIDA passaram a exibir o
  código do subgrupo entre colchetes (ver §4); datas nas planilhas
  (Porto Assistência e Dental) passaram a exibir `DD/MM/YYYY` (helper
  `celula()` em `gerador_porto.py`); botões do Sempre Odonto em azul
  pastel `#7A9CC6` para diferenciar o tipo (cor parametrizada por
  `COR_BOTAO` na classe). Menu sem placeholders.
  Spec dos quatro ajustes: `docs/SPEC-AJUSTES-2026-08-28.md`.

- **27/08/2026 (b)** — Módulo GERA PORTO DENTAL implementado (fluxo de duas
  etapas: consulta com totalizador de vidas → geração liberada depois).
  Queries reais instaladas e testadas contra o banco na vigência
  01/07/2026: 20 faturas, 7.080 vidas; amostra de 2 faturas gerou 174
  linhas — exatamente a soma de qtd_itens das duas (136+38), confirmando
  o totalizador. Ajustes na query do usuário documentados nos próprios
  .sql (data fixa → :inivig; "= :FATURA" → "IN (:faturas)";
  correção do join "VS.seq_mat=VS.seq_mat" → "VS.seq_mat=VSM.seq_mat").
- **27/08/2026** — Camada de conexão alinhada ao FedHub-Backend: credenciais
  movidas do `config.py` para o `.env` (variáveis com os nomes do FedHub) e
  `db.py` ganhou pool de conexões por charset. `config_exemplo.py` deu lugar
  ao `.env.exemplo`. Interface `db.conectar()` inalterada — nenhum módulo
  precisou mudar. Decisão de rumo: migrar todos os módulos (inclusive os
  placeholders Dental) para o FedHub-Backend, com página simples servida
  pelo próprio backend.
- **26/08/2026** — Abas Código 2 e Código 3 do Porto Assistência igualadas
  ao layout de 12 colunas do Código 1 (a pedido do usuário).
- **21/08/2026** — Primeira versão do sistema unificado. SUBGRUPOS DE VIDA
  migrado de `02-gerador_planilhas_firebird`; PORTO ASSISTÊNCIA criado a
  partir do protótipo `Base_Cheque\Envio de Layout\sftp-porto` (onde a
  conexão SFTP e o layout da planilha foram validados com a Porto).
