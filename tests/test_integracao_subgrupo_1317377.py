"""Teste de integração do robô de Vida com o Firebird real.

Execute explicitamente com:
    $env:PORTO_TESTE_INTEGRACAO = "1"
    python -m unittest discover -s tests -p test_integracao_subgrupo_1317377.py -v
"""
import os
import queue
import tempfile
import unittest
from datetime import date

from openpyxl import load_workbook

from modulos.subgrupos_vida import JanelaSubgruposVida


@unittest.skipUnless(
    os.environ.get("PORTO_TESTE_INTEGRACAO") == "1",
    "Defina PORTO_TESTE_INTEGRACAO=1 para autorizar o acesso ao Firebird.",
)
class TestGeracaoVidaSubgrupo1317377(unittest.TestCase):
    def test_robo_gera_subgrupo_na_vigencia_solicitada(self):
        janela = JanelaSubgruposVida.__new__(JanelaSubgruposVida)
        janela._fila_robo = queue.Queue()

        # Exercita o mesmo trabalhador chamado pelo botão do robô, mas limita
        # a execução ao subgrupo solicitado pelo usuário.
        with tempfile.TemporaryDirectory(prefix="teste_robo_vida_") as pasta:
            janela._executar_robo(
                date(2026, 9, 1), pasta, ["VIDA RJ [1317377]"]
            )

            gerados, vazios, erros, pasta_resultado = janela._fila_robo.get_nowait()
            self.assertEqual(pasta_resultado, pasta)
            caminho_log = os.path.join(pasta, "robo_log.txt")
            self.assertTrue(os.path.isfile(caminho_log), "O robô não criou o log.")
            with open(caminho_log, encoding="utf-8") as arquivo:
                log = arquivo.read()
            self.assertIn("Vigência: 01/09/2026", log)
            self.assertIn("VIDA RJ", log)
            self.assertEqual(erros, 0, f"O robô registrou erro:\n{log}")
            self.assertEqual(gerados + vazios, 1, f"Subgrupo não processado:\n{log}")

            if gerados:
                caminho_excel = os.path.join(
                    pasta, "Subgrupo_1317377_Relatorio_01-09-2026.xlsx"
                )
                self.assertTrue(os.path.isfile(caminho_excel))
                self.assertGreater(os.path.getsize(caminho_excel), 0)
                planilha = load_workbook(caminho_excel, read_only=True, data_only=True)
                try:
                    aba = planilha.active
                    cabecalhos = [celula.value for celula in next(aba.iter_rows(min_row=1, max_row=1))]
                    self.assertIn("APOLICE", cabecalhos)
                    self.assertIn("FATURA", cabecalhos)
                    self.assertGreater(aba.max_row, 1, "O arquivo foi criado sem linhas de dados.")
                finally:
                    planilha.close()
            else:
                self.assertEqual(vazios, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
