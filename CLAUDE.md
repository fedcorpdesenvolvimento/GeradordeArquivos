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
  e identificadores em português.
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
- **Módulo planejado** (botão placeholder no menu): GERAR DENTAL SEMPRE
  ODONTO — código entra depois, no mesmo padrão.

## Como rodar / testar

```
python main.py
```

Testes de geração sem dados reais: apontar as queries para `RDB$RELATIONS`
com CAST + aliases (ver histórico) ou usar limite pequeno (5 linhas) com as
queries reais — leitura é inofensiva; o que não pode é enviar ao SFTP.
