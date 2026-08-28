# -*- coding: utf-8 -*-
"""Núcleo de geração da planilha PORTO ASSISTÊNCIA (sem interface).

Lê as queries em ../queries/*.sql, executa no Firebird com o parâmetro
:inivig (data de início de vigência) e grava o arquivo
relacao-envio-porto-MMYYYY.xlsx com as três abas no layout exato que a
Porto Seguro recebe hoje (gerado manualmente). A tela fica em
porto_assistencia.py.
"""
import datetime
import os
import re

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES_DIR = os.path.join(BASE_DIR, "queries")

# Nomes de aba copiados byte a byte do modelo manual — a aba 2 tem espaço no
# fim e a aba 3 tem espaço duplo; a Porto pode depender disso, não "corrigir".
# Um produto pode ter mais de uma query (query_files): os resultados são
# acumulados na mesma aba, na ordem dos arquivos.
PRODUTOS = [
    {
        "codigo": 1,
        "nome": "Residencial",
        "aba": "Código 1 - Residencial",
        "query_files": ["codigo1_residencial_1.sql", "codigo1_residencial_2.sql"],
        "colunas": ["ENDERECO", "NUMERO", "COMPLEMENTO", "CEP", "BAIRRO",
                     "CIDADE", "SIGLAESTADO", "NOME", "CPF_CNPJ",
                     "DATANASCIMENTO", "NOMEINQUILINO", "CPFCNPJINQUILINO"],
    },
    {
        "codigo": 2,
        "nome": "Auto",
        "aba": "Código 2 - Auto ",
        "query_files": ["codigo2_auto.sql"],
        "colunas": ["ENDERECO", "NUMERO", "COMPLEMENTO", "CEP", "BAIRRO",
                     "CIDADE", "SIGLAESTADO", "NOME", "CPF_CNPJ",
                     "DATANASCIMENTO", "NOMEINQUILINO", "CPFCNPJINQUILINO"],
    },
    {
        "codigo": 3,
        "nome": "Empresarial",
        "aba": "Código 3 -  Empresarial",
        "query_files": ["codigo3_empresarial.sql"],
        "colunas": ["ENDERECO", "NUMERO", "COMPLEMENTO", "CEP", "BAIRRO",
                     "CIDADE", "SIGLAESTADO", "NOME", "CPF_CNPJ",
                     "DATANASCIMENTO", "NOMEINQUILINO", "CPFCNPJINQUILINO"],
    },
]

FETCH_BLOCO = 2000   # linhas por leitura no banco (equilíbrio memória x rede)


def _log_padrao(msg, transiente=False):
    print(msg)


def celula(ws, valor):
    """Valor pronto para ws.append: datas saem no formato brasileiro.

    O openpyxl grava datetime com formato ISO (aaaa-mm-dd) por padrão;
    aqui a célula continua sendo data, mas exibida como DD/MM/YYYY
    (pedido do usuário, 28/08/2026). Demais valores passam direto.
    """
    if isinstance(valor, (datetime.datetime, datetime.date)):
        c = WriteOnlyCell(ws, value=valor)
        c.number_format = "DD/MM/YYYY"
        return c
    return valor


def carregar_query(nome_arquivo: str) -> str:
    caminho = os.path.join(QUERIES_DIR, nome_arquivo)
    with open(caminho, "r", encoding="utf-8") as f:
        sql = f.read()
    if "TODO" in sql:
        raise RuntimeError(
            f"A query em queries/{nome_arquivo} ainda não foi preenchida "
            f"(contém o marcador TODO).")
    return sql


def _preparar_parametros(sql: str, inivig: datetime.date) -> tuple[str, list]:
    """Troca cada :inivig por ? (estilo do fdb) e monta a lista de valores."""
    ocorrencias = len(re.findall(r":inivig\b", sql, flags=re.IGNORECASE))
    sql_qmark = re.sub(r":inivig\b", "?", sql, flags=re.IGNORECASE)
    return sql_qmark, [inivig] * ocorrencias


def gerar_planilha(destino_pasta: str, inivig: datetime.date, selecao: dict,
                   log=_log_padrao) -> tuple[str, dict]:
    """Gera o .xlsx e retorna (caminho_do_arquivo, {codigo: linhas_gravadas}).

    inivig: data de início de vigência — alimenta o :inivig das queries e
    define a competência do nome do arquivo (mês/ano da data).
    selecao: {codigo_produto: None | int} — produtos presentes no dict são
    gerados; None = base toda, int = limite de linhas ("as N primeiras
    linhas da query"). Com mais de uma query no produto, o limite vale para
    a soma: a segunda query só roda se ainda houver saldo.
    """
    if not selecao:
        raise ValueError("Nenhum produto selecionado.")
    os.makedirs(destino_pasta, exist_ok=True)
    competencia = inivig.strftime("%m%Y")
    caminho = os.path.join(destino_pasta,
                           f"relacao-envio-porto-{competencia}.xlsx")

    wb = Workbook(write_only=True)
    resultado = {}
    con = db.conectar(charset="WIN1252")
    try:
        for prod in PRODUTOS:
            if prod["codigo"] not in selecao:
                continue
            limite = selecao[prod["codigo"]]
            ws = wb.create_sheet(title=prod["aba"])
            ws.append(prod["colunas"])
            gravadas = 0

            for query_file in prod["query_files"]:
                if limite is not None and gravadas >= limite:
                    log(f"  (limite atingido — {query_file} não executada)")
                    break
                sql = carregar_query(query_file)
                sql, params = _preparar_parametros(sql, inivig)
                log(f"Código {prod['codigo']} - {prod['nome']}: "
                    f"executando {query_file}...")

                cur = con.cursor()
                cur.execute(sql, params)
                nomes_query = [d[0].strip().upper() for d in cur.description]
                faltando = [c for c in prod["colunas"] if c not in nomes_query]
                if faltando:
                    raise RuntimeError(
                        f"Código {prod['codigo']} - {prod['nome']}: a query "
                        f"{query_file} não retorna as colunas {faltando}. "
                        f"Colunas retornadas: {nomes_query}")
                indices = [nomes_query.index(c) for c in prod["colunas"]]

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
                    for linha in bloco:
                        ws.append([celula(ws, linha[i]) for i in indices])
                    gravadas += len(bloco)
                    log(f"  ... {gravadas} linhas", transiente=True)
                cur.close()

            resultado[prod["codigo"]] = gravadas
            extra = f" (limite {limite})" if limite is not None else " (base toda)"
            log(f"Código {prod['codigo']} - {prod['nome']}: "
                f"{gravadas} linhas geradas{extra}")
    finally:
        con.close()

    wb.save(caminho)
    total = sum(resultado.values())
    log(f"Arquivo gerado: {caminho} ({total} linhas no total)")
    return caminho, resultado
