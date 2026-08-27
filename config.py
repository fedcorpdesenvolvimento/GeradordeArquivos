# -*- coding: utf-8 -*-
"""Configurações centrais do SISTEMA DE ENVIO PORTO SEGURO.

Modelo alinhado ao FedHub-Backend (08/2026): as credenciais e endereços
saíram do código e moram no arquivo .env (carregado com python-dotenv).
As variáveis do Firebird usam os MESMOS nomes do FedHub (FB_HOST, FB_PORT,
FB_DATABASE, FB_USER, FB_PASSWORD), para que o mesmo .env sirva quando os
módulos migrarem para lá.

Os módulos continuam importando DB_CONFIG/SFTP_CONFIG daqui — a interface
não mudou, só a origem dos valores.
"""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env fica ao lado deste arquivo — o caminho absoluto garante que funcione
# mesmo se o app for iniciado a partir de outra pasta.
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), encoding="utf-8")


def _env_obrigatoria(nome: str) -> str:
    """Lê uma env obrigatória; aborta na inicialização se ausente.

    Sem defaults para credenciais (padrão FedHub): um .env incompleto deve
    falhar na largada com mensagem clara, não rodar com valor de exemplo.
    """
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(
            f"Variável obrigatória ausente no .env: {nome}. "
            f"Copie o .env.exemplo para .env e preencha (pasta {BASE_DIR}).")
    return valor


# --- CONFIGURAÇÕES DO BANCO (mesma conexão do gerador de planilhas Vida) ---
DB_CONFIG = {
    'host': _env_obrigatoria('FB_HOST'),
    'port': int(os.getenv('FB_PORT', '3050')),
    'database': _env_obrigatoria('FB_DATABASE'),
    'user': _env_obrigatoria('FB_USER'),
    'password': _env_obrigatoria('FB_PASSWORD'),
    # padrão dos módulos antigos (Vida); Porto Assistência pede WIN1252
    'charset': os.getenv('FB_CHARSET', 'ASCII'),
}

# Máximo de conexões ociosas retidas no pool do db.py (padrão FedHub: 5)
FB_POOL_SIZE = int(os.getenv('FB_POOL_SIZE', '5'))

# --- CONFIGURAÇÕES DO SFTP DA PORTO SEGURO (módulo Porto Assistência) ---
SFTP_CONFIG = {
    'host': _env_obrigatoria('SFTP_HOST'),
    # O DNS da rede local não resolve o host acima; o envio tenta o nome e,
    # se o DNS falhar, cai automaticamente para o IP.
    'host_fallback_ip': _env_obrigatoria('SFTP_FALLBACK_IP'),
    'port': int(os.getenv('SFTP_PORT', '2022')),
    'user': _env_obrigatoria('SFTP_USER'),
    'password': _env_obrigatoria('SFTP_PASSWORD'),
    'destino': os.getenv('SFTP_DESTINO', '/Porto/Remessa'),
}
