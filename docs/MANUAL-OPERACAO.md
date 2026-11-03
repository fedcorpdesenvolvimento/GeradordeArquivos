# MANUAL DE OPERAÇÃO — SISTEMA DE ENVIO PORTO SEGURO

Público: usuários operacionais (não programadores). Versão de 03/11/2026.
Para instalar o sistema em outra máquina, veja `docs/MANUAL-INSTALACAO.md`.
Para detalhes técnicos (queries, tabelas, procedures), veja `docs/DOCUMENTACAO.md`.

---

## 1. Visão geral

O sistema é um programa de mesa (janela) que reúne as rotinas de geração de
planilhas Excel para a Porto Seguro e para o Sempre Odonto, lendo os dados do
banco de faturamento (`FATURA.GDB`, o mesmo dos sistemas Delphi).

Para abrir: dê dois cliques no atalho do sistema ou, na pasta do programa,
rode `python main.py`. Aparece a janela **SISTEMA DE ENVIO PORTO SEGURO** com
o texto "Selecione o módulo:" e cinco botões:

| Botão do menu | O que gera | Nome do arquivo |
|---|---|---|
| **SUBGRUPOS DE VIDA** | Relatório de segurados de Vida por subgrupo (Porto) | `Subgrupo_<código>_Relatorio_<dd-mm-aaaa>.xlsx` |
| **PORTO ASSISTÊNCIA** | Relação mensal Residencial / Auto / Empresarial (com envio opcional por SFTP) | `relacao-envio-porto-<MMAAAA>.xlsx` |
| **GERA PORTO DENTAL** | Segurados das faturas de Porto Dental | `portodental-<MMAAAA>.xlsx` |
| **GERAR DENTAL SEMPRE ODONTO** (botão azul) | Segurados das faturas de Sempre Odonto | `sempreodonto-<MMAAAA>.xlsx` |
| **GERAR ARQUIVO FUNERAL** | Segurados de Vida com cobertura Funeral/Cerimonial | `funeral-<MMAAAA>.xlsx` |

Cada botão abre uma janela própria. Pode-se abrir mais de uma, mas evite rodar
duas gerações ao mesmo tempo (ver §7 sobre o módulo Vida).

### 1.1 Regras que valem para todos os módulos

- **Data de vigência**: todos os calendários abrem já preenchidos com o
  **dia 01 do mês anterior** ao de hoje (ex.: em novembro abre 01/10). É o
  padrão de vigência mensal, mas a data pode ser alterada livremente: clique
  no campo e digite, ou use a setinha para abrir o calendário.
- **Quem entra na planilha (regra de 03/11/2026)**: entram as faturas e
  segurados cuja **vigência em curso contém a data informada**, e não só os
  que começam exatamente nela. Assim, apólices anuais ou de vários meses (ex.:
  vigência 01/01/2026 a 31/12/2026) aparecem na listagem de qualquer mês do
  período. Essa regra vale para Vida, Porto Assistência, Porto Dental, Sempre
  Odonto e Funeral.
- **Pasta de destino**: nos módulos com campo "Pasta onde salvar a planilha",
  a pasta é lembrada entre uma abertura e outra. Se não existir, o sistema a
  cria. Na primeira vez vem sugerida a pasta `saida` dentro da pasta do
  programa.
- **Log**: nos módulos com área "Log:", acompanhe o andamento ali. Linhas que
  começam com `[ERRO]` indicam falha — leia §8.
- **Arquivo já existente**: se já houver um arquivo com o mesmo nome na pasta
  (mesma competência), ele é **sobrescrito sem aviso**. Feche o Excel antes de
  gerar de novo, senão a gravação falha com erro de "Permission denied".

---

## 2. SUBGRUPOS DE VIDA

Janela: **Gerador de Relatórios - Vida**.

### 2.1 O que faz

Gera a planilha de segurados de Vida de um ou mais **subgrupos** (os
subgrupos cadastrados na Porto, ex.: VIDA RJ, VIDA SP, CIPA, PSPS). Para cada
fatura ativa na vigência o banco monta o relatório (procedure
`GERA_REL_PLA_SISTEMA`) e o sistema junta tudo em um Excel.

### 2.2 Campos e botões da tela

