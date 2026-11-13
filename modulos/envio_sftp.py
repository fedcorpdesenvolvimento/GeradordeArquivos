# -*- coding: utf-8 -*-
"""Envio de arquivos para o SFTP da Porto Seguro (/Porto/Remessa).

O upload é feito com nome temporário .part e renomeado no final, conferindo
o tamanho — assim a Porto nunca vê (nem processa) um arquivo pela metade.

Pegadinha do servidor da Porto (13/11/2026): logo depois do upload ele ainda
trata o .part como "em andamento" e recusa o rename com
"Resource busy ... because the file is currently in progress". O arquivo está
inteiro no servidor; só falta o nome. Por isso o rename é repetido com pausas
(até ~3 min) e, se mesmo assim não liberar, o próximo envio do mesmo arquivo
reaproveita o .part já completo (mesmo tamanho) e tenta só o rename de novo,
sem subir os megabytes outra vez.
"""
import os
import socket
import time

import paramiko

from config import SFTP_CONFIG

TENTATIVAS_RENAME = 18      # 18 x 10 s = 3 min
PAUSA_RENAME_S = 10


def _conectar() -> paramiko.Transport:
    host = SFTP_CONFIG["host"]
    try:
        socket.getaddrinfo(host, SFTP_CONFIG["port"])
    except socket.gaierror:
        host = SFTP_CONFIG["host_fallback_ip"]
    t = paramiko.Transport((host, SFTP_CONFIG["port"]))
    t.connect(username=SFTP_CONFIG["user"], password=SFTP_CONFIG["password"])
    return t


def _servidor_ocupado(erro: Exception) -> bool:
    msg = str(erro).lower()
    return "busy" in msg or "in progress" in msg or "em andamento" in msg


def _tamanho_remoto(sftp, caminho):
    """Tamanho do arquivo remoto, ou None se não existe."""
    try:
        return sftp.stat(caminho).st_size
    except IOError:
        return None


def _renomear_com_paciencia(sftp, origem, destino, log, dormir=time.sleep,
                            tentativas=TENTATIVAS_RENAME, pausa=PAUSA_RENAME_S):
    """Rename repetido enquanto o servidor responder 'busy / in progress'.
    Qualquer outro erro sobe na hora."""
    for tentativa in range(1, tentativas + 1):
        try:
            sftp.rename(origem, destino)
            return
        except IOError as e:
            if not _servidor_ocupado(e) or tentativa == tentativas:
                raise
            log(f"  servidor ainda processando o arquivo ({tentativa}/{tentativas}); "
                f"nova tentativa em {pausa}s...")
            dormir(pausa)


def enviar_arquivo(local: str, log=print, dormir=time.sleep) -> str:
    """Envia um arquivo local para /Porto/Remessa e retorna o caminho remoto.

    Levanta exceção em qualquer falha (conexão, autenticação, tamanho
    divergente, servidor que não libera o rename) — quem chama decide como
    mostrar o erro. `dormir` existe para os testes não esperarem de verdade.
    """
    destino = SFTP_CONFIG["destino"]
    nome = os.path.basename(local)
    tamanho_local = os.path.getsize(local)
    remoto_final = f"{destino}/{nome}"
    remoto_temp = f"{remoto_final}.part"

    transport = _conectar()
    try:
        sftp = paramiko.SFTPClient.from_transport(transport)

        if _tamanho_remoto(sftp, remoto_final) is not None:
            log(f"[aviso] {remoto_final} já existe no servidor e será substituído.")

        pendente = _tamanho_remoto(sftp, remoto_temp)
        if pendente == tamanho_local:
            # Envio anterior subiu tudo mas o rename foi recusado: só renomear.
            log(f"Encontrado {nome}.part completo no servidor ({pendente} bytes); "
                f"concluindo o envio sem subir de novo.")
        else:
            if pendente is not None:
                log(f"Removendo {nome}.part incompleto de um envio anterior ({pendente} bytes).")
                sftp.remove(remoto_temp)
            log(f"Enviando {nome} ({tamanho_local} bytes) para {destino} ...")
            sftp.put(local, remoto_temp)
            attrs = sftp.stat(remoto_temp)
            if attrs.st_size != tamanho_local:
                sftp.remove(remoto_temp)
                raise IOError(f"Tamanho divergente (local {tamanho_local}, "
                              f"remoto {attrs.st_size}). Upload descartado.")

        try:
            _renomear_com_paciencia(sftp, remoto_temp, remoto_final, log, dormir=dormir)
        except IOError as e:
            if _servidor_ocupado(e):
                raise IOError(
                    f"O arquivo subiu inteiro como {nome}.part ({tamanho_local} bytes), mas o "
                    f"servidor da Porto não liberou o nome final em "
                    f"{TENTATIVAS_RENAME * PAUSA_RENAME_S // 60} min ({e}). Clique em enviar "
                    f"de novo mais tarde: o sistema só vai renomear, sem subir o arquivo outra vez.") from e
            raise
        log(f"[ok] Enviado e verificado: {remoto_final} ({tamanho_local} bytes)")
        return remoto_final
    finally:
        transport.close()
