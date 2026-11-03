"""Teste de integração da COBERTURA PROVISÓRIA (fatura 99) com o Firebird real.

Execute explicitamente com:
    $env:PORTO_TESTE_INTEGRACAO = "1"
    python -m unittest discover -s tests -p test_integracao_cobertura_provisoria.py -v

O teste descobre no banco a vigência mais recente que tem coberturas
provisórias (FATURA IS NULL em VIDA_COBERTURA_PROV) para as apólices do
subgrupo 1317377 e gera o DataFrame só desse subgrupo. Escreve nas tabelas
TEMP_* e marca/desmarca a fatura 99 exatamente como a geração normal.
"""
import os
import unittest

import customtkinter as ctk
import pandas as pd

import db
from modulos.subgrupos_vida import JanelaSubgruposVida

SUBGRUPO = "1317377"
NOME_SUBGRUPO = "VIDA RJ"


def _residuos_99(cur):
    r = {}
    for t in ("VIDA_COBERTURA_PROV", "VIDA_SEGURADOS_MOV", "VIDA_SEGURADO_FIN"):
        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE FATURA = 99")
        r[t] = cur.fetchone()[0]
    return r


@unittest.skipUnless(
    os.environ.get("PORTO_TESTE_INTEGRACAO") == "1",
    "Defina PORTO_TESTE_INTEGRACAO=1 para autorizar o acesso ao Firebird.",
)
class TestCoberturaProvisoria1317377(unittest.TestCase):
    def test_provisorios_entram_na_planilha_e_nao_sobra_99(self):
        conn = db.conectar()
        cur = conn.cursor()
        try:
            self.assertEqual(set(_residuos_99(cur).values()), {0}, "já havia fatura 99 residual antes do teste")

            # vigência mais recente com provisórios do subgrupo e quantos
            # segurados têm financeiro (só esses saem da procedure 99)
            cur.execute("""
                SELECT FIRST 1 P.DT_INI_COBERT, COUNT(*)
                FROM VIDA_COBERTURA_PROV P
                WHERE P.FATURA IS NULL
                  AND P.APOLICE IN (SELECT DISTINCT A.APOLICE FROM APOLICES A WHERE A.SUBPORTO = ?)
                GROUP BY P.DT_INI_COBERT
                ORDER BY P.DT_INI_COBERT DESC
            """, (SUBGRUPO,))
            linha = cur.fetchone()
            if not linha:
                self.skipTest("Não há cobertura provisória pendente para o subgrupo 1317377 no momento.")
            vigencia, qtd_prov = linha
            cur.execute("""
                SELECT COUNT(*) FROM VIDA_COBERTURA_PROV P
                WHERE P.FATURA IS NULL AND P.DT_INI_COBERT = ?
                  AND P.APOLICE IN (SELECT DISTINCT A.APOLICE FROM APOLICES A WHERE A.SUBPORTO = ?)
                  AND EXISTS (SELECT 1 FROM VIDA_SEGURADO_FIN F
                              WHERE F.FATURA = 0 AND F.ADMINISTRADORA = P.ADMINISTRADORA
                                AND F.POSTO = P.POSTO AND F.SEQ_POSTO = P.SEQ_POSTO
                                AND F.MATRICULA = P.MATRICULA AND F.SEQ_MAT = P.SEQ_MAT
                                AND F.APOLICE = P.APOLICE AND F.SEQ = P.SEQ)
            """, (vigencia, SUBGRUPO))
            esperados = cur.fetchone()[0]

            root = ctk.CTk()
            root.withdraw()
            janela = JanelaSubgruposVida(root)
            janela.withdraw()
            try:
                df, id_sub = janela._montar_dataframe(conn, vigencia.strftime("%m/%d/%Y"), [f"{NOME_SUBGRUPO} [{SUBGRUPO}]"])
                aviso = janela.ultimo_aviso
            finally:
                root.destroy()

            self.assertEqual(id_sub, SUBGRUPO)
            self.assertIsNone(aviso, f"a cobertura provisória falhou: {aviso}")

            prov = df[pd.to_numeric(df["FATURA"], errors="coerce") == JanelaSubgruposVida.FATURA_COB_PROV]
            self.assertEqual(len(prov), esperados,
                             f"vigência {vigencia:%d/%m/%Y}: {qtd_prov} provisórios, {esperados} com financeiro, "
                             f"{len(prov)} na planilha")
            self.assertGreater(len(prov), 0)
            self.assertTrue(prov["DT_INI_VIG"].notna().all(), "DT_INI_VIG vazia nos provisórios (complemento 3b)")
            self.assertTrue(prov["DT_FIM_VIG"].notna().all(), "DT_FIM_VIG vazia nos provisórios (complemento 3b)")
            self.assertTrue((prov["SUBPORTO"].astype(str) == SUBGRUPO).all())
            self.assertEqual((prov["DT_INI_VIG"] == vigencia.strftime("%d/%m/%Y")).all(), True)

            self.assertEqual(set(_residuos_99(cur).values()), {0}, "sobrou fatura 99 no banco depois da geração")
        finally:
            conn.close()
