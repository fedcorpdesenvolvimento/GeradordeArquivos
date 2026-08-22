# -*- coding: utf-8 -*-
"""Módulo PORTO ASSISTÊNCIA — geração e envio da relação mensal à Porto.

Tela única: pasta de destino, data de início de vigência (pré-preenchida
com o dia 01 do mês anterior, editável), seleção por produto (base toda ou
quantidade específica de linhas), envio opcional por SFTP e log em tela com
o total de linhas geradas por produto. As escolhas ficam salvas em
porto_assistencia.json e voltam preenchidas na próxima abertura.

A data alimenta o parâmetro :inivig das queries e define a competência do
nome do arquivo (relacao-envio-porto-MMYYYY.xlsx).

A geração roda em thread separada para a janela não congelar; o log chega
por uma fila (queue) drenada pelo loop do Tk a cada 100 ms.
"""
import datetime
import json
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkcalendar import DateEntry

from modulos import gerador_porto
from modulos.envio_sftp import enviar_arquivo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_JSON = os.path.join(BASE_DIR, "porto_assistencia.json")


def primeiro_dia_mes_anterior() -> datetime.date:
    """Dia 01 do mês anterior à data de hoje (padrão da vigência)."""
    hoje = datetime.date.today()
    primeiro_deste_mes = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_deste_mes - datetime.timedelta(days=1)
    return ultimo_dia_mes_anterior.replace(day=1)


class JanelaPortoAssistencia(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("PORTO ASSISTÊNCIA — Geração e Envio da Relação")
        self.geometry("720x680")
        self.attributes("-topmost", True)

        self.fila_log = queue.Queue()
        self._ultima_linha_transiente = False
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

        # data de inicio de vigencia (padrao: dia 01 do mes anterior)
        ctk.CTkLabel(self, text="Data de início de vigência (:inivig das queries):",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(12, 2))
        self.calendario = DateEntry(
            self, width=14,
            background='darkblue', foreground='white',
            date_pattern='dd/mm/yyyy',
            font=('Arial', 12), borderwidth=2, relief="solid")
        self.calendario.set_date(primeiro_dia_mes_anterior())
        self.calendario.pack(anchor="w", padx=15)

        # produtos
        ctk.CTkLabel(self, text="Produtos:",
                     font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(12, 2))
        fr_prod = ctk.CTkFrame(self)
        fr_prod.pack(fill="x", padx=15)
        self.linhas_produto = {}
        for prod in gerador_porto.PRODUTOS:
            linha = ctk.CTkFrame(fr_prod, fg_color="transparent")
            linha.pack(fill="x", pady=4, padx=6)
            var_incluir = ctk.BooleanVar(value=True)
            var_modo = ctk.StringVar(value="toda")     # toda | quantidade
            var_qtd = ctk.StringVar(value="10000")
            ctk.CTkCheckBox(
                linha, text=f"Código {prod['codigo']} - {prod['nome']}",
                variable=var_incluir, width=220).pack(side="left")
            ctk.CTkRadioButton(linha, text="Base toda", value="toda",
                               variable=var_modo, width=110).pack(side="left")
            ctk.CTkRadioButton(linha, text="Quantidade:", value="quantidade",
                               variable=var_modo, width=110).pack(side="left")
            ctk.CTkEntry(linha, textvariable=var_qtd, width=90).pack(side="left")
            ctk.CTkLabel(linha, text=" linhas").pack(side="left")
            self.linhas_produto[prod["codigo"]] = (var_incluir, var_modo, var_qtd)

        # envio
        self.var_enviar = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self, text="Enviar para a Porto (SFTP /Porto/Remessa) após gerar",
            variable=self.var_enviar).pack(anchor="w", padx=15, pady=(12, 0))

        # botao
        self.btn_gerar = ctk.CTkButton(
            self, text="Gerar Planilha", command=self._iniciar_geracao,
            fg_color="green", hover_color="darkgreen",
            font=("Arial", 14, "bold"), height=40)
        self.btn_gerar.pack(pady=12)

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
            self.var_enviar.set(cfg.get("enviar", False))
            for codigo, valores in cfg.get("produtos", {}).items():
                trio = self.linhas_produto.get(int(codigo))
                if trio:
                    trio[0].set(valores.get("incluir", True))
                    trio[1].set(valores.get("modo", "toda"))
                    trio[2].set(str(valores.get("quantidade", "10000")))
        except Exception:
            pass  # config corrompida não impede o uso

    def _salvar_config(self):
        cfg = {
            "pasta": self.var_pasta.get(),
            "enviar": self.var_enviar.get(),
            "produtos": {
                str(c): {"incluir": v[0].get(), "modo": v[1].get(),
                          "quantidade": v[2].get()}
                for c, v in self.linhas_produto.items()
            },
        }
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    # ---------- log thread-safe ----------
    def _log(self, msg, transiente=False):
        self.fila_log.put((msg, transiente))

    def _drenar_log(self):
        try:
            while True:
                msg, transiente = self.fila_log.get_nowait()
                if msg == "__habilitar__":
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

    def _iniciar_geracao(self):
        pasta = self.var_pasta.get().strip()
        if not pasta:
            messagebox.showwarning("Atenção", "Informe a pasta de destino.", parent=self)
            return
        try:
            inivig = self.calendario.get_date()
        except Exception:
            messagebox.showwarning(
                "Atenção", "Data de início de vigência inválida.", parent=self)
            return

        selecao = {}
        for codigo, (var_incluir, var_modo, var_qtd) in self.linhas_produto.items():
            if not var_incluir.get():
                continue
            if var_modo.get() == "toda":
                selecao[codigo] = None
            else:
                try:
                    qtd = int(var_qtd.get().replace(".", "").replace(",", ""))
                    if qtd <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning(
                        "Atenção", f"Quantidade inválida no Código {codigo}.",
                        parent=self)
                    return
                selecao[codigo] = qtd
        if not selecao:
            messagebox.showwarning("Atenção", "Selecione ao menos um produto.",
                                   parent=self)
            return

        self._salvar_config()
        self.btn_gerar.configure(state="disabled")
        self._log("=" * 60)
        self._log(f"Data de início de vigência: {inivig.strftime('%d/%m/%Y')}")
        threading.Thread(
            target=self._trabalho,
            args=(pasta, inivig, selecao, self.var_enviar.get()),
            daemon=True).start()

    def _trabalho(self, pasta, inivig, selecao, enviar):
        try:
            caminho, resultado = gerador_porto.gerar_planilha(
                pasta, inivig, selecao, log=self._log)
            self._log("--- Total de linhas por produto ---")
            for prod in gerador_porto.PRODUTOS:
                if prod["codigo"] in resultado:
                    self._log(f"Código {prod['codigo']} - {prod['nome']}: "
                              f"{resultado[prod['codigo']]} linhas")
            self._log(f"TOTAL GERAL: {sum(resultado.values())} linhas")
            if enviar:
                enviar_arquivo(caminho, log=self._log)
            self._log("Concluído.")
        except Exception as e:
            self._log(f"[ERRO] {e}")
        finally:
            self.fila_log.put(("__habilitar__", False))
