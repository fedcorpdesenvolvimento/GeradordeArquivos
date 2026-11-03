# Deploy no Render — tela web (branch `web-render`)

Data: 03/11/2026. Modelo copiado do CertificadosGerador (`docs/DEPLOY-RENDER.md` de lá).
A versão desktop continua na branch `main` e na pasta `U:\--2021\04-EnvioPorto`; a web
vive na branch `web-render`, pasta local `U:\--2021\04-EnvioPorto-web`. Nada do desktop
foi perdido: a web reaproveita os mesmos geradores (`modulos/gerador_*.py`).

## 1. Por que o primeiro deploy falhou

O serviço foi criado com runtime **Python** e comando `gunicorn gerador_arquivos`:

- `gunicorn` não está nas dependências e `gerador_arquivos` não existe como módulo;
- mesmo com gunicorn, o runtime Python do Render **não tem a biblioteca cliente do
  Firebird** (`libfbclient2`) que o driver `fdb` carrega. Por isso o CertificadosGerador
  usa **Docker**, e este projeto também.

Correção: apagar o serviço criado (ou mudar para Docker) e importar o `render.yaml`
desta branch como **Blueprint**.

## 2. Como o Render chega ao Firebird (resposta à pergunta do ngrok)

O Render roda na nuvem (região Ohio). Ele **não enxerga a rede local** (192.168.0.6)
de jeito nenhum: não existe "conexão local" para um serviço hospedado fora da empresa.
"Só quem está na minha rede acessa" só é possível se o **próprio servidor web rodar
dentro da rede** (um PC/VM da empresa com `uvicorn web.app:app --host 0.0.0.0`), e aí
não é Render.

Para o Render alcançar o banco há três caminhos, os mesmos do CertificadosGerador:

| Opção | Como | Prós / contras |
|---|---|---|
| **A. ngrok TCP** (teste) | Na máquina da rede onde o ngrok já está configurado (a do FedHub): `ngrok tcp 192.168.0.6:3050`. Ele devolve `0.tcp.sa.ngrok.io:NNNNN`; no Render `FB_HOST=0.tcp.sa.ngrok.io`, `FB_PORT=NNNNN`. Com o plano pago, `ngrok tcp --remote-addr=<endereço reservado> 192.168.0.6:3050` mantém o endereço fixo. | Rápido. Expõe o Firebird 2.5 (só usuário/senha) à internet enquanto o túnel está aberto; derrubar ao terminar o teste. A porta muda a cada reinício sem endereço reservado. |
| **B. Encaminhamento no roteador** | Encaminhar uma porta externa para 192.168.0.6:3050 aceitando só os IPs de saída do Render (Settings > Outbound, planos pagos). `FB_HOST` = IP público/DDNS da empresa. | Estável e mais seguro. Exige acesso ao roteador/firewall. |
| **C. API no FedHub** (definitivo) | O Render fala com o FedHub-Backend pelo gateway (ngrok pago com domínio fixo + Caddy + Kong) em vez de abrir o Firebird. | É o rumo web decidido em 27/08/2026 (CLAUDE.md). Exige implementar as rotas no FedHub. |

Nesta máquina o `ngrok` **não está no PATH**: o túnel precisa ser aberto na máquina
onde ele está instalado (a do FedHub) e ficar rodando enquanto a web estiver em uso.

## 3. Login

Dois usuários fixos, sem cadastro em banco (decisão de 03/11/2026):

| Variável | Valor |
|---|---|
| `WEB_USUARIOS` | `alberto@grupofedcorp.com.br,beneficiosocial@grupofedcorp.com.br` (já no `render.yaml`) |
| `WEB_SENHA` | senha compartilhada — **preencher no painel do Render** (Environment); no teste local fica no `.env` |
| `WEB_SENHA_2` | opcional: senha própria do segundo usuário (o número é a posição na lista) |
| `WEB_SEGREDO_SESSAO` | gerado pelo Render (`generateValue`); localmente pode ficar vazio |

Sessão em cookie assinado (8 h), 10 tentativas erradas por e-mail+IP em 15 min bloqueiam.

## 4. Subir (plano Free — criação manual, sem Blueprint)

O Blueprint (`render.yaml`) só está disponível em planos pagos. No plano Free o
serviço é criado à mão; o `render.yaml` fica como referência das variáveis.

1. **Apague** o serviço antigo (criado como runtime Python com `gunicorn`).
2. Dashboard > **New +** > **Web Service** (card "Web Services" da tela "Create a new Service").
3. *Source Code*: conectar a conta GitHub (se ainda não estiver) e escolher o
   repositório `fedcorpdesenvolvimento/GeradordeArquivos`.
4. Preencher:
   | Campo | Valor |
   |---|---|
   | Name | `envioporto-web` (vira `https://envioporto-web.onrender.com`) |
   | Region | Ohio (US East) — qualquer uma serve; não há Brasil |
   | Branch | **`web-render`** |
   | Root Directory | (em branco) |
   | Language / Runtime | **Docker** (o Render detecta o `Dockerfile`; se oferecer "Python 3", troque para Docker) |
   | Dockerfile Path | `./Dockerfile` |
   | Instance Type | **Free** |
