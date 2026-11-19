# -*- coding: utf-8 -*-
"""Núcleo de geração do arquivo PORTO ASSISTÊNCIA (sem interface).

Lê as queries em ../queries/*.sql, executa no Firebird com o parâmetro
:inivig (data de início de vigência) e grava o arquivo
relacaoenvioportoMMYYYY.csv. A tela fica em porto_assistencia.py.

Layout (modelo enviado pela Porto em 19/11/2026, substituindo o .xlsx de
três abas): UM arquivo CSV, separador ponto e vírgula, Windows-1252,
cabeçalho na primeira linha, nove colunas:

    status         sempre "A" (ativo)
    codigoPlano    1 Residencial / 2 Auto / 3 Empresarial
    inicioVigencia data informada na tela (DD/MM/AAAA)
    finalVigencia  mesma data um ano depois (vigência de 1 ano)
    tipoDocumento  CPF (até 11 dígitos) ou CNPJ (mais de 11)
    documento      só dígitos, completado com zeros à esquerda (11 ou 14)
    cpfCnpj        igual a documento
    nome           NOME da query
    nomeSocial     igual a nome

O nome do arquivo não pode ter espaços nem traços (exigência da Porto).
Das queries só NOME e CPF_CNPJ são usados; as demais colunas (endereço,
inquilino etc.) continuam vindo mas são ignoradas.
"""
import csv
import datetime
import os
import re

import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES_DIR = os.path.join(BASE_DIR, "queries")

CABECALHO = ["status", "codigoPlano", "inicioVigencia", "finalVigencia",
             "tipoDocumento", "documento", "cpfCnpj", "nome", "nomeSocial"]
STATUS_ATIVO = "A"
COLUNAS_QUERY = ["NOME", "CPF_CNPJ"]   # o que o gerador precisa de cada query

SEPARADOR = ";"
CODIFICACAO = "cp1252"              # Windows-1252: o Excel em português abre direto

# Um produto pode ter mais de uma query (query_files): os resultados são
# acumulados no mesmo código, na ordem dos arquivos. O campo "aba" é o nome
# que cada produto tinha na planilha .xlsx antiga (modelo manual, com os
# espaços originais) — fica só como rótulo na tela.
PRODUTOS = [
    {
        "codigo": 1,
        "nome": "Residencial",
        "aba": "Código 1 - Residencial",
        "query_files": ["codigo1_residencial_1.sql", "codigo1_residencial_2.sql"],
        "colunas": COLUNAS_QUERY,
    },
    {
        "codigo": 2,
        "nome": "Auto",
        "aba": "Código 2 - Auto ",
        "query_files": ["codigo2_auto.sql"],
        "colunas": COLUNAS_QUERY,
    },
    {
        "codigo": 3,
        "nome": "Empresarial",
        "aba": "Código 3 -  Empresarial",
        "query_files": ["codigo3_empresarial.sql"],
        "colunas": COLUNAS_QUERY,
    },
]

FETCH_BLOCO = 2000   # linhas por leitura no banco (equilíbrio memória x rede)


def _log_padrao(msg, transiente=False):
    print(msg)


def celula(ws, valor):
    """Ajudante das planilhas .xlsx dos outros geradores (Dental usa): célula
    de data exibida como DD/MM/YYYY; demais valores passam direto. Ficou aqui
    por histórico — o próprio Porto Assistência não gera mais .xlsx."""
    from openpyxl.cell import WriteOnlyCell
    if isinstance(valor, (datetime.datetime, datetime.date)):
        c = WriteOnlyCell(ws, value=valor)
        c.number_format = "DD/MM/YYYY"
        return c
    return valor


def nome_arquivo(inivig: datetime.date) -> str:
    """Sem espaços nem traços, como a Porto exige."""
    return f"relacaoenvioporto{inivig:%m%Y}.csv"


def fim_vigencia(inivig: datetime.date) -> datetime.date:
    """Um ano depois, mesmo dia (29/02 vira 28/02)."""
    try:
        return inivig.replace(year=inivig.year + 1)
    except ValueError:
        return inivig.replace(year=inivig.year + 1, day=28)


