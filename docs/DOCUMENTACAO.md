# SISTEMA DE ENVIO PORTO SEGURO

Documentação para desenvolvedores. Última atualização: 03/11/2026 (b).

## 1. O que é

Sistema desktop (Python + customtkinter) do Grupo Fedcorp que reúne, num
menu único, as rotinas de geração e envio de planilhas relacionadas à
Porto Seguro. Hoje tem cinco módulos:

| Módulo | Objetivo |
|---|---|
| **SUBGRUPOS DE VIDA** | Gerar o relatório Excel de segurados de Vida por subgrupo/vigência, com checagem de inconsistências (apólices sem subgrupo), cobertura provisória (VIDA RJ) e robô noturno. §4 |
| **PORTO ASSISTÊNCIA** | Gerar a relação mensal de segurados dos produtos Residencial (1), Auto (2) e Empresarial (3) e enviá-la por SFTP para a Porto Seguro. §5 |
| **GERA PORTO DENTAL** | Consultar e gerar a planilha mensal do Porto Dental em duas etapas. §7 |
| **GERAR DENTAL SEMPRE ODONTO** | Clone parametrizado do Porto Dental para o produto Sempre Odonto. §7b |
| **GERAR ARQUIVO FUNERAL** | Planilha de segurados de Vida com cobertura FUNERAL/CERIMONIAL na vigência (administradora, apólice, nome, CPF, nascimento), sem CPF repetido. §7c |

