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

Estes módulos farão parte de um sistema maior no futuro, quando a conexão
com o banco passará por um **hub** central. Por enquanto a conexão fica em
`db.py` + `config.py` — os módulos já chamam `db.conectar()`, então trocar
para o hub não exigirá mudanças neles.

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
│  config.py                ← DB_CONFIG (Firebird) e SFTP_CONFIG (Porto)
│  db.py                    ← db.conectar() — futuro ponto de troca p/ hub
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

### Fluxo "Ver Inconsistências (Tela)" (`abrir_relatorio_tela`)

Lista em uma grade (Treeview) as faturas de Vida ativas do mês **sem
subgrupo preenchido** (`apo.subporto` nulo ou vazio), ignorando apólices
`C%` e `VR0001`. Serve para conferir cadastro antes de gerar o relatório.

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
  dia, atualizar `host_fallback_ip` no `config.py` (resolver com
  `nslookup sftp.portoseguro.com.br 8.8.8.8`).
- O upload sobe como `arquivo.part`, confere o tamanho e só então renomeia
  para o nome final — a Porto nunca vê arquivo incompleto. Qualquer falha
  vira exceção mostrada no log da tela.

### Estado atual

Queries reais instaladas e testadas contra o banco em 21/08/2026 (amostra
de 5 linhas por produto conferida contra a planilha manual de referência
`U:\PORTO SEGURO VIDA\relacao-envio-porto-042026.xlsx` — layout idêntico).

## 6. Banco de dados

- Firebird **2.5** em `192.168.0.6`, arquivo `E:\SISTEMA\BASE_CHEQUE\BASE\FATURA.GDB`
  (mesmo banco dos sistemas Delphi legados).
- Credenciais em `config.py` (`DB_CONFIG`). **Não commitar este arquivo em
  repositório público**; no sistema maior as credenciais sairão do código
  (hub de conexão).
- Charset: módulo Vida usa `ASCII` (comportamento herdado e validado);
  Porto Assistência usa `WIN1252`. `db.conectar(charset=...)` permite a
  escolha por chamada.

## 7. Módulos planejados

Já têm botão no menu (desabilitados com aviso "em desenvolvimento"),
aguardando o código, que seguirá o mesmo padrão dos módulos existentes:

- **GERA PORTO DENTAL**
- **GERAR DENTAL SEMPRE ODONTO**

## 8. Como adicionar um novo módulo

1. Criar `modulos/nome_do_modulo.py` com uma classe `ctk.CTkToplevel`
   (usar `porto_assistencia.py` como referência de estrutura).
2. Usar `db.conectar()` para acessar o banco — nunca `fdb.connect` direto.
3. Registrar um botão no `main.py` chamando a nova janela.
4. Documentar o módulo neste arquivo (objetivo, fluxo, tabelas usadas).

## 9. Histórico

- **21/08/2026** — Primeira versão do sistema unificado. SUBGRUPOS DE VIDA
  migrado de `02-gerador_planilhas_firebird`; PORTO ASSISTÊNCIA criado a
  partir do protótipo `Base_Cheque\Envio de Layout\sftp-porto` (onde a
  conexão SFTP e o layout da planilha foram validados com a Porto).