5. *Environment Variables* (botão **Add Environment Variable**; os nomes são os do `render.yaml`):

   | Variável | Valor |
   |---|---|
   | `WEB_USUARIOS` | `alberto@grupofedcorp.com.br,beneficiosocial@grupofedcorp.com.br` |
   | `WEB_SENHA` | a senha de acesso (a mesma do `.env` local) |
   | `WEB_SEGREDO_SESSAO` | qualquer texto longo aleatório (ou use **Generate** no painel) |
   | `FB_HOST` | host do túnel ngrok (ex.: `0.tcp.sa.ngrok.io`) ou IP público do roteador |
   | `FB_PORT` | porta do túnel (ex.: `14523`) |
   | `FB_DATABASE` | `E:\SISTEMA\BASE_CHEQUE\BASE\FATURA.GDB` (caminho no servidor Firebird) |
   | `FB_USER` / `FB_PASSWORD` | usuário e senha do Firebird |
   | `FB_CHARSET` | `ASCII` |
   | `FB_POOL_SIZE` | `5` |
   | `SFTP_HOST` | `sftp.portoseguro.com.br` |
   | `SFTP_FALLBACK_IP` | IP do SFTP da Porto (o do `.env`) |
   | `SFTP_PORT` | `2022` |
   | `SFTP_USER` / `SFTP_PASSWORD` | credenciais do SFTP |
   | `SFTP_DESTINO` | `/Porto/Remessa` |

   `PORT` não precisa: o Render injeta. Sem as `FB_*`/`SFTP_*` o app **não sobe**
   (`config.py` aborta avisando qual falta — é intencional).
6. *Advanced* > **Health Check Path**: `/api/saude`. Auto-Deploy: Yes.
7. **Create Web Service**. O build (Docker: `libfbclient2`, pip, testes sem banco)
   leva alguns minutos. No log, esperar `Uvicorn running on http://0.0.0.0:<porta>`.
8. Abrir `https://envioporto-web.onrender.com/` → tela de login.

Limitações do plano Free: o serviço **dorme após 15 min sem uso** e a primeira
chamada seguinte leva ~1 min para acordar; 512 MB de RAM (VIDA RJ e BOAT cabem,
mas não gere dois trabalhos pesados ao mesmo tempo); sem disco persistente (os
arquivos já eram efêmeros); 750 h/mês de uso.

## 5. O que muda em relação ao desktop

- Os arquivos gerados ficam em `/app/saida` (**efêmero**): baixe pela página do trabalho
  assim que terminar. A lista "Últimos trabalhos" some a cada deploy/reinício.
- Vida: a grade de inconsistências aparece antes de gerar, como no desktop; o robô
  noturno **não existe na web** (agendamento virá como cron do Render, se for o caso).
- Assistência: o envio SFTP só acontece com as duas caixas marcadas e a confirmação.
- Plano Starter (512 MB): VIDA RJ (19 mil linhas) e BOAT (41 mil) cabem; se aparecer
  "Out of memory" no log, subir para Standard.
- Latência: cada consulta atravessa Ohio ↔ Brasil pelo túnel. Vida RJ, que leva ~1 min
  na LAN, pode levar vários minutos.

## 6. Rodar a web localmente (sem Render)

```powershell
cd U:\--2021\04-EnvioPorto-web
pip install -r requirements.txt
# .env com FB_*, SFTP_* e WEB_USUARIOS / WEB_SENHA
uvicorn web.app:app --reload --port 8000
# http://127.0.0.1:8000/  (na rede interna: --host 0.0.0.0 e liberar a porta 8000)
```

Testes: `python -m unittest discover -s tests` (os de integração exigem
`PORTO_TESTE_INTEGRACAO=1`).

## 7. Diagnóstico

| Sintoma | Causa provável | Onde olhar |
|---|---|---|
| `gunicorn: command not found` | serviço criado como runtime Python | recriar como Web Service com Language = Docker (§4) |
| Login diz "Nenhum usuário configurado" | `WEB_USUARIOS`/`WEB_SENHA` vazios | Environment do serviço |
| Página de trabalho com `[ERRO] ... Unable to complete network request to host` | túnel fechado, porta errada | ngrok / `FB_HOST`, `FB_PORT` |
| Diagnóstico com `SQLCODE -923 connection rejected by remote interface` | cliente Firebird 3.x (pacote `libfbclient2` do Debian) contra o servidor 2.5.9 | a imagem instala o cliente **2.5.9 oficial** (tarball do GitHub) no lugar do pacote Debian; ver Dockerfile |
| Erro -802 string truncation | procedure do banco | `queries/alter_gera_rel_pla_sistema*.sql` (já aplicados em 03/11/2026) |
| Arquivo "não disponível" depois de pronto | serviço reiniciou (disco efêmero) | gerar de novo e baixar em seguida |
