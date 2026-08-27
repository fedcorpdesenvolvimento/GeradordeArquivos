# -*- coding: utf-8 -*-
"""Módulo GERA PORTO DENTAL — consulta e geração da planilha mensal.

Fluxo em duas etapas (ordem obrigatória, decisão do usuário 08/2026):

1. O usuário define a pasta de destino e a vigência (calendário
   pré-preenchido com o dia 01 do mês anterior, como nos demais módulos)
   e clica em CONSULTAR: a query 1 roda com :inivig e o log mostra as
   linhas retornadas e o TOTAL DE VIDAS a enviar.
2. Só depois da consulta o botão GERAR PLANILHA FINAL é liberado: a
   query 2 roda alimentada pelos números de fatura da query 1 e a
   planilha portodental-MMYYYY.xlsx é salva na pasta escolhida.

As escolhas ficam salvas em porto_dental.json. A consulta e a geração
rodam em thread para a janela não congelar; o log chega por queue
drenada pelo loop do Tk a cada 100 ms (mesmo padrão do Porto Assistência).
"""
import json
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkcalendar import DateEntry

from modulos import gerador_dental
from modulos.porto_assistencia import primeiro_dia_mes_anterior

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_JSON = os.path.join(BASE_DIR, "porto_dental.json")


class JanelaPortoDental(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("GERA PORTO DENTAL — Consulta e Geração da Planilha")
        self.geometry("720x620")
        self.attributes("-topmost", True)

        self.fila_log = queue.Queue()
        self._ultima_linha_transiente = False
        # resultado da etapa 1 (a etapa 2 usa exatamente o que foi consultado)
        self.faturas = []
        self.inivig_consultado = None

        self._montar_tela()
        self._carregar_config()
        self.after(100, self._drenar_log)

    # ---------- montagem da tela ----------
    def _montar_tela(self):
        # pasta de destino
        ctk.CTkLabel(self, text="Pasta onde salvar a planilha:",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 2))
        fr_pasta = ctk.CTkFrame(self)
        fr_pasta.pack(fill="x", padx=15)
        self.var_pasta = ctk.StringVar()
        ctk.CTkEntry(fr_pasta, textvariable=self.var_pasta).pack(
            side="left", fill="x", expand=True, padx=6, pady=6)
        ctk.CTkButton(fr_pasta, text="Procurar...", width=100,
                      command=self._escolher_pasta).pack(side="left", padx=6, pady=6)

        # vigencia (padrao: dia 01 do mes anterior, igual aos demais modulos)
        ctk.CTkLabel(self, text="Data de início de vigência (:inivig das queries):",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(12, 2))
        self.calendario = DateEntry(
            self, width=14,
            background='darkblue', foreground='white',
            date_pattern='dd/mm/yyyy',
            font=('Arial', 12), borderwidth=2, relief="solid")
        self.calendario.set_date(primeiro_dia_mes_anterior())
        self.calendario.pack(anchor="w", padx=15)

        # botoes das duas etapas
        fr_botoes = ctk.CTkFrame(self, fg_color="transparent")
        fr_botoes.pack(pady=12)
        self.btn_consultar = ctk.CTkButton(
            fr_botoes, text="1) Consultar Vidas", command=self._iniciar_consulta,
            fg_color="green", hover_color="darkgreen",
            font=("Arial", 14, "bold"), height=40, width=220)
        self.btn_consultar.pack(side="left", padx=8)
        # liberado somente depois de uma consulta bem-sucedida
        self.btn_gerar = ctk.CTkButton(
            fr_botoes, text="2) Gerar Planilha Final", command=self._iniciar_geracao,
            fg_color="green", hover_color="darkgreen",
            font=("Arial", 14, "bold"), height=40, width=220,
            state="disabled")
        self.btn_gerar.pack(side="left", padx=8)

        # log
        ctk.CTkLabel(self, text="Log:", font=("Arial", 14, "bold")).pack(
            anchor="w", padx=15)
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(2, 15))
        self.txt_log.configure(state="disabled")

    # ---------- config persistida ----------
    def _carregar_config(self):
        if not os.path.isfile(CONFIG_JSON):
            self.var_pasta.set(os.path.join(BASE_DIR, "saida"))
            return
        try:
            with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.var_pasta.set(cfg.get("pasta", os.path.join(BASE_DIR, "saida")))
        except Exception:
            pass  # config corrompida não impede o uso

    def _salvar_config(self):
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump({"pasta": self.var_pasta.get()}, f,
                      ensure_ascii=False, indent=2)

    # ---------- log thread-safe ----------
    def _log(self, msg, transiente=False):
        self.fila_log.put((msg, transiente))

    def _drenar_log(self):
        try:
            while True:
                msg, transiente = self.fila_log.get_nowait()
                if msg == "__consulta_ok__":
                    self.btn_consultar.configure(state="normal")
                    self.btn_gerar.configure(state="normal")
                    continue
                if msg == "__consulta_falhou__":
                    self.btn_consultar.configure(state="normal")
                    self.btn_gerar.configure(state="disabled")
                    continue
                if msg == "__fim_geracao__":
                    self.btn_consultar.configure(state="normal")
                    self.btn_gerar.configure(state="normal")
                    continue
                self.txt_log.configure(state="normal")
                if self._ultima_linha_transiente:
                    self.txt_log.delete("end-2l", "end-1l")
                self.txt_log.insert("end", msg + "\n")
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
                self._ultima_linha_transiente = transiente
        except queue.Empty:
            pass
        self.after(100, self._drenar_log)

    # ---------- ações ----------
    def _escolher_pasta(self):
        pasta = filedialog.askdirectory(
            initialdir=self.var_pasta.get() or BASE_DIR, parent=self)
        if pasta:
            self.var_pasta.set(pasta)

    def _validar_entradas(self):
        """Valida pasta e vigência; retorna (pasta, inivig) ou None."""
        pasta = self.var_pasta.get().strip()
        if not pasta:
            messagebox.showwarning("Atenção", "Informe a pasta de destino.",
                                   parent=self)
            return None
        try:
            inivig = self.calendario.get_date()
        except Exception:
            messagebox.showwarning(
                "Atenção", "Data de início de vigência inválida.", parent=self)
            return None
        return pasta, inivig

    def _iniciar_consulta(self):
        entradas = self._validar_entradas()
        if not entradas:
            return
        _, inivig = entradas
        self._salvar_config()
        # nova consulta invalida o resultado anterior até terminar
        self.faturas = []
        self.inivig_consultado = None
        self.btn_consultar.configure(state="disabled")
        self.btn_gerar.configure(state="disabled")
        self._log("=" * 60)
        self._log(f"Consultando vidas — vigência {inivig.strftime('%d/%m/%Y')}...")
        threading.Thread(target=self._trabalho_consulta, args=(inivig,),
                         daemon=True).start()

    def _trabalho_consulta(self, inivig):
        try:
            faturas, total_vidas = gerador_dental.consultar_faturas(
                inivig, log=self._log)
            self.faturas = faturas
            self.inivig_consultado = inivig
            self._log(f"Faturas encontradas: {len(faturas)}")
            self._log(f"TOTAL DE VIDAS A ENVIAR: {total_vidas}")
            if faturas:
                self._log("Consulta concluída — o botão 2) Gerar Planilha "
                          "Final foi liberado.")
                self.fila_log.put(("__consulta_ok__", False))
            else:
                self._log("Nenhuma fatura na vigência — nada a gerar.")
                self.fila_log.put(("__consulta_falhou__", False))
        except Exception as e:
            self._log(f"[ERRO] {e}")
            self.fila_log.put(("__consulta_falhou__", False))

    def _iniciar_geracao(self):
        entradas = self._validar_entradas()
        if not entradas:
            return
        pasta, _ = entradas
        if not self.faturas or self.inivig_consultado is None:
            messagebox.showwarning(
                "Atenção", "Rode a consulta (etapa 1) antes de gerar.",
                parent=self)
            return
        self._salvar_config()
        self.btn_consultar.configure(state="disabled")
        self.btn_gerar.configure(state="disabled")
        self._log("-" * 60)
        self._log(f"Gerando planilha final — vigência "
                  f"{self.inivig_consultado.strftime('%d/%m/%Y')} "
                  f"({len(self.faturas)} faturas)...")
        threading.Thread(
            target=self._trabalho_geracao,
            args=(pasta, self.inivig_consultado, list(self.faturas)),
            daemon=True).start()

    def _trabalho_geracao(self, pasta, inivig, faturas):
        try:
            caminho, linhas = gerador_dental.gerar_planilha(
                pasta, inivig, faturas, log=self._log)
            self._log(f"Concluído: {linhas} linhas em {caminho}")
        except Exception as e:
            self._log(f"[ERRO] {e}")
        finally:
            self.fila_log.put(("__fim_geracao__", False))
