# Spec — GERA PORTO DENTAL (módulo desktop)

> **Rastreabilidade** — RF: RF-DEN-001..005 · RNF: RNF-DEN-001..003
> **Status:** aprovado (implementado e validado) · **Dono:** Alberto (dono do produto) · **Atualizado:** 2026-08-27

Spec no padrão SDD do Grupo FedCorp (adaptação local — o EnvioPorto não tem
a infra completa de `specs/` do FedHub-Backend; convenções em
`FedHub-Backend/specs/CONVENCOES.md`). Marcas: `[E]` evidência com
arquivo:linha ou verificação datada; `[D]` decisão do dono com data.
Contexto local `DEN`; na migração web (spec `envio-porto` no FedHub,
contexto `EPO`) este fluxo substituirá o placeholder do RF-EPO-006.

## Contexto e Problema

O menu do EnvioPorto tinha o botão GERA PORTO DENTAL como placeholder
"em desenvolvimento". Em 27/08/2026 o dono definiu o fluxo e forneceu as
duas queries; o módulo foi implementado no mesmo padrão dos demais
(CTkToplevel, fontes Arial, botão de ação verde, log por queue drenada
pelo loop Tk) [E] (`modulos/porto_dental.py`, verificado 2026-08-27).

## Escopo

**Dentro:** tela `modulos/porto_dental.py`, núcleo `modulos/gerador_dental.py`,
queries `queries/portodental_1.sql` e `portodental_2.sql`, botão no
`main.py`. **Fora:** envio da planilha (não há SFTP no fluxo Dental);
versão web (spec `envio-porto` do FedHub-Backend).

**Extensão (28/08/2026):** GERAR DENTAL SEMPRE ODONTO implementado como
clone parametrizado desta spec — `JanelaDentalSempreOdonto` herda
`JanelaPortoDental` trocando só atributos de classe (queries
`sempreodonto_*.sql` com `tipo_dental = 'S'`, arquivo
`sempreodonto-MMYYYY.xlsx`, aba `SEMPRE ODONTO`) [E]
(`modulos/dental_sempre_odonto.py`, verificado 2026-08-28; consulta na
vigência 01/07/2026: 236 faturas/41.172 vidas; amostra de 2 faturas
gerou 52 linhas = 48+4, fechamento exato). Todos os RF/RNF desta spec
valem para os dois produtos, com os parâmetros de cada um.

## User Stories e Critérios de Aceitação

### RF-DEN-001: Definir vigência e pasta de destino

**Como** operador, **quero** definir a vigência e a pasta de salvamento,
**para** parametrizar consulta e geração como nos demais módulos.

- **QUANDO** a tela abre, **ENTÃO** o calendário **DEVE** vir pré-preenchido
  com o dia 01 do mês anterior, editável [E] (`modulos/porto_dental.py:72`,
  reutiliza `primeiro_dia_mes_anterior` do Porto Assistência).
- **QUANDO** a tela abre, **ENTÃO** a pasta **DEVE** vir preenchida com a
  última escolha, persistida em `porto_dental.json` [E]
  (`modulos/porto_dental.py:99-117`).
- **SE** pasta vazia ou data inválida, **ENTÃO** o sistema **DEVE** avisar
  e não executar [E] (`modulos/porto_dental.py:153-166`).

### RF-DEN-002: Consultar vidas (etapa 1, obrigatória)

**Como** operador, **quero** consultar as faturas da vigência e ver o total
de vidas, **para** conferir o volume antes de gerar a planilha.

- **QUANDO** o operador clica em "1) Consultar Vidas", **ENTÃO** o sistema
  **DEVE** executar `queries/portodental_1.sql` com `:inivig` e mostrar no
  log cada linha retornada (fatura, apólice, nome da administradora,
  vidas, descrição do produto e do produto master — versão ampliada da
  query 1, dono, 27/08/2026) [E] (`modulos/gerador_dental.py:34-69`).
- **QUANDO** a consulta conclui, **ENTÃO** o log **DEVE** mostrar o número
  de faturas e o **TOTAL DE VIDAS A ENVIAR** — soma da coluna `VIDAS`
  (alias de `F.qtd_itens`); sem essa coluna, contagem de linhas [E]
  (`modulos/gerador_dental.py:53-64`).
- **SE** a query 1 não retornar a coluna `FATURA`, **ENTÃO** o sistema
  **DEVE** falhar com mensagem citando as colunas retornadas [E]
  (`modulos/gerador_dental.py:48-51`).

### RF-DEN-003: Gerar planilha final (etapa 2, liberada pela etapa 1)

