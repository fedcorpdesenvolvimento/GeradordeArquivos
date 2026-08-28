# -*- coding: utf-8 -*-
"""SISTEMA DE ENVIO PORTO SEGURO — menu principal.

Ponto de entrada do sistema. Cada botão do menu abre um módulo em sua
própria janela. Para adicionar um módulo novo: criar o arquivo em
modulos/, expor uma classe CTkToplevel e registrar um botão aqui.

Rode com:  python main.py
"""
import customtkinter as ctk

from modulos.subgrupos_vida import JanelaSubgruposVida
from modulos.porto_assistencia import JanelaPortoAssistencia
from modulos.porto_dental import JanelaPortoDental
from modulos.dental_sempre_odonto import JanelaDentalSempreOdonto

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

        # azul pastel para diferenciar o produto Sempre Odonto dos da Porto
        ctk.CTkButton(self, text="GERAR DENTAL SEMPRE ODONTO",
                      font=("Arial", 15, "bold"), height=48, width=300,
                      fg_color="#7A9CC6", hover_color="#5F82AC",
                      command=self.abrir_sempre_odonto).pack(pady=8)

        ctk.CTkLabel(self, text="Grupo Fedcorp",
                     font=("Arial", 10)).pack(side="bottom", pady=8)

    def abrir_subgrupos_vida(self):
        janela = JanelaSubgruposVida(self)
        janela.focus()

    def abrir_porto_assistencia(self):
        janela = JanelaPortoAssistencia(self)
        janela.focus()

    def abrir_porto_dental(self):
        janela = JanelaPortoDental(self)
        janela.focus()

    def abrir_sempre_odonto(self):
        janela = JanelaDentalSempreOdonto(self)
        janela.focus()


if __name__ == "__main__":
    app = MenuPrincipal()
    app.mainloop()
