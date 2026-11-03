# Imagem da tela web do SISTEMA DE ENVIO PORTO SEGURO para o Render — docs/DEPLOY-RENDER.md.
# Modelo: Dockerfile do CertificadosGerador (python slim + testes no build).
# O Render precisa de Docker aqui porque o driver fdb carrega a biblioteca cliente
# do Firebird, que o runtime "Python" nativo do Render não tem.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cliente Firebird 2.5.9 OFICIAL (mesma versão do servidor e do fbclient.dll das
# estações Windows). O pacote libfbclient2 do Debian é o cliente 3.x e, contra o
# servidor 2.5 via túnel, devolvia "SQLCODE -923 connection rejected by remote
# interface" (03/11/2026). A libfbclient 2.5.9 só depende de libc/libm/libdl/
# libpthread/librt e de libncurses.so.5, que o Debian atual não tem — o link
# para a libncurses.so.6 resolve (os símbolos usados são compatíveis).
ARG FB_TGZ=https://github.com/FirebirdSQL/firebird/releases/download/R2_5_9/FirebirdCS-2.5.9.27139-0.amd64.tar.gz
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl libncurses6 \
    && rm -rf /var/lib/apt/lists/* \
    && cd /tmp \
    && curl -fsSL -o fb.tgz "$FB_TGZ" \
    && tar xzf fb.tgz \
    && tar xzf FirebirdCS-2.5.9.27139-0.amd64/buildroot.tar.gz ./opt/firebird/lib/libfbclient.so.2.5.9 \
    && install -m 644 opt/firebird/lib/libfbclient.so.2.5.9 /usr/lib/x86_64-linux-gnu/libfbclient.so.2.5.9 \
    && ln -sf libfbclient.so.2.5.9 /usr/lib/x86_64-linux-gnu/libfbclient.so.2 \
    && ln -sf libfbclient.so.2.5.9 /usr/lib/x86_64-linux-gnu/libfbclient.so \
    && ln -sf libncurses.so.6 /usr/lib/x86_64-linux-gnu/libncurses.so.5 \
    && ldconfig \
    && rm -rf /tmp/fb.tgz /tmp/FirebirdCS-2.5.9.27139-0.amd64 /tmp/opt

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Confere no build que o fdb carrega a biblioteca 2.5.9 (se falhar, o deploy para aqui).
RUN python -c "import fdb; fdb.load_api(); print('fbclient carregada:', fdb.fbcore.api.fb_library_name if hasattr(fdb.fbcore, 'api') else 'ok')"

COPY . .

# Testes unitários no build (sem banco): se falhar, o deploy para aqui.
# (só os testes sem tkinter: a imagem slim não tem Tk e o desktop não roda aqui)
# As variáveis do Render não existem durante o build e config.py aborta sem elas,
# então este passo recebe valores fictícios — valem só aqui, não na execução.
RUN FB_HOST=build FB_DATABASE=build FB_USER=build FB_PASSWORD=build \
    SFTP_HOST=build SFTP_FALLBACK_IP=127.0.0.1 SFTP_USER=build SFTP_PASSWORD=build \
    python -m unittest tests.test_gerador_funeral tests.test_web

RUN mkdir -p /app/saida
ENV WEB_PASTA_SAIDA=/app/saida

EXPOSE 8000

# O Render injeta PORT. --proxy-headers confia nos X-Forwarded-* do Render (cookie Secure).
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