- **Data de Vigência:** calendário (abre no dia 01 do mês anterior).
- **Selecione os Subgrupos:** lista de caixas de marcação, uma por subgrupo,
  no formato `NOME DO SUBGRUPO [código]` (ex.: `VIDA RJ [1317377]`). O código
  entre colchetes é só informativo.
- **Gerar Planilha Excel** (verde): geração manual.
- **Ver Inconsistências (Tela)** (azul): relatório de apólices sem subgrupo.
- **Agendar Robô (todos os subgrupos)** (roxo): robô noturno.
- Abaixo dos botões, uma linha cinza mostra o estado do robô (agendado /
  em execução / concluído).

### 2.3 Gerar Planilha Excel — passo a passo

1. Confira a **Data de Vigência**.
2. Marque um ou mais subgrupos.
3. Clique em **Gerar Planilha Excel**.
4. **Grade de inconsistências (pode ou não aparecer).** Antes de gerar, o
   sistema verifica, só para os subgrupos marcados, se há faturas de Vida
   ativas na vigência cuja apólice está **sem SUBPORTO** (sem subgrupo
   cadastrado). Se houver, abre a janela **Inconsistências no escopo do(s)
   subgrupo(s)**, com o texto em vermelho
   "N apólice(s) do escopo com SUBPORTO vazio na vigência dd/mm/aaaa." e a
   frase "Essas empresas NÃO entrarão na planilha. Corrija o cadastro ou
   continue mesmo assim.", seguidas de uma grade com as colunas
   SUBGRUPO, APOLICE, SEQ, FATURA e ADMINISTRADORA.
   - **Continuar mesmo assim** (verde): gera a planilha sem essas empresas.
   - **Cancelar geração** (vermelho) ou fechar a janela: aparece
     "Geração cancelada. Corrija o SUBPORTO das apólices e gere novamente."
     Corrija o cadastro da apólice no sistema de origem (campo SUBPORTO) e
     clique em Gerar de novo.
   - Uma apólice usada por vários subgrupos aparece em todos eles — é
     proposital (melhor avisar a mais).
5. A geração roda (a janela pode ficar sem responder por alguns segundos a
   minutos, dependendo do tamanho do subgrupo).
6. Abre a janela **Escolha onde salvar sua planilha** ("Salvar como") com o
   nome sugerido `Subgrupo_<código>_Relatorio_<dd-mm-aaaa>.xlsx`. Escolha a
   pasta e confirme. Se vários subgrupos foram marcados, sai **um único
   arquivo** com todos e o nome usa o código do último subgrupo processado —
   renomeie se quiser.
7. Mensagem **Sucesso — "Planilha salva em: ..."**.

Resultado: um Excel com as colunas ADMINISTRADORA, APOLICE, SEQ, FATURA,
POSTO, SEQ_POSTO, NOME_POSTO, NOME, DOCUMENTO, SEXO, CIVIL, NASC, DT_INI_VIG,
DT_FIM_VIG, PRODUTO, SUBPORTO, COBERTURA1, VALOR1, COBERTURA2, VALOR2
(datas em dd/mm/aaaa).

### 2.4 Fatura 99 em amarelo — cobertura provisória (só VIDA RJ, 1317377)

Para o subgrupo **1317377 VIDA RJ**, a planilha inclui também os segurados
que ainda não têm fatura (**cobertura provisória**), como fazia o sistema
Delphi. Essas linhas saem com **FATURA = 99** e a célula da coluna FATURA
fica **amarela e em negrito**; o cabeçalho da coluna tem um comentário
explicando a legenda. Trate essas linhas como provisórias na conferência.
Nenhum outro subgrupo tem esse comportamento hoje.

**Aviso "COBERTURA PROVISÓRIA NÃO INCLUÍDA"**: se a inclusão dos provisórios
falhar, a planilha é salva normalmente **sem** eles e, depois da mensagem de
sucesso, aparece a mensagem **Atenção** começando com
"COBERTURA PROVISÓRIA NÃO INCLUÍDA no subgrupo 1317377: ..." e o texto
"A planilha foi gerada SEM os segurados provisórios. Verifique a procedure
GERA_REL_PLA_SISTEMA99." Anote o erro completo e avise o responsável pelo
banco (ver §8, item "erro -802"). O banco não fica com marca pendente: a
operação é desfeita automaticamente.

### 2.5 Ver Inconsistências (Tela)

