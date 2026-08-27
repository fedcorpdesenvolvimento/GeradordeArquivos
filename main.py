# -*- coding: utf-8 -*-
"""SISTEMA DE ENVIO PORTO SEGURO — menu principal.

Ponto de entrada do sistema. Cada botão do menu abre um módulo em sua
própria janela. Para adicionar um módulo novo: criar o arquivo em
modulos/, expor uma classe CTkToplevel e registrar um botão aqui.

Rode com:  python main.py
"""
import customtkinter as ctk
from tkinter import messagebox

from modulos.subgrupos_vida import JanelaSubgruposVida
from modulos.porto_assistencia import JanelaPortoAssistencia
from modulos.porto_dental import JanelaPortoDental

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class MenuPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA DE ENVIO PORTO SEGURO")
        self.geometry("460x480")

        ctk.CTkLabel(self, text="SISTEMA DE ENVIO\nPORTO SEGURO",
                     font=("Arial", 22, "bold")).pack(pady=(30, 8))
        ctk.CTkLabel(self, text="Selecione o módulo:",
                     font=("Arial", 14)).pack(pady=(0, 18))

        ctk.CTkButton(self, text="SUBGRUPOS DE VIDA",
                      font=("Arial", 15, "bold"), height=48, width=300,
                      command=self.abrir_subgrupos_vida).pack(pady=8)

        ctk.CTkButton(self, text="PORTO ASSISTÊNCIA",
                      font=("Arial", 15, "bold"), height=48, width=300,
                      fg_color="green", hover_color="darkgreen",
                      command=self.abrir_porto_assistencia).pack(pady=8)

        ctk.CTkButton(self, text="GERA PORTO DENTAL",
                      font=("Arial", 15, "bold"), height=48, width=300,
                      fg_color="green", hover_color="darkgreen",
                      command=self.abrir_porto_dental).pack(pady=8)

        # --- Módulos planejados (código entra depois, no mesmo padrão) ---
        ctk.CTkButton(self, text="GERAR DENTAL SEMPRE ODONTO",
                      font=("Arial", 15, "bold"), height=48, width=300,
                      fg_color="gray40", hover_color="gray30",
                      command=lambda: self.modulo_em_desenvolvimento(
                          "GERAR DENTAL SEMPRE ODONTO")).pack(pady=8)

        ctk.CTkLabel(self, text="Grupo Fedcorp",
                     font=("Arial", 10)).pack(side="bottom", pady=8)

    def modulo_em_desenvolvimento(self, nome):
        messagebox.showinfo(
            nome, f"O módulo {nome} está em desenvolvimento e será "
                  f"disponibilizado em uma próxima versão.", parent=self)

    def abrir_subgrupos_vida(self):
        janela = JanelaSubgruposVida(self)
        janela.focus()

    def abrir_porto_assistencia(self):
        janela = JanelaPortoAssistencia(self)
        janela.focus()

    def abrir_porto_dental(self):
        janela = JanelaPortoDental(self)
        janela.focus()


if __name__ == "__main__":
    app = MenuPrincipal()
    app.mainloop()
