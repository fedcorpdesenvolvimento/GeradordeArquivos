# -*- coding: utf-8 -*-
"""SISTEMA DE ENVIO PORTO SEGURO — tela web (FastAPI), branch web-render.

Mesmos geradores do desktop (modulos/gerador_*.py), sem tkinter:
  /vida          SUBGRUPOS DE VIDA (inconsistências por subgrupo antes de gerar)
  /funeral       GERAR ARQUIVO FUNERAL
  /dental        GERA PORTO DENTAL (duas etapas)
  /sempreodonto  GERAR DENTAL SEMPRE ODONTO (duas etapas)
  /assistencia   PORTO ASSISTÊNCIA (xlsx; envio SFTP só com confirmação)
  /trabalhos/{id}  acompanhamento e download

Rode localmente:  uvicorn web.app:app --reload --port 8000
No Render: Dockerfile + render.yaml (docs/DEPLOY-RENDER.md).
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

import db
from modulos import gerador_dental, gerador_funeral, gerador_porto, gerador_vida
from web import auth, trabalhos

PASTA_WEB = Path(__file__).resolve().parent
BASE_DIR = PASTA_WEB.parent
PASTA_SAIDA = Path(os.getenv("WEB_PASTA_SAIDA", str(BASE_DIR / "saida")))
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("envioporto.web")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="SISTEMA DE ENVIO PORTO SEGURO", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(PASTA_WEB / "static")), name="static")

_jinja = Environment(loader=FileSystemLoader(str(PASTA_WEB / "templates")),
                     autoescape=select_autoescape(["html"]))

MODULOS = [
    ("vida", "SUBGRUPOS DE VIDA", "Relatório de segurados de Vida por subgrupo, com checagem de inconsistências."),
    ("assistencia", "PORTO ASSISTÊNCIA", "Relação mensal Residencial / Auto / Empresarial (envio SFTP opcional)."),
    ("dental", "GERA PORTO DENTAL", "Consulta de vidas e planilha mensal do Porto Dental."),
    ("sempreodonto", "GERAR DENTAL SEMPRE ODONTO", "Consulta de vidas e planilha mensal do Sempre Odonto."),
    ("funeral", "GERAR ARQUIVO FUNERAL", "Segurados com cobertura FUNERAL/CERIMONIAL, sem CPF repetido."),
]


# ------------------------------------------------------------------ apoio
def _pagina(nome, request: Request, usuario=None, **ctx) -> HTMLResponse:
    tpl = _jinja.get_template(nome)
    return HTMLResponse(tpl.render(usuario=usuario, modulos=MODULOS, request=request, **ctx))


def _data_padrao() -> str:
    return gerador_vida.primeiro_dia_mes_anterior().isoformat()


def _parse_data(texto: str) -> date:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise HTTPException(400, "Data de vigência inválida.")


@app.exception_handler(HTTPException)
async def _trata_http(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    usuario = auth.usuario_do_cookie(request)
    return _pagina("erro.html", request, usuario, codigo=exc.status_code, detalhe=exc.detail)


@app.exception_handler(Exception)
async def _trata_inesperado(request: Request, exc: Exception):
    """Erro não previsto (ex.: banco fora de alcance): mostra a causa na tela em
    vez de um "Internal Server Error" mudo, e registra no log do Render."""
    log.exception("erro inesperado em %s %s", request.method, request.url.path)
    usuario = auth.usuario_do_cookie(request)
    return _pagina("erro.html", request, usuario, codigo=500,
                   detalhe=f"{type(exc).__name__}: {exc}")


@app.middleware("http")
async def _cabecalhos(request: Request, call_next):
    t0 = time.perf_counter()
    resposta = await call_next(request)
    duracao = time.perf_counter() - t0
    if not request.url.path.startswith("/static/"):
        # aparece no log do Render: serve para ver onde o tempo está indo
        log.info("%s %s -> %s em %.2fs", request.method, request.url.path, resposta.status_code, duracao)
    resposta.headers["X-Tempo"] = f"{duracao:.2f}s"
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("Referrer-Policy", "same-origin")
    return resposta


# ------------------------------------------------------------------ login
@app.get("/api/saude")
def saude():
    return {"ok": True, "usuarios_configurados": auth.configurado(),
            "commit": os.getenv("RENDER_GIT_COMMIT", "")[:7] or None}


@app.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request):
    if auth.usuario_do_cookie(request):
        return RedirectResponse("/", status_code=303)
    return _pagina("login.html", request, None, erro=None, configurado=auth.configurado())


@app.post("/login")
def fazer_login(request: Request, email: str = Form(""), senha: str = Form("")):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    usuario = auth.autenticar(email, senha, ip)
    if not usuario:
        return _pagina("login.html", request, None, erro="E-mail ou senha inválidos.", configurado=auth.configurado())
    resposta = RedirectResponse("/", status_code=303)
    auth.criar_cookie(resposta, usuario, auth.eh_https(request))
    return resposta


@app.post("/logout")
def logout():
    resposta = RedirectResponse("/login", status_code=303)
    auth.apagar_cookie(resposta)
    return resposta


@app.get("/api/diagnostico")
def diagnostico(usuario: str = Depends(auth.usuario_atual)):
    """Mede, de dentro do servidor, o custo de falar com o Firebird pelo túnel:
    abrir conexão (ou reaproveitar do pool), SELECT 1, listar subgrupos."""
    import config
    medidas = {"fb_host": config.DB_CONFIG["host"], "fb_port": config.DB_CONFIG["port"],
               "driver_em_uso": db.DRIVER, "sonda_tcp": db.sondar_tcp(),
               "teste_drivers": db.testar_drivers()}
    t0 = time.perf_counter()
    try:
        conn = db.conectar()
        medidas["conectar_s"] = round(time.perf_counter() - t0, 3)
        cur = conn.cursor()
        t0 = time.perf_counter(); cur.execute("SELECT 1 FROM RDB$DATABASE"); cur.fetchall()
        medidas["select1_s"] = round(time.perf_counter() - t0, 3)
        t0 = time.perf_counter(); n = len(gerador_vida.listar_subgrupos(conn))
        medidas["listar_subgrupos_s"] = round(time.perf_counter() - t0, 3); medidas["subgrupos"] = n
        t0 = time.perf_counter(); cur.execute("SELECT COUNT(*) FROM FATURAS WHERE STATUS='A' AND RAMO='V' AND DT_INI_VIG = '10/01/2026'"); medidas["faturas_out_2026"] = cur.fetchone()[0]
        medidas["count_faturas_s"] = round(time.perf_counter() - t0, 3)
        conn.close()
        t0 = time.perf_counter(); conn = db.conectar(); conn.close()
        medidas["reconectar_do_pool_s"] = round(time.perf_counter() - t0, 3)
        medidas["ok"] = True
    except Exception as e:
        medidas["ok"] = False; medidas["erro"] = str(e)
    return JSONResponse(medidas)


# ------------------------------------------------------------------ menu
@app.get("/", response_class=HTMLResponse)
def menu(request: Request, usuario: str = Depends(auth.usuario_atual)):
    return _pagina("menu.html", request, usuario, trabalhos=trabalhos.listar()[:10])


# ------------------------------------------------------------------ VIDA
@app.get("/vida", response_class=HTMLResponse)
def pagina_vida(request: Request, usuario: str = Depends(auth.usuario_atual)):
    conn = db.conectar()
    try:
        subgrupos = gerador_vida.listar_subgrupos(conn)
    finally:
        conn.close()
    return _pagina("vida.html", request, usuario, subgrupos=subgrupos, data=_data_padrao())


@app.post("/vida/verificar", response_class=HTMLResponse)
async def vida_verificar(request: Request, usuario: str = Depends(auth.usuario_atual)):
    form = await request.form()
    data_obj = _parse_data(form.get("data"))
    nomes = form.getlist("subgrupo")
    if not nomes:
        raise HTTPException(400, "Selecione ao menos um subgrupo.")
    achados = []
    conn = db.conectar()
    try:
        cur = conn.cursor()
        for nome in nomes:
            cur.execute("SELECT SUBGRUPO FROM SUBGRUPOSEGURADORA WHERE NOME_SUBGRP = ?", (nome,))
            res = cur.fetchone()
            if not res:
                continue
            for apol, seq, fat, adm in gerador_vida.inconsistencias_do_subgrupo(cur, data_obj, res[0]):
                achados.append((nome, res[0], apol, seq, fat, adm))
    finally:
        conn.close()
    if not achados:
        return _iniciar_vida(usuario, data_obj, nomes)
    return _pagina("vida_inconsistencias.html", request, usuario, achados=achados,
                   nomes=nomes, data=data_obj.isoformat(), data_br=data_obj.strftime("%d/%m/%Y"))


@app.post("/vida/gerar")
async def vida_gerar(request: Request, usuario: str = Depends(auth.usuario_atual)):
    form = await request.form()
    return _iniciar_vida(usuario, _parse_data(form.get("data")), form.getlist("subgrupo"))


def _iniciar_vida(usuario, data_obj, nomes):
    def _trabalho(t):
        caminho, linhas, aviso = gerador_vida.gerar_subgrupos(str(PASTA_SAIDA), data_obj, nomes, log=t.registrar)
        resumo = f"{linhas} linhas" + (" — ATENÇÃO: " + aviso.splitlines()[0] if aviso else "")
        return caminho, resumo
    t = trabalhos.iniciar(f"VIDA — {', '.join(nomes)} — {data_obj:%d/%m/%Y}", usuario, _trabalho)
    return RedirectResponse(f"/trabalhos/{t.id}", status_code=303)


@app.get("/vida/inconsistencias", response_class=HTMLResponse)
def vida_inconsistencias(request: Request, data: str = "", usuario: str = Depends(auth.usuario_atual)):
    data_obj = _parse_data(data) if data else gerador_vida.primeiro_dia_mes_anterior()
    conn = db.conectar()
    try:
        colunas, linhas = gerador_vida.relatorio_inconsistencias(conn.cursor(), data_obj)
    finally:
        conn.close()
    return _pagina("vida_relatorio.html", request, usuario, colunas=colunas, linhas=linhas,
                   data=data_obj.isoformat(), data_br=data_obj.strftime("%d/%m/%Y"))


# ------------------------------------------------------------------ FUNERAL
@app.get("/funeral", response_class=HTMLResponse)
def pagina_funeral(request: Request, usuario: str = Depends(auth.usuario_atual)):
    return _pagina("funeral.html", request, usuario, data=_data_padrao())


@app.post("/funeral/gerar")
def funeral_gerar(usuario: str = Depends(auth.usuario_atual), data: str = Form(...)):
    data_obj = _parse_data(data)

    def _trabalho(t):
        caminho, qtd = gerador_funeral.gerar_planilha(str(PASTA_SAIDA), data_obj, log=t.registrar)
        return caminho, f"{qtd} segurados"
    t = trabalhos.iniciar(f"FUNERAL — {data_obj:%d/%m/%Y}", usuario, _trabalho)
    return RedirectResponse(f"/trabalhos/{t.id}", status_code=303)


# ------------------------------------------------------------------ DENTAL / SEMPRE ODONTO
DENTAL = {
    "dental": dict(titulo="GERA PORTO DENTAL", q1="portodental_1.sql", q2="portodental_2.sql",
                   prefixo="portodental", aba="PORTO DENTAL", cor="verde"),
    "sempreodonto": dict(titulo="GERAR DENTAL SEMPRE ODONTO", q1="sempreodonto_1.sql", q2="sempreodonto_2.sql",
                         prefixo="sempreodonto", aba="SEMPRE ODONTO", cor="azul"),
}


def _dental(produto: str) -> dict:
    if produto not in DENTAL:
        raise HTTPException(404, "Produto não encontrado.")
    return DENTAL[produto]


def _rotas_dental(produto: str):
    """Três rotas por produto, com `produto` amarrado por closure (sem parâmetro
    de caminho: uma rota genérica "/{produto}" capturaria /assistencia e /funeral,
    e um parâmetro solto na assinatura viraria query obrigatória)."""
    cfg = _dental(produto)

    def pagina(request: Request, usuario: str = Depends(auth.usuario_atual)):
        return _pagina("dental.html", request, usuario, produto=produto, cfg=cfg, data=_data_padrao(),
                       faturas=None, total_vidas=None, log=[])

    def consultar(request: Request, usuario: str = Depends(auth.usuario_atual), data: str = Form(...)):
        data_obj = _parse_data(data)
        log = []
        faturas, total = gerador_dental.consultar_faturas(data_obj, log=lambda m, t=False: log.append(str(m)),
                                                          query_file=cfg["q1"])
        return _pagina("dental.html", request, usuario, produto=produto, cfg=cfg, data=data_obj.isoformat(),
                       faturas=faturas, total_vidas=total, log=log)

    def gerar(usuario: str = Depends(auth.usuario_atual), data: str = Form(...), faturas: str = Form("")):
        data_obj = _parse_data(data)
        lista = [int(f) for f in re.findall(r"\d+", faturas)]
        if not lista:
            raise HTTPException(400, "Rode a consulta (etapa 1) antes de gerar.")

        def _trabalho(t):
            caminho, linhas = gerador_dental.gerar_planilha(str(PASTA_SAIDA), data_obj, lista, log=t.registrar,
                                                            query_file=cfg["q2"], prefixo=cfg["prefixo"], aba=cfg["aba"])
            return caminho, f"{linhas} linhas, {len(lista)} faturas"
        t = trabalhos.iniciar(f"{cfg['titulo']} — {data_obj:%d/%m/%Y}", usuario, _trabalho)
        return RedirectResponse(f"/trabalhos/{t.id}", status_code=303)

    app.add_api_route(f"/{produto}", pagina, methods=["GET"], response_class=HTMLResponse, name=f"pagina_{produto}")
    app.add_api_route(f"/{produto}/consultar", consultar, methods=["POST"], response_class=HTMLResponse,
                      name=f"consultar_{produto}")
    app.add_api_route(f"/{produto}/gerar", gerar, methods=["POST"], name=f"gerar_{produto}")


for _produto in DENTAL:
    _rotas_dental(_produto)


# ------------------------------------------------------------------ ASSISTÊNCIA
@app.get("/assistencia", response_class=HTMLResponse)
def pagina_assistencia(request: Request, usuario: str = Depends(auth.usuario_atual)):
    return _pagina("assistencia.html", request, usuario, produtos=gerador_porto.PRODUTOS, data=_data_padrao())


@app.post("/assistencia/gerar")
async def assistencia_gerar(request: Request, usuario: str = Depends(auth.usuario_atual)):
    form = await request.form()
    data_obj = _parse_data(form.get("data"))
    selecao = {}
    for prod in gerador_porto.PRODUTOS:
        cod = prod["codigo"]
        if form.get(f"produto_{cod}"):
            limite = (form.get(f"limite_{cod}") or "").strip()
            selecao[cod] = int(limite) if limite.isdigit() and int(limite) > 0 else None
    if not selecao:
        raise HTTPException(400, "Selecione ao menos um produto.")
    enviar = form.get("enviar") == "sim" and form.get("confirmo_envio") == "sim"

    def _trabalho(t):
        caminho, resultado = gerador_porto.gerar_planilha(str(PASTA_SAIDA), data_obj, selecao, log=t.registrar)
        resumo = ", ".join(f"código {c}: {n} linhas" for c, n in resultado.items())
        if enviar:
            from modulos.envio_sftp import enviar_arquivo
            t.registrar("Enviando ao SFTP da Porto (/Porto/Remessa)...")
            remoto = enviar_arquivo(caminho, log=t.registrar)
            resumo += f" — ENVIADO: {remoto}"
        return caminho, resumo
    t = trabalhos.iniciar(f"ASSISTÊNCIA — {data_obj:%d/%m/%Y}" + (" + SFTP" if enviar else ""), usuario, _trabalho)
    return RedirectResponse(f"/trabalhos/{t.id}", status_code=303)


# ------------------------------------------------------------------ trabalhos
@app.get("/trabalhos/{id_}", response_class=HTMLResponse)
def pagina_trabalho(request: Request, id_: str, usuario: str = Depends(auth.usuario_atual)):
    t = trabalhos.obter(id_)
    if not t:
        raise HTTPException(404, "Trabalho não encontrado (o servidor pode ter reiniciado).")
    return _pagina("trabalho.html", request, usuario, t=t)


@app.get("/trabalhos/{id_}/estado")
def estado_trabalho(id_: str, usuario: str = Depends(auth.usuario_atual)):
    t = trabalhos.obter(id_)
    if not t:
        raise HTTPException(404, "Trabalho não encontrado.")
    return JSONResponse({"status": t.status, "log": t.log, "arquivo": t.nome_arquivo, "resumo": t.resumo})


@app.get("/trabalhos/{id_}/arquivo")
def baixar_arquivo(id_: str, usuario: str = Depends(auth.usuario_atual)):
    t = trabalhos.obter(id_)
    if not t or not t.arquivo or not os.path.isfile(t.arquivo):
        raise HTTPException(404, "Arquivo não disponível.")
    return FileResponse(t.arquivo, filename=t.nome_arquivo,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
