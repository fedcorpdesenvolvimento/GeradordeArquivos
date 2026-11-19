"""Testes do gerador PORTO ASSISTÊNCIA em CSV (sem banco): banco simulado.
Layout do modelo da Porto de 19/11/2026 (status, codigoPlano, inicioVigencia,
finalVigencia, tipoDocumento, documento, cpfCnpj, nome, nomeSocial)."""
import csv
import datetime
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("FB_HOST", "x"); os.environ.setdefault("FB_DATABASE", "x")
os.environ.setdefault("FB_USER", "x"); os.environ.setdefault("FB_PASSWORD", "x")
os.environ.setdefault("SFTP_USER", "x"); os.environ.setdefault("SFTP_PASSWORD", "x")

from modulos import gerador_porto as gp  # noqa: E402

# A query devolve as colunas do layout antigo, fora de ordem: só NOME e CPF_CNPJ importam.
COLS_QUERY = ["APOLICE", "ENDERECO", "NOME", "CEP", "CPF_CNPJ", "DATANASCIMENTO",
              "NOMEINQUILINO", "CPFCNPJINQUILINO"]


def linha(nome, cpf):
    return ("4803", "RUA X", nome, "01234-567", cpf, datetime.date(1980, 1, 1), "", None)


class CursorFalso:
    def __init__(self, linhas, cols=COLS_QUERY):
        self.description = [(c,) for c in cols]
        self._linhas = list(linhas)

    def execute(self, sql, params):
        assert ":inivig" not in sql and sql.count("?") == len(params)

    def fetchmany(self, n):
        bloco, self._linhas = self._linhas[:n], self._linhas[n:]
        return bloco

    def close(self):
        pass


class ConexaoFalsa:
    """Cada cursor devolve as linhas da próxima query."""

    def __init__(self, por_query):
        self.por_query = list(por_query)
        self.fechada = False

    def cursor(self):
        return CursorFalso(self.por_query.pop(0))

    def close(self):
        self.fechada = True


class FuncoesTests(unittest.TestCase):
    def test_nome_do_arquivo_sem_espacos_nem_tracos(self):
        nome = gp.nome_arquivo(datetime.date(2026, 10, 1))
        self.assertEqual(nome, "relacaoenvioporto102026.csv")
        self.assertNotRegex(nome, r"[ \-]")

    def test_fim_de_vigencia_um_ano_depois(self):
        self.assertEqual(gp.fim_vigencia(datetime.date(2026, 11, 4)), datetime.date(2027, 11, 4))
        self.assertEqual(gp.fim_vigencia(datetime.date(2028, 2, 29)), datetime.date(2029, 2, 28))

    def test_documento_cpf_cnpj_e_vazios(self):
        self.assertEqual(gp.documento("111.655.777-04"), ("CPF", "11165577704"))
        self.assertEqual(gp.documento("9599845773"), ("CPF", "09599845773"))   # zero perdido no banco
        self.assertEqual(gp.documento("12.345.678/0001-99"), ("CNPJ", "12345678000199"))
        self.assertEqual(gp.documento("2345678000199"), ("CNPJ", "02345678000199"))
        self.assertEqual(gp.documento(None), ("", ""))
        self.assertEqual(gp.documento("000"), ("", ""))

    def test_montar_linha(self):
        l = gp.montar_linha(2, " ERIKA LORENA ", "11165577704", datetime.date(2026, 11, 4))
        self.assertEqual(l, ["A", "2", "04/11/2026", "04/11/2027", "CPF",
                             "11165577704", "11165577704", "ERIKA LORENA", "ERIKA LORENA"])


class GeradorCsvTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.inivig = datetime.date(2026, 10, 1)

    def tearDown(self):
        self.pasta.cleanup()

    def _gerar(self, por_query, selecao):
        con = ConexaoFalsa(por_query)
        with mock.patch.object(gp.db, "conectar", return_value=con), \
             mock.patch.object(gp, "carregar_query", return_value="select 1 where d = :inivig"):
            caminho, resultado = gp.gerar_planilha(self.pasta.name, self.inivig, selecao,
                                                   log=lambda *a, **k: None)
        self.assertTrue(con.fechada)
        return caminho, resultado

    def _ler(self, caminho):
        with open(caminho, encoding="cp1252", newline="") as f:
            return list(csv.reader(f, delimiter=";"))

    def test_arquivo_unico_no_layout_da_porto(self):
        por_query = [[linha("ANA Ç", "11165577704"), linha("BIA", "23081740720")],  # Residencial q1
                     [linha("CARLA", "9599845773")],                               # Residencial q2
                     [linha("EMPRESA LTDA", "12345678000199")],                    # Auto
                     [linha("DUDA; FILHA", None), linha("EDU", "5483859715")]]     # Empresarial
        caminho, resultado = self._gerar(por_query, {1: None, 2: None, 3: None})
        self.assertEqual(os.path.basename(caminho), "relacaoenvioporto102026.csv")
        self.assertEqual(resultado, {1: 3, 2: 1, 3: 2})
        linhas = self._ler(caminho)
        self.assertEqual(linhas[0], gp.CABECALHO)
        self.assertEqual(len(linhas), 1 + 6)
        self.assertEqual([l[1] for l in linhas[1:]], ["1", "1", "1", "2", "3", "3"])
        self.assertTrue(all(l[0] == "A" for l in linhas[1:]))
        self.assertTrue(all(l[2] == "01/10/2026" and l[3] == "01/10/2027" for l in linhas[1:]))
        self.assertEqual(linhas[1][4:], ["CPF", "11165577704", "11165577704", "ANA Ç", "ANA Ç"])
        self.assertEqual(linhas[3][5], "09599845773")
        self.assertEqual(linhas[4][4:7], ["CNPJ", "12345678000199", "12345678000199"])
        self.assertEqual(linhas[5][4:9], ["", "", "", "DUDA; FILHA", "DUDA; FILHA"])

    def test_bytes_em_windows_1252_e_ponto_e_virgula_entre_aspas(self):
        caminho, _ = self._gerar([[linha("ANA Ç", "1"), linha("DUDA; FILHA", "2")]], {2: None})
        with open(caminho, "rb") as f:
            bruto = f.read()
        self.assertTrue(bruto.startswith(b"status;codigoPlano;inicioVigencia;"))
        self.assertIn("ANA Ç".encode("cp1252"), bruto)
        self.assertIn(b'"DUDA; FILHA"', bruto)

    def test_limite_vale_para_a_soma_das_queries(self):
        por_query = [[linha(f"N{n}", str(n + 1)) for n in range(5)], [linha("N9", "9")]]
        caminho, resultado = self._gerar(por_query, {1: 3})
        self.assertEqual(resultado, {1: 3})
        self.assertEqual(len(self._ler(caminho)), 4)

    def test_mesmo_documento_no_mesmo_produto_sai_uma_vez(self):
        por_query = [[linha("ANA", "111.655.777-04"), linha("BIA", "23081740720"),
                      linha("ANA DE NOVO", "11165577704")],
                     [linha("ANA NA 15008", "11165577704"), linha("SEM DOC 1", None),
                      linha("SEM DOC 2", "")],
                     [linha("ANA NO AUTO", "11165577704")]]
        caminho, resultado = self._gerar(por_query, {1: None, 2: None})
        self.assertEqual(resultado, {1: 4, 2: 1})   # ANA uma vez no 1; sem documento todas ficam
        nomes = [(l[1], l[7]) for l in self._ler(caminho)[1:]]
        self.assertEqual(nomes, [("1", "ANA"), ("1", "BIA"), ("1", "SEM DOC 1"), ("1", "SEM DOC 2"),
                                 ("2", "ANA NO AUTO")])   # outro produto pode repetir

    def test_limite_conta_linhas_gravadas_e_nao_duplicadas(self):
        por_query = [[linha("A", "1"), linha("A2", "1"), linha("B", "2"), linha("C", "3")], []]
        caminho, resultado = self._gerar(por_query, {1: 3})
        self.assertEqual(resultado, {1: 3})
        self.assertEqual([l[7] for l in self._ler(caminho)[1:]], ["A", "B", "C"])

    def test_sem_selecao_recusa(self):
        with self.assertRaises(ValueError):
            gp.gerar_planilha(self.pasta.name, self.inivig, {})

    def test_coluna_faltando_na_query_e_erro_claro(self):
        con = ConexaoFalsa([[]])
        con.cursor = lambda: CursorFalso([], cols=[c for c in COLS_QUERY if c != "CPF_CNPJ"])
        with mock.patch.object(gp.db, "conectar", return_value=con), \
             mock.patch.object(gp, "carregar_query", return_value="select 1"):
            with self.assertRaisesRegex(RuntimeError, "CPF_CNPJ"):
                gp.gerar_planilha(self.pasta.name, self.inivig, {2: None}, log=lambda *a, **k: None)


if __name__ == "__main__":
    unittest.main()