Lista **todas** as faturas de Vida ativas no **mês** da data de vigência
cuja apólice está sem subgrupo (SUBPORTO vazio), ignorando apólices que
começam com `C` e a `VR0001`. Serve para conferir o cadastro antes de gerar.

- Se não houver nada: "Nenhuma inconsistência encontrada para esta data!".
- Se houver: abre a janela **Relatório de Inconsistências** com as colunas
  APOLICE, SEQ, FATURA, NOME (administradora), SUBPORTO e COUNT (quantidade).

Diferença para a grade do §2.3 passo 4: esta tela mostra o banco inteiro; a
grade da geração mostra só as apólices que pertencem aos subgrupos marcados.

### 2.6 Agendar Robô (todos os subgrupos) — robô noturno

O robô gera, de uma vez, **um arquivo por subgrupo** (todos os subgrupos da
lista, independentemente das caixas marcadas), em um horário escolhido, sem
abrir "Salvar como".

Passo a passo:

1. Clique em **Agendar Robô (todos os subgrupos)**. Abre a janela
   **Agendar Robô - Subgrupos de Vida**, que informa quantos subgrupos serão
   processados.
2. **Data de Vigência:** vem igual ao calendário principal; ajuste se
   precisar.
3. **Pasta onde salvar os arquivos:** clique em **Escolher...** e selecione
   uma pasta existente (ela não é criada automaticamente aqui).
4. **Horário de início (HH:MM):** padrão `22:00`. Se o horário já passou
   hoje, o robô fica para amanhã no mesmo horário.
