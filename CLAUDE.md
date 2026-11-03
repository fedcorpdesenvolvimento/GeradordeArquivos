# SISTEMA DE ENVIO PORTO SEGURO

Sistema desktop Python/customtkinter do Grupo Fedcorp que reúne as rotinas
de geração e envio de planilhas para a Porto Seguro. O usuário (Alberto) é
o dono do produto; idioma de trabalho: **português**.

**Leia `docs/DOCUMENTACAO.md` antes de mexer no código** — tem o objetivo,
o fluxo e as pegadinhas de cada módulo. Mantenha essa documentação
atualizada a cada mudança: ela é o material dos futuros programadores.

## Regras e decisões já alinhadas (não reabrir sem o usuário pedir)

- **Estilo**: customtkinter, fontes Arial, botão de ação principal em verde,
  cada módulo é uma `CTkToplevel` aberta pelo menu (`main.py`). Comentários
  e identificadores em português. Exceção de cor: produtos não-Porto usam
  azul pastel `#7A9CC6` (hoje só o SEMPRE ODONTO) para diferenciar o tipo.
- **Conexão**: sempre via `db.conectar()` (nunca `fdb.connect` direto).
  Desde 27/08/2026 segue o modelo do **FedHub-Backend** (repo privado
  `Fedcorp-Desenvolvimentos/FedHub-Backend`): credenciais no `.env`
  (variáveis `FB_*`, mesmos nomes do FedHub; nunca commitar) e pool de
  conexões em `db.py` (um pool por charset). Os módulos não devem depender
  de detalhes da conexão. Firebird 2.5 em 192.168.0.6, `FATURA.GDB`.
  Charset: Vida usa ASCII (comportamento herdado validado), Porto
  Assistência usa WIN1252.
- **Rumo web**: decisão de 27/08/2026 — todos os módulos (inclusive os
  placeholders Dental) migrarão para o FedHub-Backend como módulo FastAPI,
  com página simples servida pelo próprio backend. Este desktop continua
  em uso até a versão web ser validada.
- **SUBGRUPOS DE VIDA**: lógica migrada intacta de
  `U:\--2021\02-gerador_planilhas_firebird\main.py` — não "melhorar" queries
  nem fluxo sem o usuário pedir.
- **PORTO ASSISTÊNCIA**: nomes das abas do Excel reproduzem o modelo manual
  byte a byte (`"Código 2 - Auto "` com espaço final, `"Código 3 -  Empresarial"`
  com espaço duplo) — NUNCA corrigir. Queries em `queries/*.sql` com parâmetro
  `:inivig`; mapeamento query→aba documentado na DOCUMENTACAO.md §5.
- **Datas**: calendários abrem pré-configurados com o **dia 01 do mês
  anterior** (padrão de vigência), sempre editáveis.
- **SFTP Porto**: o DNS da rede local NÃO resolve `sftp.portoseguro.com.br`;
  o código usa fallback pelo IP (config.py). Upload sempre com `.part` +
  verificação de tamanho + rename. Nunca enviar arquivo de teste para
  `/Porto/Remessa` sem o usuário confirmar — tudo que cai lá pode ser
  processado pela seguradora.
- **GERA PORTO DENTAL**: implementado em 27/08/2026 — fluxo de DUAS etapas
  obrigatórias: consultar (query 1, :inivig → log + total de vidas) libera
  o botão de gerar (query 2 alimentada pelas faturas da query 1 via
  marcador :faturas). Planilha `portodental-MMYYYY.xlsx` no formato exato
  da query 2. Queries reais em `queries/portodental_*.sql` (instaladas e
  testadas em 27/08/2026). Ver DOCUMENTACAO.md §7.
- **GERAR DENTAL SEMPRE ODONTO**: implementado em 28/08/2026 como clone
  parametrizado do Porto Dental (subclasse trocando atributos de classe):
  `tipo_dental = 'S'` na query 1, nome SEMPRE ODONTO no título/aba/arquivo
  (`sempreodonto-MMYYYY.xlsx`). Não há mais módulos placeholder no menu.

- **ROBÔ DE VIDA** (07/10/2026): botão roxo em SUBGRUPOS DE VIDA agenda a
  geração de todos os subgrupos via `after()` + thread + `queue`; a thread
  nunca toca em widgets nem chama `self.after()`. Exige o programa aberto.
  TEMP_RELATORIO_VIDA* são compartilhadas: ninguém usa Vida enquanto roda.
- **COBERTURA PROVISÓRIA** (09/10/2026): só no subgrupo 1317377 (constante
  `SUBGRUPOS_COB_PROV`), fatura temporária 99 em VIDA_COBERTURA_PROV /
  VIDA_SEGURADOS_MOV / VIDA_SEGURADO_FIN, procedure GERA_REL_PLA_SISTEMA99,
  tudo numa transação única com limpeza igual ao Delphi; **nunca pode
  sobrar 99 no banco**. MOV com STATUS 'C' não é marcado (trigger AU0).
  Linhas 99 saem em amarelo na coluna FATURA. Lacunas em DOCUMENTACAO §4.
  Falha na procedure 99 não derruba o subgrupo (sai sem provisórios +
  aviso). Procedure corrigida no banco em 03/11/2026 (COBERTURA e BAIRRO
  varchar 30→50); `queries/alter_gera_rel_pla_sistema99.sql` guarda a
  versão aplicada e nunca é executado pelo sistema.
- **CHECAGEM DE INCONSISTÊNCIAS** (03/11/2026): antes da geração manual de
  Vida, apólices do subgrupo sem SUBPORTO na vigência são listadas e o
  usuário decide continuar ou não. O robô agendado NÃO faz a checagem.
- **GERAR ARQUIVO FUNERAL** (03/11/2026): coberturas identificadas pelo
  NOME em COBERTURAS contendo FUNERAL ou CERIMONIAL (lista dinâmica);
  faturas ramo V ativas na vigência; sem CPF repetido; colunas
  administradora, apólice, nome, CPF, nascimento. Query `queries/funeral.sql`.
- **CRITÉRIO DE VIGÊNCIA** (03/11/2026, todos os geradores): entra o que
  tem vigência em curso contendo a data informada, além do que começa
  nela (apólices anuais / N MESES). Sempre superconjunto do critério
  antigo; ver DOCUMENTACAO §7c antes de mexer em qualquer query.
- **Manuais**: `docs/MANUAL-OPERACAO.md` (usuário) e
  `docs/MANUAL-INSTALACAO.md` (replicar ambiente) — manter junto com a
  DOCUMENTACAO.md a cada mudança.
- **Agentes especialistas**: registram cada análise em
  `docs/equipe/DIARIO.md`; o dba é somente leitura por padrão.

## Como rodar / testar

```
python main.py
```

Testes unitários: `python -m unittest discover -s tests` (sem banco).
Integração com o Firebird real: definir `PORTO_TESTE_INTEGRACAO=1` antes.

Testes de geração sem dados reais: apontar as queries para `RDB$RELATIONS`
com CAST + aliases (ver histórico) ou usar limite pequeno (5 linhas) com as
queries reais — leitura é inofensiva; o que não pode é enviar ao SFTP.
