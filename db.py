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


TIMEOUT_ALCANCE_S = 10


def _conferir_alcance(host: str, port: int) -> None:
    """Falha rápido se o servidor não responde na porta (o fdb não tem timeout
    de conexão e ficaria minutos pendurado — p.ex. FB_HOST com o IP da rede
    local configurado no Render)."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT_ALCANCE_S):
            pass
    except OSError as e:
        raise ConnectionError(
            f"Não foi possível alcançar o Firebird em {host}:{port} em {TIMEOUT_ALCANCE_S}s "
            f"({e}). Confira FB_HOST/FB_PORT (no Render: endereço do túnel ngrok, não o IP da rede local) "
            f"e se o túnel está aberto.") from e


# Driver: "fdb" (padrão; usa a fbclient nativa, como o desktop) ou "firebirdsql"
# (Python puro, implementa o protocolo sem biblioteca nativa). No Render, via
# túnel ngrok, a fbclient devolvia "SQLCODE -923 connection rejected by remote
# interface" mesmo na versão 2.5.9, e o firebirdsql conecta — escolha por
# DB_DRIVER no ambiente (03/11/2026). Os dois seguem a DB-API 2 e o resto do
# sistema não vê diferença (rowcount, parâmetros ?, pandas.read_sql).
import os as _os

DRIVER = (_os.getenv("DB_DRIVER") or "fdb").strip().lower()
DRIVERS_VALIDOS = ("fdb", "firebirdsql")


def _conectar_com(driver: str, charset: str):
    if driver == "firebirdsql":
        import firebirdsql
        # O fdb com ASCII deixa os bytes acentuados passarem (comportamento
        # herdado da Vida); o firebirdsql decodifica à risca e quebra em 0xD3
        # etc. As colunas são NONE (bytes WIN1252), então para este driver
        # ASCII vira WIN1252 — mesmos bytes no fio, texto legível em Python.
        charset_driver = "WIN1252" if charset.upper() == "ASCII" else charset
        return firebirdsql.connect(
            host=DB_CONFIG['host'], port=DB_CONFIG['port'], database=DB_CONFIG['database'],
            user=DB_CONFIG['user'], password=DB_CONFIG['password'], charset=charset_driver,
            timeout=60,
        )
    return fdb.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        charset=charset,
    )


def _criar_conexao(charset: str):
    if DRIVER not in DRIVERS_VALIDOS:
        raise RuntimeError(f"DB_DRIVER inválido: {DRIVER!r} (use {' ou '.join(DRIVERS_VALIDOS)})")
    _conferir_alcance(DB_CONFIG['host'], DB_CONFIG['port'])
    return _conectar_com(DRIVER, charset)


def sondar_tcp(host: str | None = None, port: int | None = None, espera_s: float = 3.0) -> dict:
    """Diagnóstico de rede: abre o socket e observa o que acontece ANTES de
    qualquer protocolo Firebird. O Firebird fica em silêncio esperando o
    cliente falar; se o outro lado fecha sozinho ("fechado_pelo_servidor"),
    quem recusou foi a borda do túnel (ngrok) ou um firewall — não o banco."""
    import socket, time
    host = host or DB_CONFIG['host']
    port = port or DB_CONFIG['port']
    saida = {"host": host, "port": port}
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT_ALCANCE_S)
    except OSError as e:
        saida.update(resultado="tcp_recusado", detalhe=str(e),
                     segundos=round(time.perf_counter() - t0, 3))
        return saida
    saida["conexao_s"] = round(time.perf_counter() - t0, 3)
    try:
        s.settimeout(espera_s)
        t1 = time.perf_counter()
        dado = s.recv(64)
        saida["apos_s"] = round(time.perf_counter() - t1, 3)
        if dado:
            saida.update(resultado="servidor_falou_primeiro", bytes=len(dado), hex=dado[:16].hex())
        else:
            saida["resultado"] = "fechado_pelo_servidor"
    except socket.timeout:
        saida["resultado"] = "silencio"   # esperado: o Firebird aguarda o op_connect
    except OSError as e:
        saida.update(resultado="erro_recv", detalhe=str(e))
    finally:
        s.close()
    return saida


def testar_drivers(charset: str | None = None) -> dict:
    """Diagnóstico: tenta abrir uma conexão com cada driver e devolve
    {driver: {"ok": bool, "segundos": float, "erro": str|None}}."""
    import time
    charset = charset or DB_CONFIG['charset']
    saida = {}
    for driver in DRIVERS_VALIDOS:
        t0 = time.perf_counter()
        try:
            conn = _conectar_com(driver, charset)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM RDB$DATABASE")
            cur.fetchone()
            conn.close()
            saida[driver] = {"ok": True, "segundos": round(time.perf_counter() - t0, 3), "erro": None}
        except Exception as e:  # noqa: BLE001 - é diagnóstico
            saida[driver] = {"ok": False, "segundos": round(time.perf_counter() - t0, 3),
                             "erro": f"{type(e).__name__}: {str(e)[:200]}"}
    return saida


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
