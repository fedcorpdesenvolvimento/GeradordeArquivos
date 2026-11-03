# -*- coding: utf-8 -*-
"""Login da tela web — usuários fixos definidos por variáveis de ambiente.

Decisão do usuário (03/11/2026): dois usuários fixos, sem cadastro em banco.
  WEB_USUARIOS = "alberto@grupofedcorp.com.br,beneficiosocial@grupofedcorp.com.br"
  WEB_SENHA    = senha compartilhada (no .env local; no Render, em Environment)
  WEB_SENHA_<n> (opcional) = senha própria do n-ésimo usuário da lista (1, 2, ...)
  WEB_SEGREDO_SESSAO (opcional) = chave que assina o cookie; sem ela, gera-se
    uma aleatória a cada subida (as sessões caem a cada deploy).

Padrões copiados do CertificadosGerador (web/auth.py): cookie httpOnly +
SameSite=Lax + Secure em HTTPS, 8 h; 10 falhas por e-mail+IP em 15 min
bloqueiam; comparação em tempo constante; mensagem de erro única.
"""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_SESSAO = "envioporto_sessao"
HORAS_SESSAO = 8
CAMINHOS_PUBLICOS = frozenset({"/login", "/api/saude"})
PREFIXOS_PUBLICOS = ("/static/",)


def _usuarios() -> dict[str, str]:
    """{email: senha} a partir do ambiente. Vazio se não configurado."""
    emails = [e.strip().lower() for e in os.getenv("WEB_USUARIOS", "").split(",") if e.strip()]
    senha_comum = os.getenv("WEB_SENHA", "")
    tabela = {}
    for i, email in enumerate(emails, start=1):
        tabela[email] = os.getenv(f"WEB_SENHA_{i}") or senha_comum
    return {e: s for e, s in tabela.items() if s}


def configurado() -> bool:
    return bool(_usuarios())


_SEGREDO = os.getenv("WEB_SEGREDO_SESSAO") or secrets.token_urlsafe(32)
_serializador = URLSafeTimedSerializer(_SEGREDO, salt="envioporto-sessao")


class LimiteTentativas:
    def __init__(self, maximo=10, janela_seg=15 * 60):
        self.maximo, self.janela = maximo, janela_seg
        self._falhas: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def bloqueado(self, chave: str) -> bool:
        agora = time.time()
        with self._lock:
            fila = self._falhas[chave]
            while fila and fila[0] < agora - self.janela:
                fila.popleft()
            return len(fila) >= self.maximo

    def registrar_falha(self, chave: str) -> None:
        with self._lock:
            self._falhas[chave].append(time.time())

    def limpar(self, chave: str) -> None:
        with self._lock:
            self._falhas.pop(chave, None)


limite = LimiteTentativas()


def autenticar(email: str, senha: str, ip: str) -> str | None:
    """Devolve o e-mail normalizado se as credenciais conferem; senão None."""
    email = (email or "").strip().lower()
    chave = f"{email}|{ip}"
    if limite.bloqueado(chave):
        return None
    esperado = _usuarios().get(email, "")
    ok = bool(esperado) and hmac.compare_digest(senha.encode(), esperado.encode())
    if ok:
        limite.limpar(chave)
        return email
    limite.registrar_falha(chave)
    return None


def criar_cookie(resposta, email: str, https: bool) -> None:
    token = _serializador.dumps({"email": email})
    resposta.set_cookie(COOKIE_SESSAO, token, max_age=HORAS_SESSAO * 3600,
                        httponly=True, samesite="lax", secure=https, path="/")


def apagar_cookie(resposta) -> None:
    resposta.delete_cookie(COOKIE_SESSAO, path="/")


def usuario_do_cookie(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_SESSAO)
    if not token:
        return None
    try:
        dados = _serializador.loads(token, max_age=HORAS_SESSAO * 3600)
    except (BadSignature, SignatureExpired):
        return None
    email = dados.get("email")
    return email if email in _usuarios() else None


def usuario_atual(request: Request) -> str:
    """Dependência FastAPI: exige sessão válida; sem ela redireciona ao login."""
    email = usuario_do_cookie(request)
    if not email:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return email


def eh_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def redirecionar_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)