Manuais: `docs/MANUAL-OPERACAO.md` (usuário final) e
`docs/MANUAL-INSTALACAO.md` (replicar o ambiente em outra máquina).

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
copy .env.exemplo .env      # só na primeira vez; preencher FB_* e SFTP_*
python main.py
```

Testes: `python -m unittest discover -s tests` (unitários, sem banco).
O teste de integração com o Firebird real só roda com
`$env:PORTO_TESTE_INTEGRACAO = "1"` definido antes.

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
│  *.json                   ← preferências das telas (criados no 1º uso,
│                             ignorados pelo git): porto_assistencia,
│                             porto_dental, sempre_odonto, funeral
│
├─ modulos\
│    subgrupos_vida.py      ← SUBGRUPOS DE VIDA (tela + lógica + robô)
│    porto_assistencia.py   ← PORTO ASSISTÊNCIA (tela)
│    gerador_porto.py       ← núcleo de geração do xlsx da Assistência
│    envio_sftp.py          ← upload para o SFTP da Porto
│    porto_dental.py        ← GERA PORTO DENTAL (tela, duas etapas)
│    dental_sempre_odonto.py← GERAR DENTAL SEMPRE ODONTO (subclasse)
│    gerador_dental.py      ← núcleo de geração do Dental
│    funeral.py             ← GERAR ARQUIVO FUNERAL (tela)
│    gerador_funeral.py     ← núcleo de geração do Funeral
│
├─ queries\                 ← SQLs editáveis sem mexer em código
│    codigo1_residencial_1.sql / _2.sql, codigo2_auto.sql,
│    codigo3_empresarial.sql        (Porto Assistência, :inivig)
│    portodental_1.sql / _2.sql     (Porto Dental, :inivig / :faturas)
│    sempreodonto_1.sql / _2.sql    (Sempre Odonto)
│    funeral.sql                    (Funeral, :inivig)
│    alter_gera_rel_pla_sistema.sql / _99.sql  ← DDL já aplicada no
│                                     banco (registro; nunca executada
│                                     pelo sistema)
│
├─ tests\                   ← python -m unittest discover -s tests
│    test_agendador_subgrupos_vida.py, test_gerador_funeral.py (sem banco)
│    test_integracao_*.py   (só com PORTO_TESTE_INTEGRACAO=1)
│
└─ docs\
     DOCUMENTACAO.md        ← este arquivo (manual de estudo)
     MANUAL-OPERACAO.md     ← manual do usuário
     MANUAL-INSTALACAO.md   ← requisitos e instalação em outra máquina
     PLANO-WEB.md, SPEC-*.md, equipe\DIARIO.md (agentes)
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

### Checagem de inconsistências no escopo do subgrupo (03/11/2026)

Ao clicar em **Gerar Planilha Excel** (geração manual), antes de gerar o
sistema roda, para cada subgrupo marcado, a mesma query do relatório
"Ver Inconsistências (Tela)" restrita aos **códigos de apólice que fazem
parte do subgrupo** (`f.apolice IN (SELECT apolice FROM APOLICES WHERE
SUBPORTO = id)`): faturas de Vida ativas na vigência cuja apólice está com
SUBPORTO vazio. Se houver achados, abre uma grade modal (subgrupo,
apólice, seq, fatura, administradora — como no relatório) com os botões
**Continuar mesmo assim** e **Cancelar geração**; a decisão é do usuário.
Funções: `_inconsistencias_do_subgrupo` e `_confirmar_inconsistencias`.

Regras: (a) apólice compartilhada por vários subgrupos (ex.: 4803 está em
sete) aparece em todos — intencional, melhor alertar a mais; (b) o escopo
é por código de apólice, não por administradora, porque administradoras
têm apólices de outros produtos sem subgrupo (251660, 13008, BPS001) que
gerariam ruído; (c) **o robô não faz essa checagem** — ele chama
`_montar_dataframe` direto, senão ficaria parado esperando resposta.
Medição em 03/11/2026 (vigência 10/2026): PSPS 16 apólices PSPS01 sem
SUBPORTO, CIPA 0, VIDA SP 31, VIDA RJ 20.

### Segurados com COBERTURA PROVISÓRIA — só subgrupo 1317377 VIDA RJ (09/10/2026)

Reproduz o fluxo do Delphi que inclui na planilha os segurados que ainda
não têm fatura (cobertura provisória), usando a fatura temporária **99**.
Configuração nas constantes de classe `SUBGRUPOS_COB_PROV = {'1317377'}`
e `FATURA_COB_PROV = 99`; para estender a outro subgrupo basta incluir o
código no conjunto.

`_incluir_coberturas_provisorias` é chamado por `_montar_dataframe` logo
depois do loop de faturas, quando o subgrupo está no conjunto:

1. `UPDATE VIDA_COBERTURA_PROV SET FATURA=99 WHERE FATURA IS NULL AND
   APOLICE IN (apólices do subgrupo em APOLICES.SUBPORTO) AND
   DT_INI_COBERT = vigência`. Se não marcar nada, sai.
2. Marca com 99 os registros desses segurados em `VIDA_SEGURADOS_MOV`
   (`FATURA IS NULL`) e `VIDA_SEGURADO_FIN` (`FATURA = 0`), casando pelas
   chaves administradora/posto/seq_posto/matricula/seq_mat/apolice/seq.
   **Passo reconstruído**: a procedure 99 lê `VIDA_SEGURADO_FIN WHERE
   FATURA=99`, nenhum trigger do banco propaga o 99 (os que existem em
   MOV/FIN são AU0, AD0 e AI0, nenhum toca em FATURA) e a limpeza do
   Delphi desfaz justamente MOV 99→NULL e FIN 99→0. O trecho Delphi
   correspondente não foi fornecido; se existir, comparar (GAP-01).
   O UPDATE de MOV exclui `STATUS = 'C'`: a trigger
   `VIDA_SEGURADOS_MOV_AU0` apaga os movimentos/financeiros irmãos quando
   um movimento cancelado é atualizado (revisão DBA de 03/11/2026).
3. `EXECUTE PROCEDURE GERA_REL_PLA_SISTEMA99(99)` + `INSERT INTO
   TEMP_RELATORIO_VIDA2 SELECT * FROM TEMP_RELATORIO_VIDA`. As linhas
   saem com `FATURA = 99`. Só entram segurados que têm registro em
   `VIDA_SEGURADO_FIN`; cobertura provisória sem financeiro não aparece.
   3b. **Complemento que não existe no Delphi**: a procedure 99 junta
   `VIDA_SEGURADOS_MOV` com `VSM.TIPO_FAT = VSM.TIPO_FAT`, e TIPO_FAT é
   NULL em todo provisório do banco, então o join falha e as linhas 99
   sairiam com DT_INI_VIG/DT_FIM_VIG/SUBPORTO vazios (como saem no
   Delphi). Um `UPDATE TEMP_RELATORIO_VIDA2` preenche as datas a partir
   do movimento marcado 99 (MIN(INICIO_VIG)/MAX(FINAL_VIG)) e o SUBPORTO
   com o código do subgrupo, ainda dentro do `try`, antes da limpeza.
4. Limpeza: PROV 99→NULL, MOV 99→NULL, FIN 99→0 — as três instruções
   do Delphi — e **um único commit**. Desde 03/11/2026 todo o fluxo
   (marcas, procedure, acúmulo, 3b e limpeza) é uma só transação: em
   erro faz `rollback` e relança, então nenhum 99 chega a ser commitado.

Na planilha, `_salvar_excel` (usado pelo botão manual e pelo robô) pinta
de **amarelo e negrito** as células da coluna FATURA com valor 99 e põe um
comentário no cabeçalho explicando a legenda. O valor continua numérico.

Teste de 09/10/2026 (VIDA RJ, vigência 01/09/2026): 9 coberturas
provisórias da apólice 4803 → 8 movimentos e 33 linhas financeiras
marcadas → 5 segurados na planilha com fatura 99 (os outros não têm
financeiro), vigência 01/09–30/09/2026 e subporto 1317377 preenchidos,
snapshot das linhas PROV/MOV/FIN idêntico antes e depois, nenhum 99
residual, 5 células amarelas no Excel. Como as tabelas são de produção e a operação
roda em horário comercial, os totais globais podem variar por ação de
outros usuários; a invariante a checar é o estado das linhas marcadas.

**Defeito na procedure (03/11/2026)**: `GERA_REL_PLA_SISTEMA99` declara
`COBERTURA varchar(30)` (a procedure normal usa 50) e 27 coberturas têm
nome maior que 30 — ex.: "AUX DIAGNOSTICO CANCER MAMA E PROSTATA". Um
provisório com uma dessas coberturas derruba a procedure com SQLCODE -802
"string right truncation" (acontecia em VIDA RJ, vigência 01/10/2026). O
Delphi sofria do mesmo problema. **Corrigido no banco pelo usuário em
03/11/2026**: COBERTURA e BAIRRO passaram a varchar(50) (BAIRRO dava o
mesmo erro). `queries/alter_gera_rel_pla_sistema99.sql` guarda a versão
aplicada, para reaplicar em outro banco; o sistema não a executa.
Verificado após a correção: VIDA RJ 01/10/2026 com 15 provisórios (8 da
4803, 7 da 6800), vigência 01/10–31/10 preenchida, sem resíduo de 99.
Mesmo assim `_montar_dataframe` continua capturando falhas desse passo:
a transação é desfeita, a planilha sai **sem** os provisórios e
`self.ultimo_aviso` é mostrado em messagebox (manual) ou gravado como
`[AVISO ]` no `robo_log.txt` (robô). Teste permanente:
`tests/test_integracao_cobertura_provisoria.py` (descobre a vigência com
provisórios pendentes e confere quantidade, datas, subporto e resíduos).

**Defeito na procedure NORMAL (03/11/2026, à tarde)**: ao gerar VIDA RJ e
VIDA SP manualmente, `GERA_REL_PLA_SISTEMA` falhou com SQLCODE -802 na
linha 180 (FETCH). Causa medida no banco: o cursor lê `VP.BAIRRO_POSTO`
de `VIDA_POSTOS`, que é varchar(50), para a variável `BAIRRO varchar(30)`;
104 postos têm bairro acima de 30. Os demais campos do posto (cidade,
endereço, CEP, UF, nome) cabem nas variáveis. Correção em
`queries/alter_gera_rel_pla_sistema.sql`: BAIRRO → varchar(50) na
procedure **e** nas colunas BAIRRO de TEMP_RELATORIO_VIDA/VIDA2 (hoje 40,
senão o INSERT truncaria em seguida). Aplicar como SYSDBA e commitar; o
sistema não executa DDL. A procedure 99 não tem esse problema porque lê o
bairro de VIDA_SEGURADOS (30).

Lacunas registradas (03/11/2026): GAP-01 passo 2 reconstruído sem o
fonte Delphi; GAP-02 complemento 3b não existe no Delphi (alternativa:
corrigir `GERA_REL_PLA_SISTEMA99` no banco); GAP-03 só 1317377 por
constante, sem fonte da decisão; GAP-04 não há trava de concorrência nas
TEMP_* e nas marcas 99 (restrição operacional: ninguém usa Vida enquanto
o robô roda).

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

Fechar a janela Vida com robô agendado pede confirmação e cancela o
agendamento; com robô rodando a janela não fecha (`_ao_fechar`,
03/11/2026). `processar` devolve a conexão ao pool em `finally` e faz
rollback em erro.

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

## 7c. Módulo GERAR ARQUIVO FUNERAL (`modulos/funeral.py` + `modulos/gerador_funeral.py`)

Pedido do usuário em 03/11/2026. Lista os segurados de Vida que têm, nas
faturas ativas da vigência, alguma cobertura cujo nome em `COBERTURAS`
contém **FUNERAL** ou **CERIMONIAL** (9 coberturas hoje: 0009, 0015, 0084,
0129, 0189, 0209, 0216, 0219, 0244 — a lista é dinâmica, pelo nome).

- Tela de uma etapa (pasta + data de início de vigência + botão verde
  "Gerar Arquivo Funeral"), log por queue como no Dental; pasta salva em
  `funeral.json`.
- Query `queries/funeral.sql` (:inivig): FATURAS (ramo V, status A, com o
  critério de vigência abaixo) → VIDA_SEGURADO_FIN (cobertura) →
  VIDA_SEGURADOS_MOV (movimento na fatura, `STATUS <> 'C'`) →
  VIDA_SEGURADOS (nome, CPF, nascimento) → PESSOAS (administradora).
- `gerador_funeral.remover_duplicidade_cpf` mantém a primeira ocorrência
  de cada CPF (só dígitos); CPF vazio não é deduplicado.
- Planilha `funeral-MMYYYY.xlsx`, aba FUNERAL, colunas ADMINISTRADORA,
  APOLICE, NOME, CPF, NASCIMENTO (data formatada DD/MM/YYYY).
- Medição em 03/11/2026 (vigência 01/10/2026): 22.347 linhas no banco,
  20.236 CPFs distintos, 17 apólices, 215 administradoras; nenhum
  movimento cancelado nessas faturas. Leva ~15 s.
- Testes: `tests/test_gerador_funeral.py` (dedupe, CPF, planilha, sem
  banco) e `tests/test_integracao_funeral.py` (só leitura, gated).

### Critério de vigência comum a todos os geradores (03/11/2026)

Decisão do usuário: apólices não mensais (`APOLICES.NOME_VIGENCIA` =
ANUAL, 60 MESES, N MESES, REALIZADO) têm segurados ativos durante toda a
vigência, então um segurado com vigência 01/01/2026–31/12/2026 deve
entrar na listagem de qualquer mês. Regra: entra a fatura (ou segurado)
cuja vigência em curso **contém** a data informada, além das que começam
exatamente nela. Onde está aplicado:

| Gerador | Antes | Agora |
|---|---|---|
| SUBGRUPOS DE VIDA (`query_faturas`) | já era `:d BETWEEN dt_ini_vig AND dt_fim_vig OR dt_ini_vig = :d` | sem mudança (63 faturas não mensais entram em 10/2026) |
| FUNERAL | — | mesmo critério |
| PORTO DENTAL / SEMPRE ODONTO (query 1) | `F.dt_ini_vig = :inivig` | `OR :inivig BETWEEN F.dt_ini_vig AND F.dt_fim_vig` |
| PORTO ASSISTÊNCIA residencial/empresarial (`SEGURADOS_INC`) | `ss.inicio_vig >= :inivig` | `OR :inivig BETWEEN ss.inicio_vig AND ss.final_vig` |
| PORTO ASSISTÊNCIA auto/BOAT (`VIDA_SEGURADOS_MOV`) | `M.inicio_vig = :inivig` | `OR :inivig BETWEEN M.inicio_vig AND M.final_vig` |

Todas as mudanças são **superconjunto** do critério anterior (nunca
retiram alguém que entrava antes). Em 10/2026 não mudaram o resultado de
Dental (106/205 faturas) nem de BOAT (42.105 segurados). Na Assistência
residencial/empresarial o efeito é grande e **deve ser validado pelo
usuário antes do próximo envio à Porto**: residencial parte 1 passou de
21.935 para 28.797 linhas, empresarial de 6.826 para 8.966 (residencial
parte 2 ficou em 24.968) — são os segurados anuais de `SEGURADOS_INC`
cuja vigência contém 01/10/2026. Se a Porto já os tem, a seguradora pode
apontar duplicidade; nesse caso basta voltar o `OR` das três queries.

## 7d. Versão web (branch `web-render`, 03/11/2026)

Pasta local `U:\--2021-EnvioPorto-web` (git worktree da branch
`web-render`). A `main` continua sendo o desktop em uso. Estrutura:

- `web/app.py` — FastAPI: login, menu, `/vida`, `/funeral`, `/dental`,
  `/sempreodonto`, `/assistencia`, `/trabalhos/{id}` (acompanhamento +
  download). Sem tkinter.
- `web/auth.py` — usuários fixos de `WEB_USUARIOS` + `WEB_SENHA`
  (`WEB_SENHA_n` opcional por usuário); cookie assinado (`itsdangerous`),
  8 h; 10 falhas por e-mail+IP em 15 min bloqueiam.
- `web/trabalhos.py` — fila em memória; cada geração roda em thread e a
  página consulta `/trabalhos/{id}/estado` a cada 2 s.
- `web/templates/*.html`, `web/static/style.css` — telas (Jinja2).
- `modulos/gerador_vida.py` — núcleo de SUBGRUPOS DE VIDA sem interface
  (listar subgrupos, inconsistências, montar_dataframe, cobertura
  provisória, salvar_excel). A classe desktop `JanelaSubgruposVida` delega
  para ele; os SQLs são idênticos aos originais (verificado por script).
- `Dockerfile`, `.dockerignore`, `render.yaml` — deploy no Render
  (Docker, porque o runtime Python do Render não tem libfbclient2).
  Guia completo, inclusive a questão do ngrok: `docs/DEPLOY-RENDER.md`.
- Testes: `tests/test_web.py` (login, proteção das rotas, fila, download;
  sem banco). No build do Docker rodam só os testes sem tkinter.

Diferenças para o desktop: arquivos efêmeros (baixar na hora), sem robô
noturno, envio SFTP só com dupla confirmação.

Smoke test de 03/11/2026 contra o banco real pelo `TestClient`: login,
20 subgrupos listados, grade de inconsistências do PSPS, CIPA gerado e
baixado, Funeral (20.236 segurados), consultas Dental/Sempre Odonto e
Assistência Auto com limite — tudo OK.

## 8. Como adicionar um novo módulo

1. Criar `modulos/nome_do_modulo.py` com uma classe `ctk.CTkToplevel`
   (usar `porto_assistencia.py` como referência de estrutura).
2. Usar `db.conectar()` para acessar o banco — nunca `fdb.connect` direto.
3. Registrar um botão no `main.py` chamando a nova janela.
4. Documentar o módulo neste arquivo (objetivo, fluxo, tabelas usadas).

## 9. Histórico

- **03/11/2026 (e)** — Branch `web-render`: versão web FastAPI com login
  fixo, Docker + render.yaml para o Render, núcleo `gerador_vida.py` (§7d,
  `docs/DEPLOY-RENDER.md`).

- **03/11/2026 (d)** — Novo módulo GERAR ARQUIVO FUNERAL (§7c) e critério
  de vigência "vigência em curso contém a data" aplicado às queries do
  Dental e da Assistência (§7c). Manuais novos: `docs/MANUAL-OPERACAO.md`
  (usuário final) e `docs/MANUAL-INSTALACAO.md` (replicar o ambiente).

- **03/11/2026 (c)** — Erro -802 na procedure normal `GERA_REL_PLA_SISTEMA`
  (BAIRRO do posto > 30). Script `queries/alter_gera_rel_pla_sistema.sql`
  (procedure + colunas BAIRRO das TEMP para 50), aplicado pelo usuário no
  mesmo dia. Varredura dos 20 subgrupos na vigência 01/10/2026 após a
  correção: 20 OK, 0 erros, 0 avisos, 78.589 linhas, 15 provisórios em
  VIDA RJ, nenhum resíduo de 99; 4 subgrupos sem faturas em outubro
  (AP DE INCENDIO, CONSTRUCAO CIVIL - MG, CRASE SIGMA, TERCERIZADAS RUMAM).

- **03/11/2026 (b)** — SUBGRUPOS DE VIDA: checagem de inconsistências no
  escopo do subgrupo antes da geração manual, com confirmação do usuário
  (§4). Descoberto defeito da procedure 99 (`COBERTURA varchar(30)`) que
  derruba a cobertura provisória de VIDA RJ em 10/2026; geração passou a
  ser resiliente (sai sem provisórios + aviso) e o script de correção da
  procedure está em `queries/alter_gera_rel_pla_sistema99.sql`. Procedure
  corrigida no banco pelo usuário no mesmo dia (COBERTURA e BAIRRO →
  varchar(50)); teste de integração da cobertura provisória adicionado.

- **03/11/2026** — Revisão com os agentes especialistas (dev-backend, dba,
  analista-requisitos, analista-infra). Corrigido token solto `uhuh` em
  `porto_assistencia.py` que impedia o sistema de abrir; cobertura
  provisória em transação única com rollback em erro e filtro
  `STATUS <> 'C'` no MOV (trigger AU0); `processar` fecha a conexão em
  `finally`; handler de fechamento da janela Vida com robô agendado;
  destaque amarelo usa `pd.to_numeric`; pin do python-dotenv relaxado.
  Pendências: GAP-01..04 (§4), host key do SFTP não verificada
  (`envio_sftp.py`), preferência "enviar" persistida no JSON do Porto
  Assistência (decisão de produto), `docs/PLANO-WEB.md` desatualizado
  quanto ao Dental. Diário dos agentes em `docs/equipe/DIARIO.md`.

- **09/10/2026** — SUBGRUPOS DE VIDA: segurados com cobertura provisória
  (fatura 99) no subgrupo 1317377, com destaque amarelo na coluna FATURA
  (§4). Testado contra o banco: 5 segurados, estado das tabelas restaurado.

- **07/10/2026** — SUBGRUPOS DE VIDA: robô de agendamento noturno de todos
  os subgrupos (§4) e correção do parêntese na query de inconsistências.

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
