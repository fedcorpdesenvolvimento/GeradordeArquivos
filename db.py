# -*- coding: utf-8 -*-
"""Ponto único de conexão com o Firebird (FATURA.GDB) — com pool.

Modelo copiado do FedHub-Backend (src/shared/database/connection_firebird.py,
08/2026): conexões ociosas ficam retidas num pool por processo e são
reaproveitadas; close() devolve ao pool em vez de fechar de verdade. Como
aqui os módulos usam charsets diferentes (Vida = ASCII, Porto Assistência =
WIN1252) e o charset é fixado na abertura da conexão, há um pool separado
por charset.

Os módulos continuam chamando db.conectar() e con.close() normalmente —
a interface não mudou.
"""
import queue
import threading

import fdb

from config import DB_CONFIG, FB_POOL_SIZE

# um pool (LifoQueue) por charset; criado sob demanda
_pools: dict[str, queue.LifoQueue] = {}
_pools_lock = threading.Lock()


def _pool_do_charset(charset: str) -> queue.LifoQueue:
    with _pools_lock:
        if charset not in _pools:
            _pools[charset] = queue.LifoQueue(maxsize=FB_POOL_SIZE)
        return _pools[charset]


class ConexaoPool:
    """Proxy de conexão do pool: close() devolve ao pool em vez de fechar.

    A devolução faz rollback para garantir que nenhuma transação pendente
    vaze para o próximo usuário da conexão.
    """

    def __init__(self, conn, charset: str):
        self._conn = conn
        self._charset = charset
        self._fechada = False

    def close(self):
        if self._fechada:
            return
        self._fechada = True
        _devolver(self._conn, self._charset)

    def __getattr__(self, nome):
        return getattr(self._conn, nome)

    # permite usar "with db.conectar() as con:" se algum módulo quiser
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _criar_conexao(charset: str) -> fdb.Connection:
    return fdb.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        charset=charset,
    )


def _validar(conn) -> bool:
    """Confere se a conexão ociosa ainda está viva antes de reutilizá-la."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False


def _devolver(conn, charset: str):
    try:
        conn.rollback()
        _pool_do_charset(charset).put_nowait(conn)
    except queue.Full:
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def conectar(charset: str | None = None) -> ConexaoPool:
    """Abre (ou reaproveita do pool) uma conexão com o FATURA.GDB.

    charset: sobrepõe o charset padrão do .env quando o módulo precisar de
    outro (ex.: Porto Assistência usa WIN1252 por causa dos acentos).
    O objeto devolvido se comporta como a conexão fdb; close() devolve a
    conexão ao pool para reuso.
    """
    charset = charset or DB_CONFIG['charset']
    pool = _pool_do_charset(charset)
    while True:
        try:
            conn = pool.get_nowait()
        except queue.Empty:
            break
        if _validar(conn):
            return ConexaoPool(conn, charset)
    return ConexaoPool(_criar_conexao(charset), charset)
