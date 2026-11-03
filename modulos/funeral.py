# -*- coding: utf-8 -*-
"""Módulo GERAR ARQUIVO FUNERAL — tela.

Uma etapa só: o usuário escolhe a pasta e a data de início de vigência
(calendário pré-preenchido com o dia 01 do mês anterior) e clica em
GERAR. A geração roda em thread (modulos/gerador_funeral.py) e o log
chega por queue drenada pelo loop do Tk a cada 100 ms — mesmo padrão do
Porto Dental. A pasta fica salva em funeral.json.
"""
import json
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkcalendar import DateEntry

from modulos import gerador_funeral
from modulos.porto_assistencia import primeiro_dia_mes_anterior

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class JanelaFuneral(ctk.CTkToplevel):
    TITULO = "GERAR ARQUIVO FUNERAL"
    ARQUIVO_CONFIG = "funeral.json"
    COR_BOTAO = "green"
    COR_BOTAO_HOVER = "darkgreen"

    def __init__(self, master):
        super().__init__(master)
        self.config_json = os.path.join(BASE_DIR, self.ARQUIVO_CONFIG)
        self.title(self.TITULO)
        self.geometry("720x560")
        self.attributes("-topmost", True)

        self.fila_log = queue.Queue()
        self._montar_tela()
        self._carregar_config()
        self.after(100, self._drenar_log)

    # ---------- tela ----------
    def _montar_tela(self):
        ctk.CTkLabel(self, text="Segurados de Vida com cobertura FUNERAL ou CERIMONIAL",
                     font=("Arial", 16, "bold")).pack(pady=(15, 2))
        ctk.CTkLabel(self, text="Faturas ativas na vigência (inclui apólices anuais em curso). "
                               "Colunas: administradora, apólice, nome, CPF, nascimento. CPF sem repetição.",
                     font=("Arial", 11), text_color="gray").pack()

        ctk.CTkLabel(self, text="Pasta onde salvar a planilha:",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 2))
        fr_pasta = ctk.CTkFrame(self)
        fr_pasta.pack(fill="x", padx=15)
        self.var_pasta = ctk.StringVar()
        ctk.CTkEntry(fr_pasta, textvariable=self.var_pasta).pack(
            side="left", fill="x", expand=True, padx=6, pady=6)
        ctk.CTkButton(fr_pasta, text="Procurar...", width=100,
                      command=self._escolher_pasta).pack(side="left", padx=6, pady=6)

        ctk.CTkLabel(self, text="Data de início de vigência:",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(12, 2))
        self.calendario = DateEntry(
            self, width=14, background='darkblue', foreground='white',
            date_pattern='dd/mm/yyyy', font=('Arial', 12), borderwidth=2, relief="solid")
        self.calendario.set_date(primeiro_dia_mes_anterior())
        self.calendario.pack(anchor="w", padx=15)

        self.btn_gerar = ctk.CTkButton(
            self, text="Gerar Arquivo Funeral", command=self._iniciar_geracao,
            fg_color=self.COR_BOTAO, hover_color=self.COR_BOTAO_HOVER,
            font=("Arial", 14, "bold"), height=40, width=260)
        self.btn_gerar.pack(pady=12)

        ctk.CTkLabel(self, text="Log:", font=("Arial", 14, "bold")).pack(anchor="w", padx=15)
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(2, 15))
        self.txt_log.configure(state="disabled")

    # ---------- config ----------
    def _carregar_config(self):
        padrao = os.path.join(BASE_DIR, "saida")
        try:
            with open(self.config_json, "r", encoding="utf-8") as f:
                self.var_pasta.set(json.load(f).get("pasta", padrao))
        except Exception:
            self.var_pasta.set(padrao)

    def _salvar_config(self):
        try:
            with open(self.config_json, "w", encoding="utf-8") as f:
                json.dump({"pasta": self.var_pasta.get()}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- log thread-safe ----------
    def _log(self, msg, transiente=False):
        self.fila_log.put(msg)

    def _drenar_log(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                msg = self.fila_log.get_nowait()
                if msg == "__fim__":
                    self.btn_gerar.configure(state="normal")
                    continue
                self.txt_log.configure(state="normal")
                self.txt_log.insert("end", msg + "\n")
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drenar_log)

    # ---------- ações ----------
    def _escolher_pasta(self):
        pasta = filedialog.askdirectory(initialdir=self.var_pasta.get() or BASE_DIR, parent=self)
        if pasta:
            self.var_pasta.set(pasta)

    def _iniciar_geracao(self):
        pasta = self.var_pasta.get().strip()
        if not pasta:
            messagebox.showwarning("Atenção", "Informe a pasta de destino.", parent=self)
            return
        try:
            inivig = self.calendario.get_date()
        except Exception:
            messagebox.showwarning("Atenção", "Data de início de vigência inválida.", parent=self)
            return
        self._salvar_config()
        self.btn_gerar.configure(state="disabled")
        self._log("=" * 60)
        threading.Thread(target=self._trabalho, args=(pasta, inivig), daemon=True).start()

    def _trabalho(self, pasta, inivig):
        try:
            caminho, linhas = gerador_funeral.gerar_planilha(pasta, inivig, log=self._log)
            if caminho:
                self._log(f"Concluído: {linhas} segurados em {caminho}")
        except Exception as e:
            self._log(f"[ERRO] {e}")
        finally:
            self.fila_log.put("__fim__")