def documento(valor) -> tuple[str, str]:
    """(tipoDocumento, documento): só dígitos, zeros à esquerda; CPF com 11,
    CNPJ com 14. Vazio/nulo/zeros -> ("", "")."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    if digitos.strip("0") == "":
        return "", ""
    if len(digitos) > 11:
        return "CNPJ", digitos.zfill(14)
    return "CPF", digitos.zfill(11)


def montar_linha(codigo: int, nome, cpf_cnpj, inivig: datetime.date) -> list:
    tipo, doc = documento(cpf_cnpj)
    nome = (nome or "").strip() if isinstance(nome, str) else ("" if nome is None else str(nome))
    return [STATUS_ATIVO, str(codigo), inivig.strftime("%d/%m/%Y"),
            fim_vigencia(inivig).strftime("%d/%m/%Y"), tipo, doc, doc, nome, nome]


def carregar_query(nome_arquivo: str) -> str:
    caminho = os.path.join(QUERIES_DIR, nome_arquivo)
    with open(caminho, "r", encoding="utf-8") as f:
        sql = f.read()
    if "TODO" in sql:
        raise RuntimeError(
            f"A query em queries/{nome_arquivo} ainda não foi preenchida "
            f"(contém o marcador TODO).")
    return sql


def _sem_comentarios(sql: str) -> str:
    """Remove comentários /* */ e -- : eles também citam :inivig e inflariam a
    contagem de parâmetros (o fdb tolerava; o firebirdsql dá SQLDA error -804)."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return re.sub(r"--[^\n]*", "", sql)


def _preparar_parametros(sql: str, inivig: datetime.date) -> tuple[str, list]:
    """Troca cada :inivig por ? (estilo DB-API) e monta a lista de valores."""
    sql = _sem_comentarios(sql)
    ocorrencias = len(re.findall(r":inivig\b", sql, flags=re.IGNORECASE))
    sql_qmark = re.sub(r":inivig\b", "?", sql, flags=re.IGNORECASE)
    return sql_qmark, [inivig] * ocorrencias


def gerar_planilha(destino_pasta: str, inivig: datetime.date, selecao: dict,
                   log=_log_padrao) -> tuple[str, dict]:
    """Gera o .csv e retorna (caminho_do_arquivo, {codigo: linhas_gravadas}).

    (O nome da função é histórico — gerava .xlsx até 19/11/2026.)

    inivig: data de início de vigência — alimenta o :inivig das queries,
    as colunas inicioVigencia/finalVigencia e a competência do nome do
    arquivo (mês/ano da data).
    selecao: {codigo_produto: None | int} — produtos presentes no dict são
    gerados; None = base toda, int = limite de linhas ("as N primeiras
    linhas da query"). Com mais de uma query no produto, o limite vale para
    a soma: a segunda query só roda se ainda houver saldo.
    """
    if not selecao:
        raise ValueError("Nenhum produto selecionado.")
    os.makedirs(destino_pasta, exist_ok=True)
    caminho = os.path.join(destino_pasta, nome_arquivo(inivig))

    resultado = {}
    con = db.conectar(charset="WIN1252")
    try:
        # errors="replace": um caractere fora do Windows-1252 vira '?' em vez
        # de derrubar a geração inteira.
        with open(caminho, "w", newline="", encoding=CODIFICACAO, errors="replace") as f:
            escritor = csv.writer(f, delimiter=SEPARADOR, quoting=csv.QUOTE_MINIMAL)
            escritor.writerow(CABECALHO)
            for prod in PRODUTOS:
                if prod["codigo"] not in selecao:
                    continue
                limite = selecao[prod["codigo"]]
                codigo = prod["codigo"]
                gravadas = 0

                for query_file in prod["query_files"]:
                    if limite is not None and gravadas >= limite:
                        log(f"  (limite atingido — {query_file} não executada)")
                        break
                    sql = carregar_query(query_file)
                    sql, params = _preparar_parametros(sql, inivig)
                    log(f"Código {codigo} - {prod['nome']}: executando {query_file}...")

                    cur = con.cursor()
                    cur.execute(sql, params)
                    nomes_query = [d[0].strip().upper() for d in cur.description]
                    faltando = [c for c in prod["colunas"] if c not in nomes_query]
                    if faltando:
                        raise RuntimeError(
                            f"Código {codigo} - {prod['nome']}: a query "
                            f"{query_file} não retorna as colunas {faltando}. "
                            f"Colunas retornadas: {nomes_query}")
                    i_nome = nomes_query.index("NOME")
                    i_doc = nomes_query.index("CPF_CNPJ")

                    while True:
                        if limite is not None:
                            restante = limite - gravadas
                            if restante <= 0:
                                break
                            bloco = cur.fetchmany(min(FETCH_BLOCO, restante))
                        else:
                            bloco = cur.fetchmany(FETCH_BLOCO)
                        if not bloco:
                            break
                        escritor.writerows(
                            montar_linha(codigo, linha[i_nome], linha[i_doc], inivig)
                            for linha in bloco)
                        gravadas += len(bloco)
                        log(f"  ... {gravadas} linhas", transiente=True)
                    cur.close()

                resultado[codigo] = gravadas
                extra = f" (limite {limite})" if limite is not None else " (base toda)"
                log(f"Código {codigo} - {prod['nome']}: {gravadas} linhas geradas{extra}")
    finally:
        con.close()

    total = sum(resultado.values())
    log(f"Arquivo gerado: {caminho} ({total} linhas no total)")
    return caminho, resultado
