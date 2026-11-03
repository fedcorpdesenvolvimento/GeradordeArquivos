import os
import queue
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from modulos.subgrupos_vida import JanelaSubgruposVida


class WidgetFalso:
    def __init__(self):
        self.config = {}
        self.destroyed = False

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def destroy(self):
        self.destroyed = True


class CheckboxFalso:
    def __init__(self, texto):
        self.texto = texto

    def cget(self, chave):
        assert chave == "text"
        return self.texto


class ConexaoFalsa:
    def __init__(self):
        self.closed = False
        self.rollbacks = 0

    def close(self):
        self.closed = True

    def rollback(self):
        self.rollbacks += 1


class DataFrameFalso:
    empty = False
    columns = []

    def __init__(self, linhas=2):
        self.linhas = linhas

    def __len__(self):
        return self.linhas

    def to_excel(self, caminho, index=False):
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write("planilha")


class AgendadorSubgruposVidaTests(unittest.TestCase):
    def setUp(self):
        self.janela = JanelaSubgruposVida.__new__(JanelaSubgruposVida)
        self.janela.checkboxes = [
            CheckboxFalso("Vida A [101]"), CheckboxFalso("Vida B [202]"),
            CheckboxFalso("Vida C [303]"),
        ]
        self.janela._id_after_robo = None
        self.janela._robo_rodando = False
        self.janela._fila_robo = queue.Queue()
        self.janela._janela_agendador = None
        self.janela.lbl_status_robo = WidgetFalso()
        self.janela.btn_gerar = WidgetFalso()
        self.janela.btn_ver_tela = WidgetFalso()
        self.janela.btn_robo = WidgetFalso()
        self.janela.agendamentos = []
        self.janela.after = lambda atraso, callback: self.janela.agendamentos.append((atraso, callback)) or "after-1"
        self.janela.after_cancel = lambda identificador: setattr(self.janela, "cancelado", identificador)

    @patch("modulos.subgrupos_vida.os.path.isdir", return_value=True)
    @patch("modulos.subgrupos_vida.messagebox.showinfo")
    def test_executar_agora_agenda_todos_os_subgrupos(self, _info, _isdir):
        dialogo = WidgetFalso()
        self.janela._agendar_robo("07/10/2026", "destino", None, dialogo)

        atraso, callback = self.janela.agendamentos[0]
        self.assertEqual(atraso, 0)
        self.assertEqual(self.janela._id_after_robo, "after-1")
        self.assertTrue(dialogo.destroyed)
        # A callback mantém a lista completa, sem depender das caixas marcadas.
        with patch.object(self.janela, "_iniciar_robo") as iniciar:
            callback()
        iniciar.assert_called_once()
        nomes = iniciar.call_args.args[2]
        self.assertEqual(nomes, ["Vida A [101]", "Vida B [202]", "Vida C [303]"])

    @patch("modulos.subgrupos_vida.messagebox.showerror")
    def test_rejeita_data_invalida_sem_agendar(self, erro):
        self.janela._agendar_robo("31/02/2026", "destino", None, WidgetFalso())
        erro.assert_called_once()
        self.assertEqual(self.janela.agendamentos, [])

    @patch("modulos.subgrupos_vida.os.path.isdir", return_value=False)
    @patch("modulos.subgrupos_vida.messagebox.showerror")
    def test_rejeita_pasta_invalida(self, erro, _isdir):
        self.janela._agendar_robo("07/10/2026", "inexistente", None, WidgetFalso())
        erro.assert_called_once()
        self.assertEqual(self.janela.agendamentos, [])

    @patch("modulos.subgrupos_vida.os.path.isdir", return_value=True)
    @patch("modulos.subgrupos_vida.messagebox.showerror")
    def test_rejeita_horario_invalido(self, erro, _isdir):
        self.janela._agendar_robo("07/10/2026", "destino", "25:90", WidgetFalso())
        erro.assert_called_once()
        self.assertEqual(self.janela.agendamentos, [])

    @patch("modulos.subgrupos_vida.messagebox.showinfo")
    def test_cancelamento_sem_agendamento(self, info):
        self.janela._cancelar_robo()
        info.assert_called_once()

    @patch("modulos.subgrupos_vida.messagebox.showinfo")
    def test_cancelamento_de_agendamento_ativo(self, _info):
        self.janela._id_after_robo = "after-ativo"
        self.janela._cancelar_robo()
        self.assertEqual(self.janela.cancelado, "after-ativo")
        self.assertIsNone(self.janela._id_after_robo)
        self.assertEqual(self.janela.lbl_status_robo.config["text"], "Agendamento cancelado.")

    @patch("modulos.subgrupos_vida.db.conectar")
    def test_execucao_processa_todos_registra_log_e_fecha_conexao(self, conectar):
        conectar.return_value = ConexaoFalsa()
        self.janela._montar_dataframe = lambda conn, data, nomes: (DataFrameFalso(), nomes[0].split("[")[0].strip()[-1])
        with tempfile.TemporaryDirectory() as pasta:
            nomes = ["Vida A [101]", "Vida B [202]", "Vida C [303]"]
            self.janela._executar_robo(date(2026, 10, 7), pasta, nomes)

            self.assertEqual(sorted(os.listdir(pasta)), [
                "Subgrupo_A_Relatorio_07-10-2026.xlsx",
                "Subgrupo_B_Relatorio_07-10-2026.xlsx",
                "Subgrupo_C_Relatorio_07-10-2026.xlsx",
                "robo_log.txt",
            ])
            self.assertEqual(self.janela._fila_robo.get_nowait(), (3, 0, 0, pasta))
            with open(os.path.join(pasta, "robo_log.txt"), encoding="utf-8") as arquivo:
                log = arquivo.read()
            for nome in ("Vida A", "Vida B", "Vida C"):
                self.assertIn(nome, log)
        self.assertTrue(conectar.return_value.closed)

    @patch("modulos.subgrupos_vida.db.conectar", side_effect=RuntimeError("banco indisponível"))
    def test_falha_de_conexao_e_reportada_na_fila_e_log(self, _conectar):
        with tempfile.TemporaryDirectory() as pasta:
            self.janela._executar_robo(date(2026, 10, 7), pasta, ["Vida A [101]"])
            self.assertEqual(self.janela._fila_robo.get_nowait(), (0, 0, 1, pasta))
            with open(os.path.join(pasta, "robo_log.txt"), encoding="utf-8") as arquivo:
                self.assertIn("banco indisponível", arquivo.read())

    @patch("modulos.subgrupos_vida.messagebox.showinfo")
    def test_resultado_reabilita_botoes(self, _info):
        self.janela._robo_rodando = True
        self.janela._finalizar_robo(2, 1, 0, "destino")
        self.assertFalse(self.janela._robo_rodando)
        for botao in (self.janela.btn_gerar, self.janela.btn_ver_tela, self.janela.btn_robo):
            self.assertEqual(botao.config["state"], "normal")
        self.assertEqual(self.janela.lbl_status_robo.config["text_color"], "green")


if __name__ == "__main__":
    unittest.main()





