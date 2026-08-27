# -*- coding: utf-8 -*-
"""Núcleo de geração do PORTO DENTAL (sem interface).

Fluxo em duas etapas, na ordem exigida pela tela (porto_dental.py):

1. consultar_faturas(): executa queries/portodental_1.sql com :inivig,
   devolve os números de fatura e o total de vidas; cada linha do
   resultado vai para o log da tela.
2. gerar_planilha(): executa queries/portodental_2.sql alimentada pelos
   números de fatura da etapa 1 (marcador :faturas dentro de um IN) e
   grava portodental-MMYYYY.xlsx — o cabeçalho da planilha são as
   colunas da própria query 2, na ordem em que a query as retorna.

O contrato de aliases das queries está comentado nos próprios .sql.
"""
import datetime
import os
import re

from openpyxl import Workbook

import db
from modulos.gerador_porto import carregar_query, _preparar_parametros

# Limite de itens por IN (o Firebird 2.5 aceita até 1500; folga proposital)
BLOCO_IN = 1000
FETCH_BLOCO = 2000


def _log_padrao(msg, transiente=False):
    print(msg)


def consultar_faturas(inivig: datetime.date, log=_log_padrao) -> tuple[list, int]:
    """Etapa 1 — roda a query 1 e devolve (faturas, total_de_vidas).

    Loga cada linha retornada. Total de vidas: soma da coluna VIDAS se
    existir; senão, contagem de linhas.
    """
    sql = carregar_query("portodental_1.sql")
    sql, params = _preparar_parametros(sql, inivig)

    con = db.conectar(charset="WIN1252")
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        nomes = [d[0].strip().upper() for d in cur.description]
        if "FATURA" not in nomes:
            raise RuntimeError(
                "A query portodental_1.sql precisa retornar uma coluna com "
                f"alias FATURA. Colunas retornadas: {nomes}")
        idx_fatura = nomes.index("FATURA")
        idx_vidas = nomes.index("VIDAS") if "VIDAS" in nomes else None

        faturas = []
        total_vidas = 0
        for linha in cur.fetchall():
            faturas.append(linha[idx_fatura])
            if idx_vidas is not None:
                total_vidas += int(linha[idx_vidas] or 0)
            log("  " + " | ".join(
                f"{nome}: {valor}" for nome, valor in zip(nomes, linha)))
        if idx_vidas is None:
            total_vidas = len(faturas)
        cur.close()
    finally:
        con.close()

    return faturas, total_vidas


def gerar_planilha(destino_pasta: str, inivig: datetime.date, faturas: list,
                   log=_log_padrao) -> tuple[str, int]:
    """Etapa 2 — gera o portodental-MMYYYY.xlsx e retorna (caminho, linhas).

    A query 2 deve conter o marcador :faturas dentro de um IN; ele é
    substituído pelos números da etapa 1 em blocos de BLOCO_IN (limite do
    IN no Firebird). O cabeçalho da planilha vem das colunas da query.
    """
    if not faturas:
        raise ValueError("Nenhuma fatura para gerar — rode a consulta antes.")
    os.makedirs(destino_pasta, exist_ok=True)
    competencia = inivig.strftime("%m%Y")
    caminho = os.path.join(destino_pasta, f"portodental-{competencia}.xlsx")

    sql_base = carregar_query("portodental_2.sql")
    if not re.search(r":faturas\b", sql_base, flags=re.IGNORECASE):
        raise RuntimeError(
            "A query portodental_2.sql precisa conter o marcador :faturas "
            "dentro de um IN (ver comentário no próprio arquivo).")

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title="PORTO DENTAL")
    cabecalho_gravado = False
    gravadas = 0

    con = db.conectar(charset="WIN1252")
    try:
        for i in range(0, len(faturas), BLOCO_IN):
            bloco_faturas = faturas[i:i + BLOCO_IN]
            lista_in = ",".join(str(f) for f in bloco_faturas)
            sql = re.sub(r":faturas\b", lista_in, sql_base, flags=re.IGNORECASE)
            sql, params = _preparar_parametros(sql, inivig)

            cur = con.cursor()
            cur.execute(sql, params)
            if not cabecalho_gravado:
                ws.append([d[0].strip().upper() for d in cur.description])
                cabecalho_gravado = True
            while True:
                bloco = cur.fetchmany(FETCH_BLOCO)
                if not bloco:
                    break
                for linha in bloco:
                    ws.append(list(linha))
                gravadas += len(bloco)
                log(f"  ... {gravadas} linhas", transiente=True)
            cur.close()
    finally:
        con.close()

    wb.save(caminho)
    log(f"Arquivo gerado: {caminho} ({gravadas} linhas)")
    return caminho, gravadas
