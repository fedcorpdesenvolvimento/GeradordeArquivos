# -*- coding: utf-8 -*-
"""Fila de trabalhos em memória para a tela web.

Cada geração roda numa thread (as de Vida levam até alguns minutos e um
pedido HTTP não pode esperar tanto). A página /trabalhos/{id} se atualiza
sozinha e, ao terminar, oferece o download do arquivo. A fila vive só na
memória do processo: no Render, um deploy a esvazia (os arquivos também são
efêmeros) — por isso o usuário baixa o arquivo assim que fica pronto.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field

LIMITE_TRABALHOS = 50


@dataclass
class Trabalho:
    id: str
    titulo: str
    usuario: str
    criado_em: float = field(default_factory=time.time)
    status: str = "executando"        # executando | concluido | erro
    log: list = field(default_factory=list)
    arquivo: str | None = None
    resumo: str = ""
    erro: str | None = None

    def registrar(self, msg, transiente=False):
        self.log.append(str(msg))

    @property
    def nome_arquivo(self):
        return os.path.basename(self.arquivo) if self.arquivo else None


_trabalhos: dict[str, Trabalho] = {}
_lock = threading.Lock()


def _podar():
    if len(_trabalhos) <= LIMITE_TRABALHOS:
        return
    antigos = sorted(_trabalhos.values(), key=lambda t: t.criado_em)
    for t in antigos[: len(_trabalhos) - LIMITE_TRABALHOS]:
        if t.status != "executando":
            _trabalhos.pop(t.id, None)
            if t.arquivo and os.path.isfile(t.arquivo):
                try:
                    os.remove(t.arquivo)
                except OSError:
                    pass


def iniciar(titulo: str, usuario: str, funcao, *args, **kwargs) -> Trabalho:
    """funcao(trabalho, *args, **kwargs) -> (arquivo ou None, resumo). Roda em thread."""
    trabalho = Trabalho(id=uuid.uuid4().hex[:12], titulo=titulo, usuario=usuario)
    with _lock:
        _trabalhos[trabalho.id] = trabalho
        _podar()

    def _rodar():
        try:
            arquivo, resumo = funcao(trabalho, *args, **kwargs)
            trabalho.arquivo = arquivo
            trabalho.resumo = resumo or ""
            trabalho.status = "concluido"
        except Exception as e:  # noqa: BLE001 - o erro vai para a tela
            trabalho.erro = str(e)
            trabalho.log.append(f"[ERRO] {e}")
            trabalho.status = "erro"

    threading.Thread(target=_rodar, daemon=True, name=f"trabalho-{trabalho.id}").start()
    return trabalho


def obter(id_: str) -> Trabalho | None:
    with _lock:
        return _trabalhos.get(id_)


def listar(usuario: str | None = None) -> list[Trabalho]:
    with _lock:
        itens = [t for t in _trabalhos.values() if usuario is None or t.usuario == usuario]
    return sorted(itens, key=lambda t: t.criado_em, reverse=True)
