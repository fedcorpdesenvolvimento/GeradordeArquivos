# -*- coding: utf-8 -*-
"""MODELO do config.py — copie este arquivo para config.py e preencha.

O config.py real contém senhas e por isso NÃO vai para o Git (.gitignore).
Em um clone novo do repositório:  copy config_exemplo.py config.py
e preencha os valores reais.
"""

# --- CONFIGURAÇÕES DO BANCO ---
DB_CONFIG = {
    'host': 'IP_DO_SERVIDOR_FIREBIRD',
    'database': r'CAMINHO\DO\BANCO\FATURA.GDB',
    'user': 'USUARIO',
    'password': 'SENHA',
    'charset': 'ASCII',   # padrão dos módulos antigos; Porto Assistência usa WIN1252
}

# --- CONFIGURAÇÕES DO SFTP DA PORTO SEGURO (módulo Porto Assistência) ---
SFTP_CONFIG = {
    'host': 'sftp.portoseguro.com.br',
    # IP usado quando o DNS local não resolve o host acima
    # (descobrir com: nslookup sftp.portoseguro.com.br 8.8.8.8)
    'host_fallback_ip': 'IP_DE_FALLBACK',
    'port': 2022,
    'user': 'USUARIO_SFTP',
    'password': 'SENHA_SFTP',
    'destino': '/Porto/Remessa',
}