5. Clique em:
   - **Agendar** (verde): marca o disparo. Aparece a mensagem **Robô
     agendado** ("O robô vai gerar N subgrupos em dd/mm/aaaa às HH:MM ...
     Deixe o programa aberto e o computador ligado.") e a linha de estado
     da janela Vida passa a mostrar, em roxo, "Robô agendado para ..." com a
     vigência e a pasta.
   - **Executar agora** (azul): roda imediatamente, útil para testar.
   - **Cancelar agendamento** (vermelho): desfaz o agendamento ("Agendamento
     cancelado." na linha de estado). Se não houver agendamento: "Não há
     agendamento ativo."

Enquanto roda, a linha de estado mostra "Robô em execução..." (laranja) e os
três botões da janela ficam desabilitados. Ao terminar aparece **Robô
concluído** com "Gerados / Sem dados / Erros" e o caminho do
`robo_log.txt`; a linha de estado fica verde (sem erros) ou vermelha (com
erros).

O que o robô produz na pasta escolhida:

- `Subgrupo_<código>_Relatorio_<dd-mm-aaaa>.xlsx` para cada subgrupo com
  dados (com o mesmo destaque amarelo da fatura 99 em VIDA RJ);
- `robo_log.txt` (acrescentado a cada execução, nunca apagado), com início,
  fim e uma linha por subgrupo: `[OK    ]` (gerado, com o total de linhas),
  `[VAZIO ]` (sem dados na vigência), `[ERRO  ]` (falhou — a mensagem está
  na linha) e `[AVISO ]` (gerado sem a cobertura provisória, ver §2.4).

Cuidados obrigatórios:

- **O programa tem de ficar aberto e o PC ligado, sem hibernar nem
  suspender**, até o fim da execução. O agendamento é interno ao programa:
  se o PC dormir ou o programa for fechado, o robô não roda. Peça ao
  responsável pela máquina para desativar a suspensão (ver
  `MANUAL-INSTALACAO.md`, §8).
- **Ninguém pode usar o módulo Vida em outra máquina enquanto o robô roda**
  (nem a geração manual, nem outro robô): as tabelas temporárias do banco
  são compartilhadas e uma geração apaga os dados da outra. Combine o horário
  com a equipe.
- O robô **não** faz a checagem de inconsistências do §2.3 (não pode parar
  esperando resposta). Rode **Ver Inconsistências (Tela)** antes de agendar.
- Se o robô for disparado com a geração manual em andamento, ou vice-versa,
  aparece "O robô está em execução. Aguarde o término." / "O robô já está
  em execução.". Aguarde.

Fechar a janela Vida:

- Com robô **agendado**: aparece "Há um robô agendado. Fechar a janela
  CANCELA o agendamento. Fechar mesmo assim?" — **Sim** fecha e cancela,
  **Não** mantém a janela aberta e o agendamento.
- Com robô **em execução**: a janela não fecha ("O robô está gerando as
  planilhas. Aguarde o término para fechar.").

### 2.7 Mensagens do módulo Vida e o que fazer

| Mensagem | Significado / ação |
|---|---|
| "Erro ao carregar subgrupos: ..." (ao abrir) | Sem conexão com o banco. Veja §8 "Banco fora do ar". Feche e abra a janela depois. |
| "Data de vigência inválida." | Digite a data no formato dd/mm/aaaa ou escolha no calendário. |
| "Selecione ao menos um subgrupo!" | Marque pelo menos uma caixa. |
| Janela "Inconsistências no escopo do(s) subgrupo(s)" | Ver §2.3 passo 4. |
| "Nenhum dado encontrado para os filtros selecionados." | Não há fatura ativa dos subgrupos na vigência. Confira a data (alguns subgrupos não têm fatura todo mês). |
| "A exportação foi cancelada pelo usuário." | Você fechou o "Salvar como". Gere de novo. |
| "COBERTURA PROVISÓRIA NÃO INCLUÍDA ..." | Ver §2.4. Planilha válida, mas sem os provisórios. |
| "Erro durante o processamento: ..." (Erro Crítico) | Falha no banco ou na gravação. Anote o texto completo. Se contiver `-802` ou `string right truncation`, ver §8. |
| "Escolha uma pasta de destino válida." (robô) | A pasta não existe; crie-a antes ou escolha outra. |
| "Horário inválido. Use o formato HH:MM (ex.: 22:30)." | Corrija o horário. |

---

## 3. PORTO ASSISTÊNCIA

Janela: **PORTO ASSISTÊNCIA — Geração e Envio da Relação**.

### 3.1 O que faz

Gera a planilha mensal `relacao-envio-porto-<MMAAAA>.xlsx` com três abas
(Código 1 - Residencial, Código 2 - Auto, Código 3 - Empresarial), no layout
que a Porto espera (12 colunas: ENDERECO, NUMERO, COMPLEMENTO, CEP, BAIRRO,
CIDADE, SIGLAESTADO, NOME, CPF_CNPJ, DATANASCIMENTO, NOMEINQUILINO,
CPFCNPJINQUILINO), e, se você pedir, envia o arquivo para o SFTP da Porto.
`MMAAAA` é o mês/ano da data de vigência (ex.: 01/10/2026 gera `...-102026`).

### 3.2 Campos e botões da tela

- **Pasta onde salvar a planilha:** campo de texto + botão **Procurar...**.
- **Data de início de vigência (:inivig das queries):** calendário.
- **Produtos:** uma linha por produto, cada uma com a caixa
  **Código 1 - Residencial** / **Código 2 - Auto** / **Código 3 - Empresarial**
  (marcada = entra na planilha) e a escolha **Base toda** ou **Quantidade:**
  seguida de um campo numérico (padrão 10000) e a palavra "linhas".
  Com **Quantidade**, só as N primeiras linhas do produto entram — use para
  gerar amostras de teste; para o envio oficial use **Base toda**.
- Caixa **Enviar para a Porto (SFTP /Porto/Remessa) após gerar**.
- Botão **Gerar Planilha** (verde).
- **Log:** área de texto com o andamento.

Todas as escolhas (pasta, produtos, quantidades e **inclusive a caixa de
envio**) ficam gravadas e voltam preenchidas na próxima abertura. Por isso,
**sempre confira a caixa de envio antes de clicar em Gerar Planilha**.

### 3.3 Passo a passo

1. Confira a pasta e a data de início de vigência.
2. Marque os produtos e deixe **Base toda** (ou informe uma quantidade para
   teste).
3. Decida sobre a caixa **Enviar para a Porto (SFTP /Porto/Remessa) após
   gerar**:
   - **desmarcada**: só gera o arquivo na pasta (recomendado para conferir
     antes);
   - **marcada**: depois de gerar, o arquivo é enviado automaticamente para a
     pasta `/Porto/Remessa` do SFTP da Porto Seguro.
4. Clique em **Gerar Planilha**. O botão fica desabilitado até o fim.
5. Acompanhe o log: para cada produto aparece "Código N - Nome: executando
   <arquivo>.sql...", um contador "... N linhas" e ao final "Código N - Nome:
   N linhas geradas (base toda)" ou "(limite N)". Depois:
   "Arquivo gerado: <caminho> (N linhas no total)", o bloco
   "--- Total de linhas por produto ---", "TOTAL GERAL: N linhas" e, se o
   envio estava marcado, "Enviando <arquivo> (N bytes) para /Porto/Remessa
   ..." e "[ok] Enviado e verificado: /Porto/Remessa/<arquivo> (N bytes)".
   A última linha é "Concluído.".

### 3.4 Cuidado com o envio SFTP

**Tudo o que cai em `/Porto/Remessa` pode ser processado pela seguradora.**
Portanto:

- nunca envie planilha de teste (gerada com **Quantidade**) com a caixa de
  envio marcada;
- confira os totais do log e abra o Excel antes de enviar; se preferir, gere
  sem enviar, confira, e depois gere de novo com a caixa marcada (o arquivo é
  o mesmo);
- o envio é seguro contra arquivo pela metade: sobe com nome temporário
  `.part`, o tamanho é conferido e só então o arquivo recebe o nome final.
  Se o log mostrar "[ERRO] Tamanho divergente ... Upload descartado.", nada
  ficou no servidor — tente de novo;
- o envio não pede confirmação: a caixa marcada já é a confirmação.

### 3.5 Mensagens e o que fazer

| Mensagem | Significado / ação |
|---|---|
| "Informe a pasta de destino." | Preencha a pasta (Procurar...). |
| "Data de início de vigência inválida." | Corrija a data. |
| "Quantidade inválida no Código N." | O campo de quantidade precisa ser um número inteiro maior que zero. |
| "Selecione ao menos um produto." | Marque ao menos um código. |
| Log "(limite atingido — <arquivo>.sql não executada)" | Normal com Quantidade: o produto Residencial tem duas consultas e a segunda só roda se ainda houver saldo. |
| Log "[ERRO] A query em queries/... ainda não foi preenchida (contém o marcador TODO)." | Arquivo de consulta incompleto — avise o programador. |
| Log "[ERRO] Código N ...: a query ... não retorna as colunas [...]" | Alguém alterou a consulta e quebrou o layout — avise o programador. |
| Log "[ERRO] ... getaddrinfo ... / Name or service not known / timed out" (no envio) | Falha de rede ou DNS no SFTP — ver §8. O arquivo local foi gerado; só o envio falhou. |
| Log "[ERRO] Authentication failed" | Usuário/senha do SFTP inválidos no `.env` — avise quem instalou. |
| Log "[ERRO] Permission denied: '...xlsx'" | O Excel está aberto com o arquivo anterior. Feche e gere de novo. |

---

## 4. GERA PORTO DENTAL

Janela: **GERA PORTO DENTAL — Consulta e Geração da Planilha**.

### 4.1 O que faz

Gera `portodental-<MMAAAA>.xlsx` (aba **PORTO DENTAL**) com os segurados das
faturas de Porto Dental da vigência, em **duas etapas obrigatórias**:
primeiro consultar (ver faturas e total de vidas), depois gerar.

### 4.2 Campos e botões

- **Pasta onde salvar a planilha:** + **Procurar...**
- **Data de início de vigência (:inivig das queries):** calendário.
- **1) Consultar Vidas** (verde).
- **2) Gerar Planilha Final** (verde) — começa **desabilitado**; só libera
  depois de uma consulta com resultado.
- **Log:**

### 4.3 Passo a passo

1. Confira pasta e data.
2. Clique em **1) Consultar Vidas**. O log mostra "Consultando vidas —
   vigência dd/mm/aaaa...", uma linha por fatura encontrada (FATURA, APOLICE,
   NOME da administradora, VIDAS, descrição do produto), depois
   "Faturas encontradas: N" e **"TOTAL DE VIDAS A ENVIAR: N"**.
   - Se houver faturas: "Consulta concluída — o botão 2) Gerar Planilha Final
     foi liberado."
   - Se não houver: "Nenhuma fatura na vigência — nada a gerar." (o botão 2
     continua desabilitado; confira a data).
