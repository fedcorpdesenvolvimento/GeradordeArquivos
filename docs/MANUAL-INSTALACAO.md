# MANUAL DE REQUISITOS E INSTALAÇÃO — SISTEMA DE ENVIO PORTO SEGURO

Público: quem vai instalar ou atualizar o sistema em uma máquina Windows.
Versão de 03/11/2026 (ambiente de referência levantado nessa data).
Operação do dia a dia: `docs/MANUAL-OPERACAO.md`. Detalhes de código:
`docs/DOCUMENTACAO.md`.

**Este manual não contém senhas.** Usuário/senha do Firebird e do SFTP ficam
no arquivo `.env`, que é preenchido à mão em cada máquina e nunca é
versionado, copiado para e-mail ou deixado em pasta de rede.

---

## 1. Requisitos

### 1.1 Hardware e sistema operacional

- Windows 10/11 64 bits (referência: Windows 11 Pro). Qualquer PC de
  escritório atual serve: 8 GB de RAM são suficientes (a maior geração,
  Porto Assistência base toda, grava em modo "streaming" e não carrega a base
  inteira em memória). Reserve alguns GB de disco para as planilhas geradas.
- Para o **robô noturno** do módulo Vida: a máquina precisa ficar ligada e
  sem suspender/hibernar durante a noite (ver §8).

### 1.2 Rede

| Destino | Porta | Para quê |
|---|---|---|
| `192.168.0.6` (servidor Firebird 2.5, banco `FATURA.GDB`) | TCP 3050 | Todos os módulos |
| `sftp.portoseguro.com.br` (SFTP da Porto Seguro) | TCP 2022 (saída para a internet) | Envio do Porto Assistência |

Observações:

- O DNS interno **não resolve** `sftp.portoseguro.com.br`. O programa tenta
  o nome e, se falhar, usa o IP guardado em `SFTP_FALLBACK_IP` no `.env`.
  Para descobrir/confirmar o IP atual use um DNS público:
  `nslookup sftp.portoseguro.com.br 8.8.8.8`.
- Firewall/proxy de saída precisa liberar a porta 2022 para esse destino.
- O repositório do código é clonado pela rede uma vez; depois disso o
  programa roda localmente.

### 1.3 Permissões

- Conta Windows com permissão para instalar o Python (ou um Python já
  instalado para todos os usuários) e para gravar na pasta de instalação
  (ex.: `C:\apps\EnvioPorto`) e nas pastas de saída das planilhas.
- Usuário do Firebird com permissão de leitura nas tabelas usadas e de
  **escrita** nas tabelas temporárias e nas marcas do módulo Vida
  (`TEMP_RELATORIO_VIDA`, `TEMP_RELATORIO_VIDA2`, `VIDA_COBERTURA_PROV`,
  `VIDA_SEGURADOS_MOV`, `VIDA_SEGURADO_FIN`) e de execução das procedures
  `GERA_REL_PLA_SISTEMA` e `GERA_REL_PLA_SISTEMA99`. Na prática usa-se o
  mesmo usuário dos sistemas Delphi.
- Usuário do SFTP fornecido pela Porto Seguro, com gravação em
  `/Porto/Remessa`.
- Acesso de leitura ao repositório git do projeto.

### 1.4 Software

| Componente | Versão de referência | Observação |
|---|---|---|
| Python | **3.14.3** (mínimo **3.12**) | Instalado via PyManager em `C:\Program Files\PyManager\python.exe`. Usar **64 bits**. `tkinter` já vem com o Python (não instalar à parte). |
| Client Firebird 2.5 (`fbclient.dll`) | 2.5, **64 bits** | Encontrada em `C:\Windows\System32\fbclient.dll` (e também em `C:\Program Files\Firebird\Firebird_2_5\bin`). O driver `fdb` a localiza sozinho (`fdb.load_api()`), sem variável de ambiente. Já existe nas estações que rodam os sistemas Delphi; em máquina nova, instalar o client do Firebird 2.5 64 bits ou copiar a DLL para `System32`. |
| git | qualquer versão atual | Para clonar e atualizar. |
| Pacotes Python (`requirements.txt`) | customtkinter 5.2.2, tkcalendar 1.6.1, pandas 3.0.1, openpyxl 3.1.5, fdb 2.0.4, paramiko 5.0.0, python-dotenv 1.2.3 (mínimo 1.1.1) | Instalados pelo `pip` no passo 3. |

