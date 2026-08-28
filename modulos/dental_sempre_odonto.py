# -*- coding: utf-8 -*-
"""Módulo GERAR DENTAL SEMPRE ODONTO.

Idêntico ao GERA PORTO DENTAL (decisão do usuário, 28/08/2026) — mesma
tela de duas etapas (consultar libera gerar), mesmo motor
(gerador_dental.py). As diferenças são só parâmetros:

- query 1 filtra AP.tipo_dental = 'S' em vez de 'P'
  (queries/sempreodonto_1.sql; a query 2 é idêntica);
- o nome SEMPRE ODONTO substitui PORTO no título, na aba e no arquivo
  gerado: sempreodonto-MMYYYY.xlsx.
"""
from modulos.porto_dental import JanelaPortoDental


class JanelaDentalSempreOdonto(JanelaPortoDental):
    TITULO = "GERAR DENTAL SEMPRE ODONTO — Consulta e Geração da Planilha"
    ARQUIVO_CONFIG = "sempre_odonto.json"
    QUERY_1 = "sempreodonto_1.sql"
    QUERY_2 = "sempreodonto_2.sql"
    PREFIXO_ARQUIVO = "sempreodonto"
    NOME_ABA = "SEMPRE ODONTO"
    # azul pastel para diferenciar do verde dos produtos Porto
    # (pedido do usuário, 28/08/2026)
    COR_BOTAO = "#7A9CC6"
    COR_BOTAO_HOVER = "#5F82AC"
