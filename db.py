# -*- coding: utf-8 -*-
"""Ponto único de conexão com o Firebird (FATURA.GDB).

Hoje é um repasse simples para fdb.connect com os dados do config.py.
No futuro, o hub de conexão do sistema maior entra aqui — os módulos
continuam chamando db.conectar() sem saber a diferença.
"""
import fdb

from config import DB_CONFIG


def conectar(charset: str | None = None) -> fdb.Connection:
    """Abre uma conexão com o FATURA.GDB.

    charset: sobrepõe o charset do config.py quando o módulo precisar de
    outro (ex.: Porto Assistência usa WIN1252 por causa dos acentos).
    """
    cfg = dict(DB_CONFIG)
    if charset:
        cfg['charset'] = charset
    return fdb.connect(**cfg)