3. Confira o total de vidas com o esperado para o mês.
4. Clique em **2) Gerar Planilha Final**. O log mostra "Gerando planilha
   final — vigência dd/mm/aaaa (N faturas)...", o contador de linhas e
   "Arquivo gerado: <caminho> (N linhas)" / "Concluído: N linhas em
   <caminho>". O total de linhas deve bater com o TOTAL DE VIDAS da consulta.

**Importante**: a geração usa a vigência e as faturas **da consulta feita**.
Se mudar a data depois da etapa 1, **consulte de novo** antes de gerar —
senão a planilha sai com a vigência antiga.

Colunas da planilha: FATURA, APOLICE, ADMINISTRADORA, NOME, NOME_POSTO,
NOME_SEGURADO, CPF_CNPJ, SEXO, NASCIMENTO, NOME_MAE.

### 4.4 Mensagens

| Mensagem | Ação |
|---|---|
| "Informe a pasta de destino." / "Data de início de vigência inválida." | Corrija o campo. |
| "Rode a consulta (etapa 1) antes de gerar." | Clique em 1) Consultar Vidas primeiro. |
| Log "[ERRO] ..." na consulta | O botão 2 fica desabilitado. Se for erro de conexão, ver §8. |
| Log "[ERRO] Permission denied" na geração | Feche o Excel que está com o arquivo aberto. |

