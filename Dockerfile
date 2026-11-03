# Imagem da tela web do SISTEMA DE ENVIO PORTO SEGURO para o Render — docs/DEPLOY-RENDER.md.
# Modelo: Dockerfile do CertificadosGerador (python slim + libfbclient2 + testes no build).
# O Render precisa de Docker aqui porque o driver fdb carrega a biblioteca cliente
# do Firebird (libfbclient2), que o runtime "Python" nativo do Render não tem.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# libfbclient2: biblioteca cliente que o fdb carrega (servidor Firebird 2.5).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfbclient2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Testes unitários no build (sem banco): se falhar, o deploy para aqui.
# (só os testes sem tkinter: a imagem slim não tem Tk e o desktop não roda aqui)
RUN python -m unittest tests.test_gerador_funeral tests.test_web

RUN mkdir -p /app/saida
ENV WEB_PASTA_SAIDA=/app/saida

EXPOSE 8000

# O Render injeta PORT. --proxy-headers confia nos X-Forwarded-* do Render (cookie Secure).
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
