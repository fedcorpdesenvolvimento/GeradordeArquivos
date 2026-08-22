# -*- coding: utf-8 -*-
"""Envio de arquivos para o SFTP da Porto Seguro (/Porto/Remessa).

O upload é feito com nome temporário .part e renomeado no final, conferindo
o tamanho — assim a Porto nunca vê (nem processa) um arquivo pela metade.
"""
import os
import socket

import paramiko

from config import SFTP_CONFIG


def _conectar() -> paramiko.Transport:
    host = SFTP_CONFIG["host"]
    try:
        socket.getaddrinfo(host, SFTP_CONFIG["port"])
    except socket.gaierror:
        host = SFTP_CONFIG["host_fallback_ip"]
    t = paramiko.Transport((host, SFTP_CONFIG["port"]))
    t.connect(username=SFTP_CONFIG["user"], password=SFTP_CONFIG["password"])
    return t


def enviar_arquivo(local: str, log=print) -> str:
    """Envia um arquivo local para /Porto/Remessa e retorna o caminho remoto.

    Levanta exceção em qualquer falha (conexão, autenticação, tamanho
    divergente) — quem chama decide como mostrar o erro.
    """
    destino = SFTP_CONFIG["destino"]
    nome = os.path.basename(local)
    tamanho_local = os.path.getsize(local)
    remoto_final = f"{destino}/{nome}"
    remoto_temp = f"{remoto_final}.part"

    transport = _conectar()
    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
        log(f"Enviando {nome} ({tamanho_local} bytes) para {destino} ...")
        sftp.put(local, remoto_temp)
        attrs = sftp.stat(remoto_temp)
        if attrs.st_size != tamanho_local:
            sftp.remove(remoto_temp)
            raise IOError(f"Tamanho divergente (local {tamanho_local}, "
                          f"remoto {attrs.st_size}). Upload descartado.")
        sftp.rename(remoto_temp, remoto_final)
        log(f"[ok] Enviado e verificado: {remoto_final} ({attrs.st_size} bytes)")
        return remoto_final
    finally:
        transport.close()