**Como** operador, **quero** gerar a planilha final só depois de conferir a
consulta, **para** nunca gerar sem ver o volume [D] (fluxo em duas etapas
com ordem obrigatória — decisão do dono, 27/08/2026).

- **ENQUANTO** não houver consulta bem-sucedida com faturas, o botão
  "2) Gerar Planilha Final" **DEVE** permanecer desabilitado [E]
  (`modulos/porto_dental.py:82-89,119-133`).
- **QUANDO** o operador gera, **ENTÃO** a `queries/portodental_2.sql`
  **DEVE** ser alimentada pelos números de fatura da consulta: o marcador
  `:faturas` dentro do `IN` é substituído em blocos de 1.000 (folga sobre o
  limite de 1.500 do `IN` no Firebird 2.5) [E]
  (`modulos/gerador_dental.py:72-120`).
- **QUANDO** a planilha é gravada, **ENTÃO** o cabeçalho **DEVE** ser
  exatamente as colunas da query 2, na ordem da query (o formato da
  planilha É o formato da query 2) [D] (dono, 27/08/2026) [E]
  (`modulos/gerador_dental.py:94-106`).
- **QUANDO** a planilha é gravada, **ENTÃO** o nome **DEVE** ser
  `portodental-MMYYYY.xlsx` com a competência da vigência, na pasta
  escolhida [E] (`modulos/gerador_dental.py:83-84`).
- A geração usa a vigência e as faturas **da consulta realizada** — mudar o
  calendário depois da etapa 1 não altera a etapa 2; nova consulta
  desabilita o botão de gerar até concluir [E]
  (`modulos/porto_dental.py:168-181,203-223`).

### RF-DEN-004: Queries do fluxo (fonte: dono, 27/08/2026)

As queries fornecidas pelo dono foram instaladas com quatro ajustes,
documentados no cabeçalho de cada `.sql` [E] (verificado 2026-08-27):

| # | Ajuste | Motivo |
|---|---|---|
| 1 | `F.dt_ini_vig = '07/01/2026'` → `= :inivig` | data vem do calendário |
| 2 | `F.qtd_itens` → alias `VIDAS` | totalizador soma vidas, não conta faturas |
| 3 | `VSM.fatura = :FATURA` → `IN (:faturas)` | busca em blocos, mesmo resultado |
| 4 | `VS.seq_mat=VS.seq_mat` → `VS.seq_mat=VSM.seq_mat` | **bug**: comparava a coluna com ela mesma; corrigido no padrão do join do `codigo2_auto.sql` |

### RF-DEN-005: Botão no menu

- **QUANDO** o menu abre, **ENTÃO** GERA PORTO DENTAL **DEVE** aparecer
  como módulo ativo (verde) abrindo a janela do módulo [E]
  (`main.py:41-44,69-71`); GERAR DENTAL SEMPRE ODONTO segue placeholder.

## Requisitos Não Funcionais

### RNF-DEN-001: Consistência consulta × planilha

O total de vidas da etapa 1 corresponde às linhas da planilha da etapa 2
(mesmas faturas, `status <> 'C'`). Verificado em 2026-08-27 contra o banco
de produção (leitura): vigência 01/07/2026 → 20 faturas, 7.080 vidas;
amostra de 2 faturas (136 + 38 vidas) gerou exatamente 174 linhas.

### RNF-DEN-002: Responsividade da tela

Consulta e geração rodam em thread; o log chega por `queue.Queue` drenada
a cada 100 ms; linhas de progresso são transientes (mesmo padrão do Porto
Assistência) [E] (`modulos/porto_dental.py:121-151`).

### RNF-DEN-003: Conexão e charset

Acesso ao banco somente via `db.conectar(charset="WIN1252")` (pool por
charset, modelo FedHub) — nunca `fdb.connect` direto [E]
(`modulos/gerador_dental.py:43,97`). Excel em `openpyxl` `write_only`,
leitura em blocos de 2.000 linhas.

## Divergência vs. produção

Nenhuma divergência conhecida — o módulo entrou em 27/08/2026 já conforme
esta spec; a spec foi escrita a partir do comportamento implementado e
validado.

## Pendências

- Validação com a base toda pelo dono (o teste usou amostra de 2 faturas).
  Atenção especial ao efeito da correção do `seq_mat` (RF-DEN-004 #4) no
  conteúdo — o fechamento exato com `qtd_itens` na amostra é forte
  indício de que a correção está certa.
- Na migração web, portar este fluxo para o módulo `envio_porto` do
  FedHub-Backend substituindo o placeholder 501 (RF-EPO-006 da spec
  `envio-porto`, branch `envio-porto`).