A arquitetura (bits) da `fbclient.dll` tem de ser a mesma do Python. Python
64 bits + DLL 32 bits dá erro ao carregar a API (ver §9).

---

## 2. Onde instalar: clone local, não compartilhamento de rede

Instale em uma pasta **local** da máquina, por exemplo `C:\apps\EnvioPorto`,
em vez de rodar direto do compartilhamento `U:\--2021\04-EnvioPorto`.
Motivos:

- o `.env` contém as senhas do Firebird e do SFTP; na rede ele fica exposto
  a qualquer um com acesso ao compartilhamento;
- uma queda da rede no meio de uma geração (ou do robô noturno) derruba o
  programa, que carrega módulos e consultas `.sql` do disco em tempo de
  execução;
- cada máquina guarda suas próprias preferências (`*.json`).

O compartilhamento de rede continua sendo a origem do código (repositório
git). Se o git reclamar do caminho UNC ao clonar ou atualizar
("detected dubious ownership"), registre a pasta como segura:

```powershell
git config --global --add safe.directory "//servidor/compartilhamento/--2021/04-EnvioPorto"
# ou, se mapeado como unidade:
git config --global --add safe.directory "U:/--2021/04-EnvioPorto"
```

---

## 3. Instalação passo a passo (PowerShell)

Abra o **PowerShell** (não precisa ser como administrador, exceto para
instalar o Python ou copiar a DLL em `System32`).

### Passo 1 — Python

Se `python --version` não responder 3.12 ou superior, instale o Python 3.14
64 bits (via PyManager, como na máquina de referência, ou pelo instalador de
python.org marcando "Add python.exe to PATH" e "tcl/tk and IDLE"). Depois:

```powershell
python --version        # esperado: Python 3.14.x (mínimo 3.12)
python -c "import tkinter; print('tkinter ok')"
```

### Passo 2 — Client Firebird

```powershell
Test-Path "C:\Windows\System32\fbclient.dll"
```

Se retornar `False`, instale o client do Firebird 2.5 **64 bits** (ou copie
`fbclient.dll` 64 bits de uma estação que já roda os sistemas Delphi para
`C:\Windows\System32`). Confira a arquitetura antes de copiar.

### Passo 3 — Clonar o repositório e instalar os pacotes

```powershell
New-Item -ItemType Directory -Force C:\apps | Out-Null
Set-Location C:\apps
git clone "U:\--2021\04-EnvioPorto" EnvioPorto
Set-Location C:\apps\EnvioPorto
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se preferir isolar os pacotes em um ambiente virtual (recomendado quando a
máquina tem outros programas Python):

```powershell
Set-Location C:\apps\EnvioPorto
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # se bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install -r requirements.txt
```

Com venv, todos os comandos `python ...` deste manual devem ser executados
com o ambiente ativado (`.\.venv\Scripts\Activate.ps1`).

### Passo 4 — Criar o `.env`

Ver §4.

### Passo 5 — Verificar

Ver §5.

---

## 4. Configuração do `.env`

O `.env` fica na raiz da instalação (ao lado de `main.py`). Ele **não existe
no repositório** (está no `.gitignore`); crie-o a partir do modelo:

```powershell
Set-Location C:\apps\EnvioPorto
Copy-Item .env.exemplo .env
notepad .env
```

Preencha as 13 variáveis (formato `NOME=valor`, sem aspas, sem espaços em
volta do `=`; salve o arquivo em UTF-8):

| Variável | Obrigatória | Conteúdo |
|---|---|---|
| `FB_HOST` | sim | IP/nome do servidor Firebird (`192.168.0.6`) |
| `FB_PORT` | não (padrão 3050) | Porta do Firebird |
| `FB_DATABASE` | sim | Caminho do banco **como visto pelo servidor** (`E:\SISTEMA\BASE_CHEQUE\BASE\FATURA.GDB`) |
| `FB_USER` | sim | Usuário do Firebird |
| `FB_PASSWORD` | sim | Senha do Firebird |
| `FB_CHARSET` | não (padrão ASCII) | Charset padrão das conexões. Deixar `ASCII`: o módulo Vida depende dele; os demais módulos pedem WIN1252 por conta própria |
| `FB_POOL_SIZE` | não (padrão 5) | Conexões ociosas mantidas no pool |
| `SFTP_HOST` | sim | `sftp.portoseguro.com.br` |
| `SFTP_FALLBACK_IP` | sim | IP usado quando o DNS não resolve o host (obter com `nslookup sftp.portoseguro.com.br 8.8.8.8`) |
| `SFTP_PORT` | não (padrão 2022) | Porta do SFTP |
| `SFTP_USER` | sim | Usuário do SFTP fornecido pela Porto |
| `SFTP_PASSWORD` | sim | Senha do SFTP |
| `SFTP_DESTINO` | não (padrão `/Porto/Remessa`) | Pasta remota de envio |

Mesmo as variáveis com padrão devem constar no arquivo (o modelo já as
traz); as marcadas como obrigatórias, se vazias, impedem o programa de abrir
com a mensagem "Variável obrigatória ausente no .env: NOME".

Os nomes `FB_*` são os mesmos do FedHub-Backend, para o mesmo `.env` servir
na futura versão web.

**Regras de segurança do `.env`:**

- nunca fazer `git add .env`, nunca anexar em e-mail/chat, nunca deixar em
  pasta compartilhada;
- ao desinstalar ou trocar de máquina, apagar o arquivo;
- os valores de usuário/senha são obtidos com o responsável pelo banco e
  pelo cadastro na Porto, não estão em nenhum documento do projeto.

---

## 5. Verificação (checklist)

Execute na pasta da instalação (`C:\apps\EnvioPorto`), com o venv ativado se
houver. Nenhum destes comandos grava no banco.

```powershell
Set-Location C:\apps\EnvioPorto

