# PLANO — ENVIO PORTO NA WEB

Roteiro da migração do sistema desktop (customtkinter) para uma página web
servida pelo FedHub-Backend (FastAPI). Escrito em 27/08/2026; atualizar o
status a cada etapa concluída.

**Decisões já tomadas** (ver DOCUMENTACAO.md §1 e CLAUDE.md):
- Destino: módulo novo `src/modules/envio_porto` dentro do repositório
  `Fedcorp-Desenvolvimentos/FedHub-Backend`.
- Escopo: todos os módulos — Porto Assistência, Subgrupos Vida e os
  placeholders Dental (como rotas "em desenvolvimento").
- Interface: página HTML simples servida pelo próprio backend (sem depender
  do frontend principal).
- O desktop continua em uso até a versão web ser validada.

---

## Etapa 0 — Pré-requisitos de infraestrutura (decisão do Alberto)

O servidor que rodar o backend precisa alcançar duas redes:

1. **Firebird**: `192.168.0.6:3050` (rede interna do escritório).
2. **SFTP da Porto**: `sftp.portoseguro.com.br:2022` (internet; o DNS
   interno não resolve — o código já tem fallback por IP via `.env`).

**RESPONDIDO em 27/08/2026** (fonte: CLAUDE.md do FedHub-Backend): o FedHub
roda **local, em Docker**, na rede do ERP — é o único componente com acesso
ao Firebird — e é exposto à internet via **ngrok premium com domínio fixo**.
O módulo Envio Porto herda essa infraestrutura: acesso ao banco pela rede
local e saída para o SFTP da Porto (conexão de saída, não passa pelo ngrok).

Atenção: **`fedhub.com` NÃO é o FedHub da Fedcorp** — é um domínio
estacionado de terceiros (registrado em 2000, nameservers parkingcrew.net;
verificado via RDAP em 27/08/2026). O endereço público real é o domínio
fixo do ngrok.

- [ ] Anotar aqui o domínio fixo do ngrok quando formos publicar a página
      (não está no repositório, por segurança).

## Etapa 1 — Criar o módulo `envio_porto` no FedHub-Backend

**Antes de codar**: o FedHub-Backend segue spec-driven design obrigatório
(CLAUDE.md de lá) — módulo novo com contrato externo (SFTP) exige
`specs/<feature>/requirements.md` aprovado pelo dono antes do código.
O primeiro passo da etapa é escrever essa spec a partir deste plano e da
DOCUMENTACAO.md daqui.

Estrutura no padrão dos módulos existentes:

```
src/modules/envio_porto/
├─ controllers/   ← rotas FastAPI
├─ services/      ← geração da planilha, envio SFTP, jobs
├─ queries/       ← os .sql do Porto Assistência (copiados daqui)
├─ schemas/       ← modelos Pydantic (request/response)
└─ static/        ← página HTML da Etapa 3
```

Portes (a lógica já está separada da tela, o que facilita):
- `gerador_porto.py` → `services/gerador_assistencia.py`. Trocar
  `db.conectar(charset="WIN1252")` por `get_connection_firebird()` (o pool
  do FedHub já é WIN1252). Nomes de abas e layout de 12 colunas **intactos**.
- `queries/*.sql` → copiados sem alteração (parâmetro `:inivig` mantido).
- `envio_sftp.py` → `services/envio_sftp.py` (paramiko entra no
  requirements do FedHub). Mantém `.part` + verificação de tamanho + rename
  e o fallback de IP.
- `subgrupos_vida.py` → separar a lógica da tela (hoje estão juntas) em
  `services/subgrupos_vida.py`. **Atenção**: usa charset ASCII e o pool do
  FedHub é fixo em WIN1252 → adaptar `connection_firebird.py` para aceitar
  charset por chamada com um pool por charset (modelo já pronto e testado no
  `db.py` daqui — é levar o mesmo código).
- Lógica migrada **intacta** (regra do projeto): nada de "melhorar" queries
  ou fluxo na passagem.

## Etapa 2 — Endpoints

