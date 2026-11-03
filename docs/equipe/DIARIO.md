# DIARIO DA EQUIPE — SISTEMA DE ENVIO PORTO SEGURO

Registro compartilhado entre os agentes. Acrescentar entradas no fim; nunca apagar.

---

## 2026-11-03 — dev-backend — Revisão de código (somente leitura)

**Tarefa**: revisar `modulos/subgrupos_vida.py` (refatoração `_montar_dataframe`, robô noturno, coberturas provisórias fatura 99, `_salvar_excel`) e, de forma mais rápida, `main.py`, `db.py` e demais módulos.

**Decisões**: nenhum arquivo de código alterado; nada executado contra o banco. Rodei só `tests/test_agendador_subgrupos_vida.py` (mockado): 9/9 OK.

**Principais achados** (relatório completo entregue ao orquestrador):
1. `modulos/porto_assistencia.py:28` tem um token solto `uhuh` -> NameError na importação; como `main.py` importa todos os módulos, o sistema inteiro não abre.
2. `processar` (Vida) não fecha a conexão em caso de erro: conexão do pool vaza com transação aberta (pode manter marcas 99 não commitadas e locks em VIDA_*).
3. `_incluir_coberturas_provisorias`: commit intermediário (linha 348) torna as marcas 99 visíveis antes da limpeza; falha no `finally` mascara a exceção original.
4. Robô: fechar a janela Vida com agendamento pendente faz o `after` disparar sobre widgets destruídos -> robô nunca roda, sem aviso.
5. Preferência "enviar por SFTP" persiste em JSON e volta marcada -> risco de envio acidental a /Porto/Remessa.

**Pendências**: correções para dev-backend (itens 1-4) após aprovação do orquestrador; item 5 é decisão de produto (Alberto). DOCUMENTACAO.md §3 e cabeçalho desatualizados (analista-requisitos).

## 2026-11-03 - dba - validacao somente leitura do fluxo de cobertura provisoria (Vida)

- Tarefa: residuos FATURA=99, perfil do subgrupo 1317377, indices/planos dos UPDATEs de
  `_incluir_coberturas_provisorias`, sintaxe das queries, unicidade de nomes em SUBGRUPOSEGURADORA.
- Decisoes: nenhuma alteracao de codigo ou banco (apenas SELECT e prepare de statements).
- Achados principais: 0 residuos 99 nas 3 tabelas; 15 coberturas provisorias NULL do 1317377 (todas
  DT_INI_COBERT=01/10/2026, apolices 4803 e 6800), todas com 1 MOV NULL e FIN=0 (100 linhas);
  UPDATEs com EXISTS usam indice por FATURA (IDX1) e custam <2 s hoje; trigger VIDA_SEGURADOS_MOV_AU0
  apaga MOV/FIN irmaos quando um MOV com STATUS='C' e atualizado (12.426 MOV com FATURA NULL e
  STATUS='C' no banco) - risco a avaliar pelo dev-backend; 20 nomes de subgrupo unicos.
- Arquivos tocados: so este diario. Scripts em scratchpad da sessao (nao versionados).
- Pendencias: dev-backend decidir se o UPDATE de MOV deve excluir STATUS='C' (ou usar chave a chave).

## 2026-11-03 - orquestrador (Claude Code) - consolidacao da revisao

- Aplicado: remocao do token `uhuh` (porto_assistencia.py:28); cobertura provisoria em transacao
  unica com rollback em erro e `STATUS <> 'C'` no UPDATE de MOV; `processar` com finally/rollback;
  `_ao_fechar` na janela Vida; `pd.to_numeric` no destaque; pin python-dotenv relaxado;
  DOCUMENTACAO.md (§2, §4, §9) e CLAUDE.md atualizados.
- Verificado: todos os modulos importam; 10 testes unitarios OK; teste de integracao 1317377 OK (27 s).
- Pendente de decisao do Alberto: GAP-01..04, host key SFTP, preferencia "enviar" persistida,
  PLANO-WEB.md (Dental), rodar o app de clone local em vez do compartilhamento.

## 2026-11-03 - orquestrador (Claude Code) - modulo FUNERAL e criterio de vigencia

- Novo modulo GERAR ARQUIVO FUNERAL (modulos/funeral.py, modulos/gerador_funeral.py, queries/funeral.sql),
  botao no menu, testes unitarios e de integracao (gated). Conexao WIN1252 (query com acentos).
