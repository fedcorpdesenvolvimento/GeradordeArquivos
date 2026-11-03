"""Testes unitários do gerador FUNERAL (sem banco)."""
import datetime
import os
import tempfile
import unittest

from openpyxl import load_workbook

from modulos import gerador_funeral as gf


class NormalizarCpfTests(unittest.TestCase):
    def test_remove_mascara_e_trata_vazios(self):
        self.assertEqual(gf.normalizar_cpf("123.456.789-01"), "12345678901")
        self.assertEqual(gf.normalizar_cpf(" 12345678901 "), "12345678901")
        self.assertEqual(gf.normalizar_cpf(None), "")
        self.assertEqual(gf.normalizar_cpf(""), "")
        self.assertEqual(gf.normalizar_cpf("0"), "")
        self.assertEqual(gf.normalizar_cpf("000"), "")
        self.assertEqual(gf.normalizar_cpf("5648163452"), "05648163452")   # zero à esquerda perdido no banco
        self.assertEqual(gf.normalizar_cpf("12345678000199"), "12345678000199")
        self.assertEqual(gf.normalizar_cpf("2345678000199"), "02345678000199")


class DuplicidadeTests(unittest.TestCase):
    def test_mantem_primeira_ocorrencia_e_conta_removidas(self):
        linhas = [
            ("ADM A", "4803", "JOAO", "12345678901", datetime.date(1980, 1, 1)),
            ("ADM B", "6800", "JOAO", "123.456.789-01", datetime.date(1980, 1, 1)),
            ("ADM A", "4803", "MARIA", "98765432100", datetime.date(1990, 2, 2)),
            ("ADM D", "4803", "MARIA DE NOVO", "098765432100"[1:], datetime.date(1990, 2, 2)),
            ("ADM C", "301", "SEM CPF 1", "", None),
            ("ADM C", "301", "SEM CPF 2", None, None),
        ]
        saida, removidas = gf.remover_duplicidade_cpf(linhas)
        self.assertEqual(removidas, 2)
        self.assertEqual([l[2] for l in saida], ["JOAO", "MARIA", "SEM CPF 1", "SEM CPF 2"])
        self.assertEqual(saida[0][0], "ADM A")  # a primeira ocorrência é a mantida


class PlanilhaTests(unittest.TestCase):
    def test_grava_colunas_nome_do_arquivo_e_datas(self):
        linhas = [("ADM A ", "4803", " JOAO ", "123.456.789-01", datetime.date(1980, 1, 31))]
        with tempfile.TemporaryDirectory() as pasta:
            caminho = gf.gravar_planilha(pasta, datetime.date(2026, 10, 1), linhas)
            self.assertEqual(os.path.basename(caminho), "funeral-102026.xlsx")
            ws = load_workbook(caminho).active
            self.assertEqual(ws.title, "FUNERAL")
            self.assertEqual([c.value for c in ws[1]], gf.COLUNAS)
            self.assertEqual([c.value for c in ws[2]][:4], ["ADM A", "4803", "JOAO", "12345678901"])
            self.assertEqual(ws.cell(row=2, column=5).value, datetime.datetime(1980, 1, 31))
            self.assertEqual(ws.cell(row=2, column=5).number_format, "DD/MM/YYYY")


class ParametrosTests(unittest.TestCase):
    def test_troca_todas_as_ocorrencias_de_inivig(self):
        sql, params = gf._preparar_parametros("a = :inivig or b between :inivig and c", datetime.date(2026, 10, 1))
        self.assertEqual(sql, "a = ? or b between ? and c")
        self.assertEqual(params, [datetime.date(2026, 10, 1)] * 2)


if __name__ == "__main__":
    unittest.main()