---

## 5. GERAR DENTAL SEMPRE ODONTO

Janela: **GERAR DENTAL SEMPRE ODONTO — Consulta e Geração da Planilha**.
Botões em **azul** (produto não-Porto).

Funciona **exatamente como o GERA PORTO DENTAL** (§4): mesma tela, mesmas
duas etapas (**1) Consultar Vidas** libera **2) Gerar Planilha Final**),
mesmas mensagens. Diferenças:

- considera só as apólices do tipo dental "S" (Sempre Odonto);
- o arquivo é `sempreodonto-<MMAAAA>.xlsx`, aba **SEMPRE ODONTO**;
- a pasta lembrada é independente da do Porto Dental.

---

## 6. GERAR ARQUIVO FUNERAL

Janela: **GERAR ARQUIVO FUNERAL**, com o título "Segurados de Vida com
cobertura FUNERAL ou CERIMONIAL".

### 6.1 O que faz

Gera `funeral-<MMAAAA>.xlsx` (aba **FUNERAL**) com os segurados de Vida que
têm, nas faturas ativas da vigência, alguma cobertura cujo nome contém
FUNERAL ou CERIMONIAL. Colunas: ADMINISTRADORA, APOLICE, NOME, CPF,
NASCIMENTO (dd/mm/aaaa). **CPF não se repete**: se o mesmo CPF aparece em
mais de uma fatura/apólice, fica só a primeira ocorrência.

### 6.2 Passo a passo

1. **Pasta onde salvar a planilha:** (Procurar...) e **Data de início de
   vigência:**.
2. Clique em **Gerar Arquivo Funeral** (verde). Etapa única; o botão fica
   desabilitado até o fim (cerca de 15 segundos para a base atual).
3. Log: "Consultando segurados com cobertura FUNERAL/CERIMONIAL — vigência
   dd/mm/aaaa...", "Linhas retornadas pelo banco: N", "Duplicidades de CPF
   removidas: N", "Segurados a enviar: N", "Planilha gravada: <caminho>" e
   "Concluído: N segurados em <caminho>".
   Se não houver ninguém: "Nenhum segurado com cobertura funeral na vigência
   — nada a gerar." (nenhum arquivo é criado).

### 6.3 Mensagens

As mesmas de pasta/data dos outros módulos ("Informe a pasta de destino.",
"Data de início de vigência inválida.") e `[ERRO] ...` no log para falha de
banco ou gravação (ver §8).

---

## 7. Boas práticas de operação

- Gere primeiro, confira o Excel (totais, datas de vigência, nomes), e só
  então envie ou encaminhe.
- No módulo Vida, **uma geração por vez em toda a rede** (manual ou robô):
  as tabelas temporárias são compartilhadas entre todas as máquinas.
- Rode **Ver Inconsistências (Tela)** no começo do mês e corrija o SUBPORTO
  das apólices antes de gerar os subgrupos (o robô não avisa).
- Mantenha a caixa de envio SFTP desmarcada por padrão; marque só na
  geração oficial.
- Não altere nada na pasta do programa (arquivos `.sql`, `.json`, `.env`).
  Dúvidas de cadastro são do sistema de origem (Delphi); dúvidas de
  programa, do suporte.

---