- Criterio "vigencia em curso contem a data" aplicado a portodental_1, sempreodonto_1, codigo1/3 e codigo2.
  Impacto 10/2026: Dental e BOAT sem mudanca; residencial_1 +6.862 e empresarial +2.140 linhas -> validar com o usuario.
- Procedures GERA_REL_PLA_SISTEMA (BAIRRO 50 + TEMP.BAIRRO 50) e _99 (COBERTURA/BAIRRO 50) corrigidas pelo usuario;
  varredura dos 20 subgrupos em 10/2026 sem erros.
- Manuais MANUAL-OPERACAO.md e MANUAL-INSTALACAO.md delegados ao analista-requisitos.

## 2026-11-03 - analista-requisitos - manuais de operacao e de instalacao

- Tarefa: escrever `docs/MANUAL-OPERACAO.md` (usuario final: cinco modulos, botoes/campos com os
  nomes exatos da tela, mensagens e acoes, grade de inconsistencias, fatura 99, robo noturno,
  envio SFTP, regra de vigencia de 03/11/2026, problemas comuns) e `docs/MANUAL-INSTALACAO.md`
  (requisitos, clone local, PowerShell passo a passo, .env com 13 variaveis sem valores,
  checklist de verificacao, primeira execucao, atualizacao, preparo para o robo, problemas).
- Decisoes: nenhuma regra de negocio decidida; fatos do ambiente conforme levantamento de
  03/11/2026 passado pelo orquestrador. Nada executado contra o banco; .env nao lido.
- Arquivos tocados: docs/MANUAL-OPERACAO.md (novo), docs/MANUAL-INSTALACAO.md (novo), este diario.
- Inconsistencias encontradas (para o orquestrador/dev-backend):
  1. `.gitignore` ignora porto_assistencia.json, porto_dental.json e sempre_odonto.json, mas NAO
     `funeral.json` (criado por modulos/funeral.py) - vai entrar no git no primeiro commit apos uso.
  2. DOCUMENTACAO.md §1: a linha da tabela "GERAR ARQUIVO FUNERAL" esta fora da tabela (apos o
     paragrafo do FedHub) e a tabela nao lista Dental/Sempre Odonto; §3 (estrutura de pastas) nao
     mostra porto_dental.py, dental_sempre_odonto.py, funeral.py, gerador_*.py, tests/ nem as
     queries novas; §2 diz que o sistema "hoje tem dois modulos".
  3. Vida, varios subgrupos marcados: o nome sugerido usa o codigo do ULTIMO subgrupo processado
     (id_sub_arquivo sobrescrito no loop); o valor "Varios" so aparece quando nenhum nome resolve.
     Documentei o comportamento real; confirmar se e o desejado.
  4. Vida: o robo exige pasta existente (isdir), os demais modulos criam a pasta (makedirs).
  5. Porto Assistencia: a caixa "Enviar..." volta marcada da ultima vez (ja apontado em 03/11).
- Pendencias: decidir itens 1 e 3 (Alberto); atualizar DOCUMENTACAO.md §1-§3 (analista-requisitos,
  quando autorizado); testes unitarios rodados sem banco (ver relatorio).

## 2026-11-03 - orquestrador (Claude Code) - branch web-render (versao web para o Render)

- main preservada e publicada (044e882) antes de qualquer mudanca; branch web-render criada no GitHub e
  como worktree local em U:\--2021\04-EnvioPorto-web.
- Novo: modulos/gerador_vida.py (nucleo de Vida sem tkinter; classe desktop delega; 8 SQLs identicos
  verificados por script), web/ (FastAPI: auth com usuarios fixos por env, fila de trabalhos em thread,
  templates Jinja2), Dockerfile, .dockerignore, render.yaml, docs/DEPLOY-RENDER.md, tests/test_web.py.
- Smoke contra o banco pelo TestClient: login, 20 subgrupos, inconsistencias, CIPA, Funeral (20.236),
  Dental/Sempre Odonto (consulta + geracao de 2 faturas), Assistencia Auto (limite 50) - tudo OK.
- Primeiro deploy falhou por runtime Python + "gunicorn gerador_arquivos"; correcao = Blueprint Docker.
- Pendente do usuario: abrir o tunel ngrok (ou roteador) ate 192.168.0.6:3050; preencher WEB_SENHA e FB_*/SFTP_*
  no painel do Render; importar o render.yaml.
