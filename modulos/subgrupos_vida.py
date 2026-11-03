# -*- coding: utf-8 -*-
"""Módulo SUBGRUPOS DE VIDA — gerador de relatórios de Vida por subgrupo.

Código original de U:\\--2021\\02-gerador_planilhas_firebird\\main.py,
adaptado para rodar como janela do SISTEMA DE ENVIO PORTO SEGURO:
- a classe virou CTkToplevel (janela filha do menu) em vez de CTk;
- a conexão passou a vir de db.conectar() em vez de fdb.connect local.
Toda a lógica de negócio (queries, procedure e geração) está intacta.
"""
import calendar
import os
import queue
import re
import threading
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk, filedialog

import customtkinter as ctk
import pandas as pd
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill
from tkcalendar import DateEntry

import db
from modulos import gerador_vida


def primeiro_dia_mes_anterior() -> date:
    """Dia 01 do mês anterior à data de hoje (padrão da vigência)."""
    primeiro_deste_mes = date.today().replace(day=1)
    return (primeiro_deste_mes - timedelta(days=1)).replace(day=1)


class JanelaSubgruposVida(ctk.CTkToplevel):
    # Subgrupos cujo relatório inclui os segurados com COBERTURA PROVISÓRIA
    # (fluxo do Delphi com a fatura temporária 99). Hoje só VIDA RJ.
    SUBGRUPOS_COB_PROV = gerador_vida.SUBGRUPOS_COB_PROV
    FATURA_COB_PROV = gerador_vida.FATURA_COB_PROV

    def __init__(self, master):
        super().__init__(master)
        self.title("Gerador de Relatórios - Vida")
        self.geometry("450x830")  # Aumentado para acomodar os botões e o status do robô
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

        # Botão do robô (agendamento noturno de todos os subgrupos)
        self.btn_robo = ctk.CTkButton(self, text="Agendar Robô (todos os subgrupos)",
                                      command=self.abrir_agendador,
                                      fg_color="#6B4E9B", hover_color="#4F3875")
        self.btn_robo.pack(pady=10)

        self.lbl_status_robo = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.lbl_status_robo.pack(pady=(0, 10))

        # Estado do agendamento
        self._id_after_robo = None      # id retornado por self.after (para cancelar)
        self._janela_agendador = None
        self._robo_rodando = False
        self.ultimo_aviso = None        # aviso não fatal da última geração
        self._fila_robo = queue.Queue()  # resultado da thread -> thread principal
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _ao_fechar(self):
        """Fechar a janela com robô agendado cancelaria o after() em silêncio
        (o robô nunca rodaria). Avisa e, se estiver rodando, não deixa fechar."""
        if self._robo_rodando:
            messagebox.showwarning("Robô em execução",
                                   "O robô está gerando as planilhas. Aguarde o término para fechar.")
            return
        if self._id_after_robo is not None:
            if not messagebox.askyesno("Robô agendado",
                                       "Há um robô agendado. Fechar a janela CANCELA o agendamento.\n\nFechar mesmo assim?"):
                return
            self.after_cancel(self._id_after_robo)
            self._id_after_robo = None
        self.destroy()

    def carregar_subgrupos(self):
        try:
            conn = db.conectar()
            cur = conn.cursor()
            # O código do subgrupo aparece entre [] no fim, só como informação;
            # a geração continua buscando pelo nome (o sufixo é removido antes).
            cur.execute("SELECT NOME_SUBGRP, SUBGRUPO FROM SUBGRUPOSEGURADORA ORDER BY NOME_SUBGRP")
            for row in cur.fetchall():
                cb = ctk.CTkCheckBox(self.scroll_frame, text=f"{row[0]} [{row[1]}]")
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
                and ((apo.subporto is null) or (apo.subporto=''))
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

    # ------------------------------------------------------------------
    # Miolo da geração — delega a modulos/gerador_vida.py (branch web-render):
    # a tela desktop e a tela web usam exatamente a mesma lógica.
    # ------------------------------------------------------------------
    @staticmethod
    def _limpar_nome_subgrupo(texto):
        return gerador_vida.limpar_nome_subgrupo(texto)

    def _montar_dataframe(self, conn, data_firebird, nomes_subgrupos):
        df, id_sub_arquivo, self.ultimo_aviso = gerador_vida.montar_dataframe(conn, data_firebird, nomes_subgrupos)
        return df, id_sub_arquivo

    def _incluir_coberturas_provisorias(self, conn, cur, data_firebird, id_subgrupo):
        return gerador_vida.incluir_coberturas_provisorias(conn, cur, data_firebird, id_subgrupo)

    def _salvar_excel(self, df, caminho):
        return gerador_vida.salvar_excel(df, caminho)

    def _inconsistencias_do_subgrupo(self, cur, data_obj, id_subgrupo):
        return gerador_vida.inconsistencias_do_subgrupo(cur, data_obj, id_subgrupo)

    def _confirmar_inconsistencias(self, achados, data_ptbr):
        """Mostra a grade de apólices sem SUBPORTO e pergunta se continua.
        achados: [(nome_subgrupo, id_subgrupo, apolice, seq, fatura, nome_adm)].
        Devolve True para continuar a geração, False para cancelar."""
        jan = ctk.CTkToplevel(self)
        jan.title("Inconsistências no escopo do(s) subgrupo(s)")
        jan.geometry("900x480")
        jan.attributes("-topmost", True)
        jan.grab_set()

        ctk.CTkLabel(jan, text=f"{len(achados)} apólice(s) do escopo com SUBPORTO vazio na vigência {data_ptbr}.",
                     font=("Arial", 14, "bold"), text_color="#B00020").pack(pady=(12, 2))
        ctk.CTkLabel(jan, text="Essas empresas NÃO entrarão na planilha. Corrija o cadastro ou continue mesmo assim.",
                     font=("Arial", 11)).pack()

        frame = ctk.CTkFrame(jan)
        frame.pack(expand=True, fill="both", padx=10, pady=8)
        colunas = ("SUBGRUPO", "APOLICE", "SEQ", "FATURA", "ADMINISTRADORA")
        tabela = ttk.Treeview(frame, columns=colunas, show="headings")
        larguras = {"SUBGRUPO": 170, "APOLICE": 90, "SEQ": 50, "FATURA": 80, "ADMINISTRADORA": 420}
        for c in colunas:
            tabela.heading(c, text=c)
            tabela.column(c, width=larguras[c], anchor="w" if c in ("SUBGRUPO", "ADMINISTRADORA") else "center")
        for nome_sub, id_sub, apol, seq, fat, adm in achados:
            tabela.insert("", "end", values=(f"{nome_sub} [{id_sub}]", apol, seq, fat, adm))
        sb = ttk.Scrollbar(frame, orient="vertical", command=tabela.yview)
        tabela.configure(yscrollcommand=sb.set)
        tabela.pack(side="left", expand=True, fill="both")
        sb.pack(side="right", fill="y")

        resposta = {"continuar": False}
        botoes = ctk.CTkFrame(jan, fg_color="transparent")
        botoes.pack(pady=10)

        def continuar():
            resposta["continuar"] = True
            jan.destroy()

        ctk.CTkButton(botoes, text="Continuar mesmo assim", fg_color="green", hover_color="darkgreen",
                      command=continuar).pack(side="left", padx=8)
        ctk.CTkButton(botoes, text="Cancelar geração", fg_color="#8B0000", hover_color="#5A0000",
                      command=jan.destroy).pack(side="left", padx=8)
        jan.protocol("WM_DELETE_WINDOW", jan.destroy)
        self.wait_window(jan)
        return resposta["continuar"]

    # ------------------------------------------------------------------
    # Botão manual "Gerar Planilha Excel"
    # ------------------------------------------------------------------
    def processar(self):
        if self._robo_rodando:
            messagebox.showwarning("Atenção", "O robô está em execução. Aguarde o término.")
            return

        data_ptbr = self.calendario.get()
        try:
            data_objeto = datetime.strptime(data_ptbr, '%d/%m/%Y')
        except ValueError:
            messagebox.showerror("Erro", "Data de vigência inválida.")
            return
        data_firebird = data_objeto.strftime('%m/%d/%Y')

        selecionados = [cb.cget("text") for cb in self.checkboxes if cb.get() == 1]

        if not selecionados:
            messagebox.showwarning("Atenção", "Selecione ao menos um subgrupo!")
            return

        conn = None
        try:
            conn = db.conectar()

            # Checagem de inconsistências no escopo de cada subgrupo escolhido.
            # Só na geração manual: o robô chama _montar_dataframe direto e
            # não pode ficar parado esperando resposta.
            cur = conn.cursor()
            achados = []
            for nome in selecionados:
                nome_limpo = self._limpar_nome_subgrupo(nome)
                cur.execute("SELECT SUBGRUPO FROM SUBGRUPOSEGURADORA WHERE NOME_SUBGRP = ?", (nome_limpo,))
                res = cur.fetchone()
                if not res:
                    continue
                for apol, seq, fat, adm in self._inconsistencias_do_subgrupo(cur, data_objeto, res[0]):
                    achados.append((nome_limpo, res[0], apol, seq, fat, adm))
            if achados and not self._confirmar_inconsistencias(achados, data_ptbr):
                messagebox.showwarning("Cancelado", "Geração cancelada. Corrija o SUBPORTO das apólices e gere novamente.")
                return

            df, id_sub_arquivo = self._montar_dataframe(conn, data_firebird, selecionados)

            if df.empty:
                messagebox.showinfo("Aviso", "Nenhum dado encontrado para os filtros selecionados.")
            else:
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
                    self._salvar_excel(df, caminho_arquivo)
                    messagebox.showinfo("Sucesso", f"Planilha salva em:\n{caminho_arquivo}")
                    if self.ultimo_aviso:
                        messagebox.showwarning("Atenção", self.ultimo_aviso)
                else:
                    messagebox.showwarning("Cancelado", "A exportação foi cancelada pelo usuário.")

        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            messagebox.showerror("Erro Crítico", f"Erro durante o processamento: {e}")
        finally:
            if conn is not None:
                conn.close()   # devolve ao pool mesmo em erro

    # ------------------------------------------------------------------
    # ROBÔ: agendamento da geração de TODOS os subgrupos
    # ------------------------------------------------------------------
    def abrir_agendador(self):
        """Janela para configurar o robô: vigência, pasta de destino e horário."""
        if self._robo_rodando:
            messagebox.showwarning("Atenção", "O robô já está em execução.")
            return
        if self._janela_agendador is not None and self._janela_agendador.winfo_exists():
            self._janela_agendador.lift()
            return

        jan = ctk.CTkToplevel(self)
        jan.title("Agendar Robô - Subgrupos de Vida")
        jan.geometry("520x440")
        jan.attributes("-topmost", True)
        self._janela_agendador = jan

        ctk.CTkLabel(jan, text="Robô: gera a planilha de TODOS os subgrupos",
                     font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(jan, text=f"{len(self.checkboxes)} subgrupos serão processados, um arquivo por subgrupo.",
                     font=("Arial", 11), text_color="gray").pack()

        # Data de vigência
        ctk.CTkLabel(jan, text="Data de Vigência:", font=("Arial", 12, "bold")).pack(pady=(15, 2))
        cal_robo = DateEntry(jan, width=18, background='darkblue', foreground='white',
                             date_pattern='dd/mm/yyyy', font=('Arial', 12), borderwidth=2, relief="solid")
        # começa com a mesma data do calendário principal
        try:
            cal_robo.set_date(datetime.strptime(self.calendario.get(), '%d/%m/%Y'))
        except Exception:
            cal_robo.set_date(primeiro_dia_mes_anterior())
        cal_robo.pack(pady=2)

        # Pasta de destino
        ctk.CTkLabel(jan, text="Pasta onde salvar os arquivos:", font=("Arial", 12, "bold")).pack(pady=(15, 2))
        frame_pasta = ctk.CTkFrame(jan, fg_color="transparent")
        frame_pasta.pack(fill="x", padx=20)
        var_pasta = ctk.StringVar(value="")
        ent_pasta = ctk.CTkEntry(frame_pasta, textvariable=var_pasta, font=("Arial", 11))
        ent_pasta.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def escolher_pasta():
            jan.attributes("-topmost", False)
            pasta = filedialog.askdirectory(title="Escolha a pasta de destino", parent=jan)
            jan.attributes("-topmost", True)
            if pasta:
                var_pasta.set(pasta)

        ctk.CTkButton(frame_pasta, text="Escolher...", width=90, command=escolher_pasta).pack(side="left")

        # Horário
        ctk.CTkLabel(jan, text="Horário de início (HH:MM):", font=("Arial", 12, "bold")).pack(pady=(15, 2))
        var_hora = ctk.StringVar(value="22:00")
        ctk.CTkEntry(jan, textvariable=var_hora, width=90, justify="center",
                     font=("Arial", 14)).pack(pady=2)
        ctk.CTkLabel(jan, text="Se o horário já passou hoje, o robô é agendado para amanhã.\n"
                              "O programa deve ficar aberto e o computador ligado (sem hibernar).",
                     font=("Arial", 10), text_color="gray").pack(pady=(4, 0))

        # Botões
        frame_btn = ctk.CTkFrame(jan, fg_color="transparent")
        frame_btn.pack(pady=15)
        ctk.CTkButton(frame_btn, text="Agendar", fg_color="green", hover_color="darkgreen",
                      command=lambda: self._agendar_robo(cal_robo.get(), var_pasta.get(), var_hora.get(), jan)
                      ).pack(side="left", padx=5)
        ctk.CTkButton(frame_btn, text="Executar agora", fg_color="#2b5797", hover_color="#1e3d6b",
                      command=lambda: self._agendar_robo(cal_robo.get(), var_pasta.get(), None, jan)
                      ).pack(side="left", padx=5)
        ctk.CTkButton(frame_btn, text="Cancelar agendamento", fg_color="#8B0000", hover_color="#5A0000",
                      command=self._cancelar_robo).pack(side="left", padx=5)

    def _agendar_robo(self, data_ptbr, pasta, hora_txt, janela):
        """Valida os campos e marca o disparo com self.after()."""
        try:
            data_obj = datetime.strptime(data_ptbr, '%d/%m/%Y')
        except ValueError:
            messagebox.showerror("Erro", "Data de vigência inválida.", parent=janela)
            return
        if not pasta or not os.path.isdir(pasta):
            messagebox.showerror("Erro", "Escolha uma pasta de destino válida.", parent=janela)
            return

        if hora_txt is None:
            atraso_ms = 0
            quando = datetime.now()
        else:
            try:
                hora_obj = datetime.strptime(hora_txt.strip(), '%H:%M').time()
            except ValueError:
                messagebox.showerror("Erro", "Horário inválido. Use o formato HH:MM (ex.: 22:30).", parent=janela)
                return
            quando = datetime.combine(date.today(), hora_obj)
            if quando <= datetime.now():
                quando += timedelta(days=1)
            atraso_ms = int((quando - datetime.now()).total_seconds() * 1000)

        # cancela agendamento anterior, se houver
        if self._id_after_robo is not None:
            self.after_cancel(self._id_after_robo)
            self._id_after_robo = None

        nomes = [cb.cget("text") for cb in self.checkboxes]
        self._id_after_robo = self.after(atraso_ms, lambda: self._iniciar_robo(data_obj, pasta, nomes))

        self.lbl_status_robo.configure(
            text=f"Robô agendado para {quando.strftime('%d/%m/%Y %H:%M')} | vigência {data_ptbr}\n{pasta}",
            text_color="#6B4E9B")
        janela.destroy()
        if hora_txt is not None:
            messagebox.showinfo("Robô agendado",
                                f"O robô vai gerar {len(nomes)} subgrupos em {quando.strftime('%d/%m/%Y às %H:%M')}.\n"
                                f"Vigência: {data_ptbr}\nPasta: {pasta}\n\n"
                                "Deixe o programa aberto e o computador ligado.")

    def _cancelar_robo(self):
        if self._id_after_robo is None:
            messagebox.showinfo("Robô", "Não há agendamento ativo.")
            return
        self.after_cancel(self._id_after_robo)
        self._id_after_robo = None
        self.lbl_status_robo.configure(text="Agendamento cancelado.", text_color="gray")

    def _iniciar_robo(self, data_obj, pasta, nomes):
        """Chamado pelo after() na hora marcada: dispara a thread de geração."""
        self._id_after_robo = None
        self._robo_rodando = True
        self.btn_gerar.configure(state="disabled")
        self.btn_ver_tela.configure(state="disabled")
        self.btn_robo.configure(state="disabled")
        self.lbl_status_robo.configure(text="Robô em execução...", text_color="orange")

        threading.Thread(target=self._executar_robo, args=(data_obj, pasta, nomes), daemon=True).start()
        self.after(500, self._vigiar_robo)

    def _vigiar_robo(self):
        """Roda na thread principal a cada 0,5 s até a thread do robô
        depositar o resultado na fila. (Chamar self.after() de dentro da
        thread do robô NÃO funciona — tkinter não é thread-safe.)"""
        try:
            gerados, vazios, erros, pasta = self._fila_robo.get_nowait()
        except queue.Empty:
            self.after(500, self._vigiar_robo)
            return
        self._finalizar_robo(gerados, vazios, erros, pasta)

    def _executar_robo(self, data_obj, pasta, nomes):
        """Roda em thread: um arquivo por subgrupo + robo_log.txt na pasta.

        Nada aqui mexe em widgets nem chama self.after(): o resultado vai
        para self._fila_robo e _vigiar_robo (thread principal) finaliza.
        """
        data_ptbr = data_obj.strftime('%d/%m/%Y')
        data_firebird = data_obj.strftime('%m/%d/%Y')
        data_str = data_ptbr.replace('/', '-')
        log = [f"ROBÔ SUBGRUPOS DE VIDA - início {datetime.now():%d/%m/%Y %H:%M:%S}",
               f"Vigência: {data_ptbr} | Pasta: {pasta} | Subgrupos: {len(nomes)}", ""]
        gerados = vazios = erros = 0

        try:
            conn = db.conectar()
        except Exception as e:
            log.append(f"ERRO ao conectar no banco: {e}")
            self._gravar_log(pasta, log)
            self._fila_robo.put((0, 0, 1, pasta))
            return

        for nome in nomes:
            nome_limpo = self._limpar_nome_subgrupo(nome)
            try:
                df, id_sub = self._montar_dataframe(conn, data_firebird, [nome])
                if id_sub == "Varios":
                    # nenhum SUBGRUPO encontrado para esse nome
                    erros += 1
                    log.append(f"[ERRO  ] {nome_limpo} - subgrupo não encontrado em SUBGRUPOSEGURADORA")
                    continue
                if df.empty:
                    vazios += 1
                    log.append(f"[VAZIO ] {nome_limpo} ({id_sub}) - nenhum dado")
                    continue
                caminho = os.path.join(pasta, f"Subgrupo_{id_sub}_Relatorio_{data_str}.xlsx")
                self._salvar_excel(df, caminho)
                gerados += 1
                log.append(f"[OK    ] {nome_limpo} ({id_sub}) - {len(df)} linhas -> {os.path.basename(caminho)}")
                aviso = getattr(self, "ultimo_aviso", None)
                if aviso:
                    log.append(f"[AVISO ] {aviso.splitlines()[0]}")
            except Exception as e:
                erros += 1
                log.append(f"[ERRO  ] {nome_limpo} - {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

        try:
            conn.close()
        except Exception:
            pass

        log += ["", f"Fim {datetime.now():%d/%m/%Y %H:%M:%S} - gerados: {gerados} | vazios: {vazios} | erros: {erros}"]
        self._gravar_log(pasta, log)
        self._fila_robo.put((gerados, vazios, erros, pasta))

    @staticmethod
    def _gravar_log(pasta, linhas):
        try:
            with open(os.path.join(pasta, "robo_log.txt"), "a", encoding="utf-8") as f:
                f.write("\n".join(linhas) + "\n\n")
        except Exception:
            pass

    def _finalizar_robo(self, gerados, vazios, erros, pasta):
        self._robo_rodando = False
        self.btn_gerar.configure(state="normal")
        self.btn_ver_tela.configure(state="normal")
        self.btn_robo.configure(state="normal")
        cor = "green" if erros == 0 else "red"
        self.lbl_status_robo.configure(
            text=f"Robô concluído {datetime.now():%d/%m %H:%M} - gerados: {gerados} | vazios: {vazios} | erros: {erros}",
            text_color=cor)
        messagebox.showinfo("Robô concluído",
                            f"Gerados: {gerados}\nSem dados: {vazios}\nErros: {erros}\n\n"
                            f"Detalhes em:\n{os.path.join(pasta, 'robo_log.txt')}")
