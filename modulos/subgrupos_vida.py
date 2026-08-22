# -*- coding: utf-8 -*-
"""Módulo SUBGRUPOS DE VIDA — gerador de relatórios de Vida por subgrupo.

Código original de U:\\--2021\\02-gerador_planilhas_firebird\\main.py,
adaptado para rodar como janela do SISTEMA DE ENVIO PORTO SEGURO:
- a classe virou CTkToplevel (janela filha do menu) em vez de CTk;
- a conexão passou a vir de db.conectar() em vez de fdb.connect local.
Toda a lógica de negócio (queries, procedure e geração) está intacta.
"""
import calendar
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk, filedialog

import customtkinter as ctk
import pandas as pd
from tkcalendar import DateEntry

import db


def primeiro_dia_mes_anterior() -> date:
    """Dia 01 do mês anterior à data de hoje (padrão da vigência)."""
    primeiro_deste_mes = date.today().replace(day=1)
    return (primeiro_deste_mes - timedelta(days=1)).replace(day=1)


class JanelaSubgruposVida(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Gerador de Relatórios - Vida")
        self.geometry("450x750")  # Aumentado para acomodar os novos botões
        self.attributes("-topmost", True)

        # UI - Cabeçalho
        ctk.CTkLabel(self, text="Data de Vigência:", font=("Arial", 18, "bold")).pack(pady=(20, 5))
        self.calendario_frame = ctk.CTkFrame(self)
        self.calendario_frame.pack(pady=20, padx=20, fill="x")

        # Calendário com tamanho aumentado
        self.calendario = DateEntry(
            self.calendario_frame,
            width=20,              # Largura do campo
            background='darkblue',
            foreground='white',
            date_pattern='dd/mm/yyyy',
            font=('Arial', 12),    # Fonte maior para melhor visualização
            borderwidth=2,         # Borda mais grossa para destacar
            relief="solid"
        )
        # Data pré-configurada: dia 01 do mês anterior (pode ser alterada)
        self.calendario.set_date(primeiro_dia_mes_anterior())
        self.calendario.pack(pady=10, padx=10, fill="x", expand=True)

        ctk.CTkLabel(self, text="Selecione os Subgrupos:", font=("Arial", 14, "bold")).pack(pady=(20, 5))
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=380, height=300)
        self.scroll_frame.pack(pady=10)

        self.checkboxes = []
        self.carregar_subgrupos()

        # --- BOTÕES ---
        self.btn_gerar = ctk.CTkButton(self, text="Gerar Planilha Excel", command=self.processar,
                                       fg_color="green", hover_color="darkgreen")
        self.btn_gerar.pack(pady=10)

        # Botão de Inconsistências
        self.btn_ver_tela = ctk.CTkButton(self, text="Ver Inconsistências (Tela)",
                                          command=self.abrir_relatorio_tela,
                                          fg_color="#2b5797", hover_color="#1e3d6b")
        self.btn_ver_tela.pack(pady=10)

    def carregar_subgrupos(self):
        try:
            conn = db.conectar()
            cur = conn.cursor()
            cur.execute("SELECT NOME_SUBGRP FROM SUBGRUPOSEGURADORA ORDER BY NOME_SUBGRP")
            for row in cur.fetchall():
                cb = ctk.CTkCheckBox(self.scroll_frame, text=row[0])
                cb.pack(anchor="w", padx=10, pady=5)
                self.checkboxes.append(cb)
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar subgrupos: {e}")

    def abrir_relatorio_tela(self):
        # 1. Preparação da Data baseada na seleção do calendário
        data_ptbr = self.calendario.get()
        data_obj = datetime.strptime(data_ptbr, '%d/%m/%Y')

        # Ajuste dinâmico conforme sua query: Mês/01/Ano e Mês/último-dia/Ano
        data_ini = data_obj.strftime('%m/01/%Y')

        if isinstance(data_obj, tuple):
            # Pega apenas os 3 primeiros elementos (ano, mês, dia) caso a tupla seja maior
            data_obj = datetime(*data_obj[:3])

        _, ultimo_dia = calendar.monthrange(data_obj.year, data_obj.month)
        data_final_mes = data_obj.replace(day=ultimo_dia)
        data_fim = data_final_mes.strftime('%m/%d/%Y')

        try:
            conn = db.conectar()
            cur = conn.cursor()

            query_tela = f"""
                select f.apolice, f.seq, f.fatura, pes.nome, apo.subporto, count(*)
                from faturas f
                left join apolices apo on apo.apolice=f.apolice
                                      and apo.administradora = f.administradora
                                      and apo.seq = f.seq
                left join pessoas pes on pes.pessoa = f.administradora
                where ((f.dt_ini_vig='{data_ini}') or (f.dt_ini_vig < '{data_ini}' and f.dt_fim_vig >='{data_fim}'))
                and f.status = 'A'
                and f.ramo = 'V'
                and ((apo.subporto is null) or (apo.subporto='')
                and ((f.apolice not like 'C%') and (f.apolice <> 'VR0001'))
                group by f.apolice, f.seq, f.fatura, pes.nome, apo.subporto
                order by 1, 4
            """
            cur.execute(query_tela)
            dados = cur.fetchall()
            colunas = [desc[0] for desc in cur.description]  # Nomes das colunas da query
            conn.close()

            if not dados:
                messagebox.showinfo("Inconsistências", "Nenhuma inconsistência encontrada para esta data!")
                return

            # Janela Pop-up para a Tabela
            janela_tabela = ctk.CTkToplevel(self)
            janela_tabela.title("Relatório de Inconsistências")
            janela_tabela.geometry("800x450")
            janela_tabela.attributes("-topmost", True)

            # Estilo para a Tabela
            style = ttk.Style()
            style.theme_use("clam")

            frame_tab = ctk.CTkFrame(janela_tabela)
            frame_tab.pack(expand=True, fill="both", padx=10, pady=10)

            tabela = ttk.Treeview(frame_tab, columns=colunas, show='headings')

            for col in colunas:
                tabela.heading(col, text=col)
                tabela.column(col, width=110, anchor="center")

            for linha in dados:
                tabela.insert('', 'end', values=linha)

            scrollbar = ttk.Scrollbar(frame_tab, orient="vertical", command=tabela.yview)
            tabela.configure(yscrollcommand=scrollbar.set)

            tabela.pack(side="left", expand=True, fill="both")
            scrollbar.pack(side="right", fill="y")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar relatório em tela: {e}")

    def processar(self):
        data_ptbr = self.calendario.get()
        data_objeto = datetime.strptime(data_ptbr, '%d/%m/%Y')
        data_firebird = data_objeto.strftime('%m/%d/%Y')

        selecionados = [cb.cget("text") for cb in self.checkboxes if cb.get() == 1]

        if not selecionados:
            messagebox.showwarning("Atenção", "Selecione ao menos um subgrupo!")
            return

        try:
            conn = db.conectar()
            cur = conn.cursor()

            cur.execute("DELETE FROM TEMP_RELATORIO_VIDA")
            cur.execute("DELETE FROM TEMP_RELATORIO_VIDA2")

            id_sub_arquivo = "Varios"  # Valor padrão caso selecione muitos

            for nome_sub in selecionados:
                cur.execute("SELECT SUBGRUPO FROM SUBGRUPOSEGURADORA WHERE NOME_SUBGRP = ?", (nome_sub,))
                res_sub = cur.fetchone()
                if not res_sub:
                    continue
                id_subgrupo = res_sub[0]
                id_sub_arquivo = id_subgrupo  # Guarda o último ID para o nome do arquivo

                query_faturas = f"""
                    select fat.fatura
                    from faturas fat
                    left join apolices apo on apo.administradora=fat.administradora
                                         and apo.apolice=fat.apolice and apo.seq = fat.seq
                    where fat.status = 'A'
                      and (('{data_firebird}' between fat.dt_ini_vig and fat.dt_fim_vig) or (fat.dt_ini_vig = '{data_firebird}'))
                      and apo.subporto = '{id_subgrupo}'
                    group by fat.fatura, fat.dt_ini_vig, fat.dt_fim_vig
                """
                cur.execute(query_faturas)
                faturas_rows = cur.fetchall()

                for row in faturas_rows:
                    num_fatura = row[0]
                    cur.execute("EXECUTE PROCEDURE GERA_REL_PLA_SISTEMA(?)", (num_fatura,))
                    cur.execute("INSERT INTO TEMP_RELATORIO_VIDA2 SELECT * FROM TEMP_RELATORIO_VIDA")

                conn.commit()

            # Gerar Planilha Final
            qry_tempo = """
                select trv.coestip administradora, trv.apolice, trv.seq, trv.fatura,
                       trv.posto, trv.seq_posto, vp.nome_posto,
                       trv.nome, trv.documento, trv.sexo,1 civil, trv.nasc,
                       trv.dt_ini_vig, trv.dt_fim_vig,
                       trv.produto, trv.subporto,
                       trv.cobertura1, trv.valor1,
                       trv.cobertura2, trv.valor2
                from temp_relatorio_vida2 trv
                left join vida_postos vp on vp.administradora = trv.administradora
                                       and vp.posto = trv.posto
                                       and vp.seq_posto = trv.seq_posto
                order by 1, 2, 3
            """

            df = pd.read_sql(qry_tempo, conn)

            if df.empty:
                messagebox.showinfo("Aviso", "Nenhum dado encontrado para os filtros selecionados.")
            else:
                # --- FORMATAÇÃO DE DATAS ---
                colunas_data = ['NASC', 'DT_INI_VIG', 'DT_FIM_VIG']
                for col in colunas_data:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y')

                # --- JANELA PARA ESCOLHER PASTA E NOME ---
                data_str = data_ptbr.replace('/', '-')
                nome_sugerido = f"Subgrupo_{id_sub_arquivo}_Relatorio_{data_str}.xlsx"

                # Abre a janela "Salvar Como"
                caminho_arquivo = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    initialfile=nome_sugerido,
                    filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                    title="Escolha onde salvar sua planilha"
                )

                # Se o usuário não cancelar a janela (caminho_arquivo não for vazio)
                if caminho_arquivo:
                    df.to_excel(caminho_arquivo, index=False)
                    messagebox.showinfo("Sucesso", f"Planilha salva em:\n{caminho_arquivo}")
                else:
                    messagebox.showwarning("Cancelado", "A exportação foi cancelada pelo usuário.")

            conn.close()

        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Erro durante o processamento: {e}")