# 1. Python 3.12+ e tkinter
python --version
python -c "import tkinter; print('tkinter', tkinter.TkVersion)"

# 2. Pacotes nas versões do requirements.txt
python -m pip list | Select-String "customtkinter|tkcalendar|pandas|openpyxl|fdb|paramiko|python-dotenv"

# 3. Client do Firebird carregável pelo driver
python -c "import fdb; fdb.load_api(); print('fbclient ok')"

# 4. .env completo (config.py aborta se faltar variável) — não imprime valores
python -c "import config; print('env ok; host', config.DB_CONFIG['host'], 'porta', config.DB_CONFIG['port'])"

# 5. Conexão real com o banco via db.conectar() (somente leitura)
python -c "import db; c = db.conectar(); cur = c.cursor(); cur.execute('SELECT 1 FROM RDB$DATABASE'); print('banco ok', cur.fetchone()); c.close()"

# 6. Saída de rede para o SFTP (sem autenticar)
Test-NetConnection -ComputerName sftp.portoseguro.com.br -Port 2022   # pode falhar só por DNS
nslookup sftp.portoseguro.com.br 8.8.8.8                               # IP para SFTP_FALLBACK_IP
```

Resultados esperados: `Python 3.14.x`; sete pacotes listados nas versões da
§1.4; `fbclient ok`; `env ok; host 192.168.0.6 porta 3050`; `banco ok (1,)`;
no item 6, se `TcpTestSucceeded : False` por "nome não resolvido", confirme
o IP pelo `nslookup` e repita `Test-NetConnection` com o IP.

Testes automatizados (opcional, recomendado após instalar):

```powershell
# unitários — sem banco, rápidos
python -m unittest discover -s tests