A geração pode demorar (centenas de milhares de linhas), então ela roda como
**job em background** e a página consulta o andamento — mesmo papel da
thread + fila do desktop:

| Método | Rota | Função |
|---|---|---|
| POST | `/api/envio-porto/assistencia/gerar` | inicia a geração (body: `inivig`, produtos com base toda/limite) → retorna `job_id` |
| GET | `/api/envio-porto/jobs/{job_id}` | status + log acumulado (a página faz polling, como a fila do Tk fazia) |
| GET | `/api/envio-porto/jobs/{job_id}/download` | baixa o .xlsx gerado |
| POST | `/api/envio-porto/jobs/{job_id}/enviar-sftp` | envia à Porto — **sempre ação separada e explícita**, nunca automática |
| POST | `/api/envio-porto/vida/gerar` | Subgrupos Vida (mesmo padrão de job) |
| GET | `/api/envio-porto/dental/*` | placeholders → HTTP 501 "em desenvolvimento" |

Regras que se mantêm da versão desktop:
- Data pré-sugerida = dia 01 do mês anterior (a página calcula, o usuário edita).
- Nunca enviar arquivo de teste ao `/Porto/Remessa` — o envio exige
  confirmação na página (a Porto processa tudo que cai lá).
- Autenticação: a global do FedHub (`X-Application-Key`) já cobre as rotas.

## Etapa 3 — Página web

- HTML + JS puro (sem framework), servido pelo FastAPI em
  `/envio-porto` (StaticFiles ou Jinja2 — decidir na hora, o mais simples).
- Reproduz a tela do desktop: data de vigência, produtos com "base toda ×
  quantidade", botão verde **Gerar Planilha**, log em tela (polling do job),
  botão de download e botão separado **Enviar para a Porto** com confirmação.
- Preferências (última pasta não existe mais; produtos/limites) podem ficar
  em `localStorage` do navegador — substitui o `porto_assistencia.json`.

## Etapa 4 — Rodar e validar localmente

1. `uvicorn` local (porta 8090) na máquina do Alberto, `.env` apontando para
   o Firebird de produção (leitura é inofensiva).
2. Testar geração com **Quantidade: 5** por produto e comparar com a
   planilha do desktop: nomes das abas byte a byte, cabeçalhos, 12 colunas.
3. Gerar a base toda e conferir totais de linhas contra o desktop (mesma
   data de vigência ⇒ mesmos totais).
4. Testar o envio SFTP **somente com confirmação do Alberto** e, de
   preferência, na competência real (não há pasta de teste na Porto).
5. Rodar uma competência inteira em paralelo (desktop + web) antes de
   confiar só na web.

## Etapa 5 — Deploy no servidor

1. Resolver a Etapa 0 (acesso ao Firebird a partir do servidor).
2. O FedHub-Backend já tem `Dockerfile`/`docker-compose.yml` — o módulo novo
   entra no mesmo deploy, sem infraestrutura própria.
3. `.env` do servidor: variáveis `FB_*` (mesmos nomes já usados aqui) +
   `SFTP_*`. Nunca copiar o `.env` para repositório.
4. Se exposto fora da rede: HTTPS via reverse proxy e a chave
   `X-Application-Key` obrigatória (modo bloqueio, não sombra).
5. Validada a versão web por 1–2 competências, aposentar o desktop
   (este repositório vira histórico; documentar o encerramento).

---

## Status

- [x] Etapa 0 — infraestrutura definida (FedHub local em Docker + ngrok;
      falta só anotar o domínio fixo na hora de publicar)
- [ ] Etapa 1 — módulo criado no FedHub-Backend
  - [x] Spec `specs/envio-porto/requirements.md` escrita e enviada na branch
        `envio-porto` do FedHub-Backend (27/08/2026) — status "em revisão";
        aguarda aprovação do dono e respostas das PA-021 (auth da página)
        e PA-022 (retenção de arquivos)
- [ ] Etapa 2 — endpoints funcionando
- [ ] Etapa 3 — página web
- [ ] Etapa 4 — validação local (planilha idêntica à do desktop)
- [ ] Etapa 5 — deploy definitivo
