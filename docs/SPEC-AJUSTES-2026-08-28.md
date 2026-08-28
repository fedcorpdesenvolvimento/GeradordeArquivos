# Spec — Ajustes de 28/08/2026 (Sempre Odonto, códigos de subgrupo, datas BR, cor por tipo)

> **Rastreabilidade** — RF: RF-AJU-001..004
> **Status:** aprovado (implementado e validado) · **Dono:** Alberto (dono do produto) · **Atualizado:** 2026-08-28

Spec no padrão SDD do Grupo FedCorp (mesma adaptação local da
`SPEC-PORTO-DENTAL.md`). Cobre os três ajustes pedidos pelo dono em
28/08/2026 e documenta comportamento já implementado e testado.

## Contexto

Quatro pedidos do dono no mesmo dia: (1) exibir o código do subgrupo nos
checkboxes do SUBGRUPOS DE VIDA; (2) implementar o último módulo do menu,
GERAR DENTAL SEMPRE ODONTO, idêntico ao GERA PORTO DENTAL; (3) datas de
nascimento nas planilhas em formato brasileiro (estavam saindo aaaa-mm-dd);
(4) botões do Sempre Odonto em cor pastel para diferenciar o tipo de
produto.

## RF-AJU-001: Código do subgrupo nos checkboxes (SUBGRUPOS DE VIDA)

**Como** operador, **quero** ver o código de cada subgrupo na lista de
seleção, **para** identificar o subgrupo sem sair da tela — apenas
informação visual; o critério de geração não muda [D] (dono, 28/08/2026).

- **QUANDO** a tela carrega os subgrupos, **ENTÃO** a listagem **DEVE**
  trazer `NOME_SUBGRP, SUBGRUPO` e o checkbox exibir
  `NOME DO SUBGRUPO [código]` [E] (`modulos/subgrupos_vida.py:79-81`).
- **QUANDO** a geração roda, **ENTÃO** o sufixo ` [código]` **DEVE** ser
  removido do texto antes da busca `WHERE NOME_SUBGRP = ?` — o critério
  continua sendo o nome, como sempre foi [E]
  (`modulos/subgrupos_vida.py:184-187`; regex remove apenas colchetes no
  fim do texto, preservando nomes com hífens etc.).
- Validação (2026-08-28, banco de produção, leitura): os 18 subgrupos
  montados como `NOME [código]` resolveram para o código correto após a
  limpeza — zero falhas.

## RF-AJU-002: Módulo GERAR DENTAL SEMPRE ODONTO

**Como** operador, **quero** o último módulo do menu idêntico ao GERA
PORTO DENTAL, **para** gerar a planilha do produto Sempre Odonto no mesmo
fluxo de duas etapas [D] (dono, 28/08/2026: "identico ao terceiro";
muda só `tipo_dental` e o nome).

Especificação completa do fluxo: **`SPEC-PORTO-DENTAL.md`** (RF-DEN-001..
005 e RNF-DEN-001..003 valem para os dois produtos) — os detalhes desta
extensão estão registrados lá, na seção "Extensão (28/08/2026)". Resumo
do que muda:

| Parâmetro | PORTO DENTAL | SEMPRE ODONTO |
|---|---|---|
| Filtro da query 1 | `AP.tipo_dental = 'P'` | `AP.tipo_dental = 'S'` |
| Queries | `portodental_*.sql` | `sempreodonto_*.sql` |
| Arquivo gerado | `portodental-MMYYYY.xlsx` | `sempreodonto-MMYYYY.xlsx` |
| Aba / título | PORTO DENTAL | SEMPRE ODONTO |
| Preferências | `porto_dental.json` | `sempre_odonto.json` |

- Implementação por herança: `JanelaDentalSempreOdonto(JanelaPortoDental)`
  troca só atributos de classe [E] (`modulos/dental_sempre_odonto.py:16-22`);
  o motor `gerador_dental.py` foi parametrizado por
  `query_file`/`prefixo`/`aba` sem mudar o comportamento padrão [E]
  (regressão do Porto Dental em 2026-08-28: 20 faturas / 7.080 vidas,
  idêntico ao teste de 27/08).
- **QUANDO** o menu abre, **ENTÃO** GERAR DENTAL SEMPRE ODONTO **DEVE**
  abrir o módulo (deixou de ser placeholder; o menu não tem mais módulos
  em desenvolvimento) [E] (`main.py`).

## RF-AJU-003: Datas em formato brasileiro nas planilhas

**Como** operador, **quero** as datas de nascimento exibidas como
`dd/mm/aaaa`, **para** leitura no padrão brasileiro [D] (dono, 28/08/2026
— estavam saindo `aaaa-mm-dd`, formato ISO padrão do openpyxl).

- **QUANDO** qualquer gerador grava um valor de data/datetime, **ENTÃO** a
  célula **DEVE** continuar sendo data no Excel, com `number_format`
  `DD/MM/YYYY` [E] (`modulos/gerador_porto.py:63-75`, helper `celula()`;
  aplicado no Porto Assistência em `gerador_porto.py:156` e nos dois
  módulos Dental em `gerador_dental.py:122`).
- Vale para **todas** as planilhas do sistema: Porto Assistência
  (`DATANASCIMENTO`) e Dental/Sempre Odonto (`NASCIMENTO`). Subgrupos de
  Vida usa pandas/outro fluxo e não apresentou o problema.
- Validação (2026-08-28): planilha Dental regenerada — células de
  `NASCIMENTO` com `number_format='DD/MM/YYYY'` e valor datetime íntegro.

## RF-AJU-004: Cor diferenciada para o Sempre Odonto

**Como** operador, **quero** os botões do Sempre Odonto numa cor diferente
do verde dos produtos Porto, **para** distinguir o tipo de produto à
primeira vista [D] (dono, 28/08/2026: "uma cor pastel ... apenas para
diferenciar o tipo").

- **QUANDO** o menu abre, **ENTÃO** o botão GERAR DENTAL SEMPRE ODONTO
  **DEVE** aparecer em azul pastel `#7A9CC6` (hover `#5F82AC`), enquanto
  os produtos Porto continuam verdes [E] (`main.py`, botão do menu).
- **QUANDO** a janela do Sempre Odonto abre, **ENTÃO** os botões
  "1) Consultar Vidas" e "2) Gerar Planilha Final" **DEVEM** usar a mesma
  cor pastel [E]: a cor virou parâmetro de produto — atributos de classe
  `COR_BOTAO`/`COR_BOTAO_HOVER` em `modulos/porto_dental.py` (padrão
  `green`/`darkgreen`), sobrepostos na subclasse
  `modulos/dental_sempre_odonto.py` (`#7A9CC6`/`#5F82AC`).
- A regra geral do sistema não muda: botão de ação principal **verde** é o
  padrão (CLAUDE.md, Estilo); o pastel é a exceção que marca o produto
  não-Porto.

## Divergência vs. produção

Nenhuma — os três ajustes entraram em 28/08/2026 já conforme esta spec.

## Pendências

- Validação visual pelo dono (abrir as planilhas no Excel e conferir as
  datas e, no caso do Porto Assistência, se o modelo manual da Porto
  também exibia `dd/mm/aaaa` — hipótese assumida: sim, Excel brasileiro).
- Na migração web (spec `envio-porto` do FedHub-Backend), levar os três
  comportamentos junto.
