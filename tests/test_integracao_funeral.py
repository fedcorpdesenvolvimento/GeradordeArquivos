"""Teste de integração do ARQUIVO FUNERAL com o Firebird real (só leitura).

Execute explicitamente com:
    $env:PORTO_TESTE_INTEGRACAO = "1"
    python -m unittest discover -s tests -p test_integracao_funeral.py -v
"""
import datetime
import os
import tempfile
import unittest

from openpyxl import load_workbook

import db
from modulos import gerador_funeral as gf


@unittest.skipUnless(
    os.environ.get("PORTO_TESTE_INTEGRACAO") == "1",
    "Defina PORTO_TESTE_INTEGRACAO=1 para autorizar o acesso ao Firebird.",
)
class TestFuneralIntegracao(unittest.TestCase):
    def test_gera_para_vigencia_com_faturas(self):
        conn = db.conectar()
        try:
            cur = conn.cursor()
            # vigência mais recente com faturas de Vida ativas
            cur.execute("SELECT MAX(DT_INI_VIG) FROM FATURAS WHERE STATUS = 'A' AND RAMO = 'V' AND DT_INI_VIG <= CURRENT_DATE")
            inivig = cur.fetchone()[0]
        finally:
            conn.close()
        self.assertIsNotNone(inivig)

        mensagens = []
        with tempfile.TemporaryDirectory() as pasta:
            caminho, qtd = gf.gerar_planilha(pasta, inivig, log=lambda m, t=False: mensagens.append(m))
            self.assertIsNotNone(caminho, "\n".join(mensagens))
            self.assertGreater(qtd, 0)
            wb = load_workbook(caminho, read_only=True)
            linhas = list(wb.active.iter_rows(values_only=True))
            wb.close()  # senão o Windows não deixa apagar a pasta temporária
        self.assertEqual(list(linhas[0]), gf.COLUNAS)
        self.assertEqual(len(linhas) - 1, qtd)
        cpfs = [gf.normalizar_cpf(l[3]) for l in linhas[1:] if gf.normalizar_cpf(l[3])]
        self.assertEqual(len(cpfs), len(set(cpfs)), "CPF repetido na planilha")
        self.assertTrue(all(l[0] and l[1] and l[2] for l in linhas[1:]), "linha sem administradora/apólice/nome")
        nascimentos = [l[4] for l in linhas[1:] if l[4] is not None]
        self.assertTrue(all(isinstance(n, (datetime.date, datetime.datetime)) for n in nascimentos))
