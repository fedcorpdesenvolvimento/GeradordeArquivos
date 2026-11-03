# -*- coding: utf-8 -*-
"""Gerador do ARQUIVO FUNERAL — lógica sem interface.

Fluxo (uma etapa só, decisão do usuário 03/11/2026):
1. roda queries/funeral.sql com :inivig (segurados de Vida com cobertura
   FUNERAL/CERIMONIAL nas faturas ativas da vigência);
2. remove duplicidade de CPF (mantém a primeira ocorrência; CPF vazio não
   é deduplicado, pois não dá para saber se é a mesma pessoa);
3. grava funeral-MMYYYY.xlsx (aba FUNERAL) com as colunas
   ADMINISTRADORA, APOLICE, NOME, CPF, NASCIMENTO.

Conexão sempre via db.conectar() (regra do projeto), charset WIN1252.
"""
import datetime
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Font

import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES_DIR = os.path.join(BASE_DIR, "queries")
COLUNAS = ["ADMINISTRADORA", "APOLICE", "NOME", "CPF", "NASCIMENTO"]


def _log_padrao(msg, transiente=False):
    print(msg)


def _carregar_sql(query_file: str) -> str:
    caminho = os.path.join(QUERIES_DIR, query_file)
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def _preparar_parametros(sql: str, inivig: datetime.date):
    """Troca cada :inivig por ? e monta a lista de valores, ignorando os
    comentários da query (que também citam :inivig) — ver gerador_porto."""
    from modulos.gerador_porto import _sem_comentarios
    sql = _sem_comentarios(sql)
    ocorrencias = len(re.findall(r":inivig\b", sql, flags=re.IGNORECASE))
    return re.sub(r":inivig\b", "?", sql, flags=re.IGNORECASE), [inivig] * ocorrencias


def normalizar_cpf(valor) -> str:
    """Só dígitos, completados com zeros à esquerda como na planilha de Vida
    (11 para CPF, 14 para CNPJ); '' quando vazio/None/'0' (não deduplicável)."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    if digitos.strip("0") == "":
        return ""
    return digitos.zfill(14) if len(digitos) > 11 else digitos.zfill(11)


def remover_duplicidade_cpf(linhas):
    """linhas: iterável de tuplas (ADMINISTRADORA, APOLICE, NOME, CPF, NASCIMENTO).
    Devolve (lista_sem_duplicidade, qtd_removidas). Mantém a primeira
    ocorrência de cada CPF; linhas sem CPF são todas mantidas."""
    vistos = set()
    saida = []
    removidas = 0
    for linha in linhas:
        cpf = normalizar_cpf(linha[3])
        if cpf:
            if cpf in vistos:
                removidas += 1
                continue
            vistos.add(cpf)
        saida.append(linha)
    return saida, removidas


def consultar(inivig: datetime.date, log=_log_padrao, query_file="funeral.sql"):
    """Executa a query e devolve as linhas já sem duplicidade de CPF."""
    sql, params = _preparar_parametros(_carregar_sql(query_file), inivig)
    log(f"Consultando segurados com cobertura FUNERAL/CERIMONIAL — vigência {inivig:%d/%m/%Y}...")
    # WIN1252 como o Porto Assistência: a query tem acentos e os nomes dos
    # segurados também; a conexão ASCII (padrão da Vida) não os aceita.
    conn = db.conectar("WIN1252")
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        brutas = [tuple(l) for l in cur.fetchall()]
    finally:
        conn.close()
    log(f"Linhas retornadas pelo banco: {len(brutas)}")
    linhas, removidas = remover_duplicidade_cpf(brutas)
    log(f"Duplicidades de CPF removidas: {removidas}")
    log(f"Segurados a enviar: {len(linhas)}")
    return linhas


def gravar_planilha(destino_pasta: str, inivig: datetime.date, linhas,
                    prefixo="funeral", aba="FUNERAL") -> str:
    os.makedirs(destino_pasta, exist_ok=True)
    caminho = os.path.join(destino_pasta, f"{prefixo}-{inivig:%m%Y}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = aba
    ws.append(COLUNAS)
    for cel in ws[1]:
        cel.font = Font(bold=True)
    for adm, apolice, nome, cpf, nasc in linhas:
        ws.append([(adm or "").strip(), (apolice or "").strip(), (nome or "").strip(),
                   normalizar_cpf(cpf) or (cpf or "").strip(), nasc])
        if isinstance(nasc, (datetime.date, datetime.datetime)):
            ws.cell(row=ws.max_row, column=5).number_format = "DD/MM/YYYY"
    larguras = {"A": 45, "B": 12, "C": 45, "D": 16, "E": 13}
    for col, larg in larguras.items():
        ws.column_dimensions[col].width = larg
    wb.save(caminho)
    return caminho


def gerar_planilha(destino_pasta: str, inivig: datetime.date, log=_log_padrao,
                   query_file="funeral.sql"):
    """Etapa única: consulta + dedupe + gravação. Devolve (caminho, qtd_linhas)."""
    linhas = consultar(inivig, log=log, query_file=query_file)
    if not linhas:
        log("Nenhum segurado com cobertura funeral na vigência — nada a gerar.")
        return None, 0
    caminho = gravar_planilha(destino_pasta, inivig, linhas)
    log(f"Planilha gravada: {caminho}")
    return caminho, len(linhas)