## 8. Problemas comuns

### Erro `-802` / "string right truncation" (módulo Vida)

Sintoma: "Erro durante o processamento: ... SQLCODE: -802 ... string right
truncation" na geração manual, linha `[ERRO  ]` com esse texto no
`robo_log.txt`, ou o aviso "COBERTURA PROVISÓRIA NÃO INCLUÍDA".

Causa: uma **procedure do banco** (`GERA_REL_PLA_SISTEMA` ou
`GERA_REL_PLA_SISTEMA99`) tem campos internos menores que os dados (ex.:
nome de bairro ou de cobertura com mais de 30 letras). Não é problema da
planilha nem do seu PC. **Ação**: avise o responsável pelo banco (DBA) para
aplicar a correção que está em `queries/alter_gera_rel_pla_sistema.sql` e
`queries/alter_gera_rel_pla_sistema99.sql` (ambas já aplicadas no banco de
produção em 03/11/2026; o erro só deve voltar em outro banco ou após uma
restauração). O programa não aplica essa correção sozinho.

### Envio SFTP falha por DNS (Porto Assistência)

Sintoma: `[ERRO]` no envio citando `getaddrinfo`, "nome não resolvido",
"Name or service not known" ou "timed out"; a planilha foi gerada
normalmente.

Causa: a rede interna **não resolve** o endereço `sftp.portoseguro.com.br`.
O programa já tenta automaticamente um endereço IP reserva. Se mesmo assim
falhar, ou o IP da Porto mudou (quem instalou atualiza `SFTP_FALLBACK_IP` no
`.env`, ver `MANUAL-INSTALACAO.md`), ou a saída para a internet na porta
2022 está bloqueada (firewall/proxy) — chame a infraestrutura. O arquivo
continua na pasta local; depois de resolvido, gere de novo com a caixa de
envio marcada (ou peça para enviarem manualmente).

### Banco fora do ar / sem conexão

Sintomas: "Erro ao carregar subgrupos: ..." ao abrir o módulo Vida (lista de
subgrupos vazia), `[ERRO]` logo no início dos outros módulos com textos como
"Unable to complete network request to host", "connection refused",
"Your user name and password are not defined" ou "I/O error".

O que fazer:

1. Veja se os sistemas Delphi também não abrem o banco — se não abrem, o
   servidor `192.168.0.6` (Firebird) está fora ou a rede caiu; chame a
   infraestrutura.
2. Se só este programa falha com "user name and password", o `.env` está
   com usuário/senha errados — quem instalou deve conferir.
3. Se aparecer "Variável obrigatória ausente no .env" ao abrir o programa,
   o `.env` está incompleto (ver `MANUAL-INSTALACAO.md`).
4. Depois de restabelecido, feche e abra a janela do módulo de novo.

### Pasta inválida

- Porto Assistência / Dental / Sempre Odonto / Funeral: se a pasta não
  existe, o sistema cria. Se o caminho é inválido (unidade inexistente,
  caractere proibido, sem permissão), aparece `[ERRO]` com "No such file or
  directory", "Permission denied" ou "The filename, directory name, or volume
  label syntax is incorrect". Use **Procurar...** e escolha uma pasta
  existente em que você possa gravar (evite pastas de rede que exigem
  senha).
- Robô do Vida: a pasta **precisa existir** ("Escolha uma pasta de destino
  válida."). Crie-a antes no Explorador de Arquivos.
- Pasta de rede que fica indisponível no meio da execução do robô: os
  subgrupos seguintes aparecem como `[ERRO  ]` no log. Prefira pasta local e
  copie depois.

### A janela "não responde" durante a geração

No módulo Vida a geração manual roda na própria janela e ela pode ficar
"Não respondendo" por alguns minutos em subgrupos grandes — é normal,
aguarde. Nos demais módulos a janela continua respondendo e o log mostra o
progresso.

### O robô não rodou

Confira, nesta ordem: o programa ficou aberto a noite toda? O PC ficou
ligado sem suspender/hibernar e sem reiniciar por atualização do Windows?
Alguém fechou a janela Vida (o fechamento cancela o agendamento)? O
`robo_log.txt` da pasta tem a execução da data? Se não tem, o disparo não
aconteceu: reagende e verifique as configurações de energia da máquina
(`MANUAL-INSTALACAO.md`, §8).