# integração — acessa o Firebird; só roda com a variável definida
$env:PORTO_TESTE_INTEGRACAO = "1"
python -m unittest discover -s tests
Remove-Item Env:PORTO_TESTE_INTEGRACAO
```

Atenção com os testes de integração: `test_integracao_cobertura_provisoria`
exercita o fluxo da fatura 99 do módulo Vida (marca e desmarca registros em
transação, como a geração real) e usa as tabelas temporárias compartilhadas.
Rode-os **somente quando ninguém estiver gerando Vida** em outra máquina e,
de preferência, fora do horário de produção. Os demais são só leitura.

---

## 6. Primeira execução

```powershell
Set-Location C:\apps\EnvioPorto
python main.py
```

Deve abrir a janela **SISTEMA DE ENVIO PORTO SEGURO** com cinco botões.
Teste rápido sem risco:

1. **SUBGRUPOS DE VIDA**: a lista "Selecione os Subgrupos:" deve carregar os
   subgrupos (prova que banco e `.env` estão certos). Clique em **Ver
   Inconsistências (Tela)** — é só leitura.
2. **GERA PORTO DENTAL**: clique em **1) Consultar Vidas** — só leitura,
   mostra o total de vidas da vigência.
3. **PORTO ASSISTÊNCIA**: gere uma amostra com **Quantidade: 10** em cada
   produto e a caixa **"Enviar para a Porto (SFTP /Porto/Remessa) após
   gerar" DESMARCADA**. Confira o arquivo em `saida\`.

**Nunca envie arquivo de teste para o SFTP**: tudo o que entra em
`/Porto/Remessa` pode ser processado pela seguradora. A validação do envio
em uma máquina nova deve ser feita com o arquivo oficial do mês, pelo
operador responsável.

Atalho na área de trabalho (opcional): crie um atalho para
`"C:\Program Files\PyManager\python.exe" C:\apps\EnvioPorto\main.py` (ou
`pythonw.exe` para não abrir a janela preta do console) com "Iniciar em"
`C:\apps\EnvioPorto`. Se usar venv, aponte para
`C:\apps\EnvioPorto\.venv\Scripts\pythonw.exe`.

Arquivos criados pelo uso (podem ser apagados; são recriados):
`porto_assistencia.json`, `porto_dental.json`, `sempre_odonto.json`,
`funeral.json` (preferências de tela) e a pasta `saida\`.

---

## 7. Atualização

Com o programa **fechado** (e sem robô agendado):

```powershell
Set-Location C:\apps\EnvioPorto
git pull
python -m pip install -r requirements.txt
python main.py
```

- `git pull` não toca no `.env` nem nos `*.json` (estão no `.gitignore`).
- Se o `pull` falhar por alteração local em arquivo versionado (ex.: alguém
  editou um `.sql` na máquina), use `git status` para ver o que mudou e
  `git stash` para guardar antes de atualizar — ou descarte com
  `git checkout -- <arquivo>` se a alteração não era intencional.
- Se o `pull` trouxer um script em `queries/alter_*.sql`, ele é uma
  correção **do banco** (procedure/tabela) que o DBA aplica como SYSDBA no
  servidor; o programa não executa DDL. Os dois scripts existentes
  (`alter_gera_rel_pla_sistema.sql`, `alter_gera_rel_pla_sistema99.sql`)
  já estão aplicados no banco de produção desde 03/11/2026 e só precisam ser
  reaplicados em um banco restaurado ou de homologação.
- Após mudança de versão do Python, repita `pip install -r requirements.txt`
  (o novo Python não herda pacotes).

---

## 8. Preparação da máquina para o robô noturno (módulo Vida)

O robô é disparado pelo próprio programa aberto; se o Windows suspender,
hibernar ou reiniciar, ele não roda. Em PowerShell **como administrador**:

```powershell
# nunca suspender nem hibernar quando ligado na tomada
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
# opcional: manter a tela acesa não é necessário; pode desligar só o monitor
powercfg /change monitor-timeout-ac 15
```

Além disso:

- **Windows Update**: em Configurações > Windows Update > Opções avançadas,
  ajuste o **Horário ativo** para cobrir o período do robô (ou ative "Ajustar
  horário ativo automaticamente") e desative o reinício automático fora do
  horário ativo, para a máquina não reiniciar com o programa aberto.
- Deixe o usuário logado com o programa aberto e a janela **Gerador de
  Relatórios - Vida** aberta com o agendamento feito (fechar essa janela
  cancela o robô). Bloquear a tela (Win+L) pode; fazer logoff não.
- Combine com a equipe: **ninguém usa o módulo Vida em outra máquina**
  enquanto o robô roda.
- Use pasta de destino local; se for de rede, garanta que fica acessível
  à noite.
- Antivírus/limpeza automática não devem apagar a pasta `saida\` ou
  `robo_log.txt`.

---

## 9. Problemas comuns na instalação

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python` não é reconhecido | Python fora do PATH | Reinstale marcando "Add to PATH" ou chame pelo caminho completo (`"C:\Program Files\PyManager\python.exe"`). |
| `ModuleNotFoundError: No module named 'customtkinter'` (ou outro) | Pacotes instalados em outro Python/venv | Rode `python -m pip install -r requirements.txt` com o **mesmo** `python` que abre o programa; se usa venv, ative-o. |
| `ModuleNotFoundError: No module named 'tkinter'` ou `_tkinter` | Python instalado sem tcl/tk | Reinstale o Python marcando "tcl/tk and IDLE". |
| `fdb.load_api()` falha: "Can't find Firebird Client Library" / `OSError: [WinError 126]` | `fbclient.dll` ausente | Instalar client Firebird 2.5 64 bits ou copiar a DLL para `C:\Windows\System32`. |
| `fdb.load_api()` falha com `[WinError 193] %1 is not a valid Win32 application` | DLL de 32 bits com Python 64 bits (ou vice-versa) | Trocar a DLL pela arquitetura correta. |
| "Variável obrigatória ausente no .env: FB_..." ao abrir | `.env` não criado, incompleto ou na pasta errada | Deve estar ao lado de `main.py`; preencher todas as variáveis (§4). |
| "Your user name and password are not defined" | `FB_USER`/`FB_PASSWORD` errados | Conferir com o responsável pelo banco. |
| "Unable to complete network request to host 192.168.0.6" / "connection refused" | Sem rota para o servidor ou Firebird parado | `Test-NetConnection 192.168.0.6 -Port 3050`; chamar a infraestrutura. |
| "I/O error ... FATURA.GDB" | `FB_DATABASE` com caminho errado (deve ser o caminho **no servidor**) | Ajustar para `E:\SISTEMA\BASE_CHEQUE\BASE\FATURA.GDB` (ou o caminho/alias atual do servidor). |
| Acentos trocados na planilha do Porto Assistência / Dental | Charset errado | Esses módulos fixam WIN1252 no código; se mesmo assim sair errado, confirme que o `.env` não força outro charset nem foi salvo em codificação estranha. |
| Envio SFTP: "getaddrinfo failed" / "nome não resolvido" | DNS interno não resolve o host | Esperado; o programa usa `SFTP_FALLBACK_IP`. Se ainda falhar, atualize o IP com `nslookup ... 8.8.8.8` e verifique a porta 2022 no firewall. |
| Envio SFTP: "Authentication failed" | `SFTP_USER`/`SFTP_PASSWORD` errados | Conferir com o responsável pelo cadastro na Porto. |
| `git pull`: "detected dubious ownership" | Repositório em caminho UNC | `git config --global --add safe.directory <caminho>` (§2). |
| `git pull`: "Your local changes would be overwritten" | Arquivo versionado editado localmente | `git status`, depois `git stash` ou `git checkout -- <arquivo>`. |
| Erro `-802` "string right truncation" ao gerar Vida | Procedure do banco com campo curto | DBA aplica `queries/alter_gera_rel_pla_sistema*.sql` (ver `MANUAL-OPERACAO.md`, §8). |
| `PermissionError ... .xlsx` ao gerar | Arquivo aberto no Excel | Fechar o Excel e gerar de novo. |
| Robô não rodou de noite | PC suspendeu/reiniciou ou janela Vida foi fechada | Aplicar §8 e reagendar; conferir `robo_log.txt`. |

---

## 10. Resumo do ambiente de referência (03/11/2026)

- Windows 11 Pro; Python 3.14.3 64 bits via PyManager
  (`C:\Program Files\PyManager\python.exe`); tkinter embutido.
- `fbclient.dll` 2.5 64 bits em `C:\Windows\System32` (origem:
  `C:\Program Files\Firebird\Firebird_2_5\bin`).
- Pacotes: customtkinter 5.2.2, tkcalendar 1.6.1, pandas 3.0.1,
  openpyxl 3.1.5, fdb 2.0.4, paramiko 5.0.0, python-dotenv 1.2.3.
- Firebird 2.5 em `192.168.0.6:3050`, banco `FATURA.GDB`.
- SFTP Porto: `sftp.portoseguro.com.br:2022`, destino `/Porto/Remessa`,
  DNS interno não resolve (fallback por IP no `.env`).
- `.env` com 13 variáveis (8 obrigatórias, 5 com padrão), copiado de
  `.env.exemplo`, nunca versionado.
