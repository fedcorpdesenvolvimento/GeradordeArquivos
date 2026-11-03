# -*- coding: utf-8 -*-
"""Núcleo do SUBGRUPOS DE VIDA sem interface (branch web-render, 03/11/2026).

Extraído de modulos/subgrupos_vida.py para a tela desktop (customtkinter) e
a tela web (web/app.py) usarem exatamente a mesma lógica. As queries são as
do gerador antigo (U:\\--2021\\02-gerador_planilhas_firebird) — não alterar
sem o usuário pedir. A classe JanelaSubgruposVida delega para cá.
"""
import calendar
import re
from datetime import date, datetime

import pandas as pd
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill

import db

# Subgrupos cujo relatório inclui os segurados com COBERTURA PROVISÓRIA
# (fluxo do Delphi com a fatura temporária 99). Hoje só VIDA RJ.
SUBGRUPOS_COB_PROV = {'1317377'}
FATURA_COB_PROV = 99


def primeiro_dia_mes_anterior() -> date:
    """Dia 01 do mês anterior à data de hoje (padrão da vigência)."""
    primeiro_deste_mes = date.today().replace(day=1)
    return (primeiro_deste_mes.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)


def limpar_nome_subgrupo(texto):
    """Remove o sufixo " [código]" exibido nos checkboxes."""
    return re.sub(r"\s*\[[^\]]*\]$", "", texto)


def listar_subgrupos(conn):
    """[(nome, codigo), ...] em ordem de nome."""
    cur = conn.cursor()
    cur.execute("SELECT NOME_SUBGRP, SUBGRUPO FROM SUBGRUPOSEGURADORA ORDER BY NOME_SUBGRP")
    return [(r[0], r[1]) for r in cur.fetchall()]


def _datas_mes(data_obj):
    data_ini = data_obj.strftime('%m/01/%Y')
    _, ultimo_dia = calendar.monthrange(data_obj.year, data_obj.month)
    data_fim = data_obj.replace(day=ultimo_dia).strftime('%m/%d/%Y')
    return data_ini, data_fim


def relatorio_inconsistencias(cur, data_obj):
    """Relatório "Ver Inconsistências (Tela)": faturas de Vida ativas no mês
    cuja apólice está sem SUBPORTO. Devolve (colunas, linhas)."""
    data_ini, data_fim = _datas_mes(data_obj)
    cur.execute(f"""
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
    """)
    linhas = cur.fetchall()
    colunas = [d[0] for d in cur.description]
    return colunas, linhas


def inconsistencias_do_subgrupo(cur, data_obj, id_subgrupo):
    """Mesma query do relatório, restrita aos CÓDIGOS DE APÓLICE do subgrupo
    (APOLICES.SUBPORTO). Devolve [(apolice, seq, fatura, nome_administradora)].
    Apólice compartilhada por vários subgrupos aparece em todos — intencional."""
    data_ini, data_fim = _datas_mes(data_obj)
    cur.execute(f"""
        select f.apolice, f.seq, f.fatura, pes.nome
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
        and f.apolice in (select distinct a.apolice from apolices a where a.subporto = ?)
        group by f.apolice, f.seq, f.fatura, pes.nome
        order by 1, 4
    """, (id_subgrupo,))
    return [(r[0], r[1], r[2], (r[3] or "").strip()) for r in cur.fetchall()]


def montar_dataframe(conn, data_firebird, nomes_subgrupos):
    """Roda a lógica original (temp tables + procedure) para os subgrupos
    informados. Devolve (DataFrame, id_sub_arquivo, aviso).

    aviso: None ou texto de aviso não fatal (cobertura provisória não incluída).
    Não abre nenhuma janela: quem chama decide o que fazer com o resultado.
    """
    cur = conn.cursor()
    aviso = None

    cur.execute("DELETE FROM TEMP_RELATORIO_VIDA")
    cur.execute("DELETE FROM TEMP_RELATORIO_VIDA2")

    id_sub_arquivo = "Varios"  # Valor padrão caso selecione muitos

    for nome_sub in nomes_subgrupos:
        nome_sub = limpar_nome_subgrupo(nome_sub)
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

        # Segurados com cobertura provisória (só para os subgrupos configurados).
        # Falha aqui NÃO derruba o subgrupo: a transação é desfeita, a
        # planilha sai sem os provisórios e com aviso explícito.
        if str(id_subgrupo).strip() in SUBGRUPOS_COB_PROV:
            try:
                incluir_coberturas_provisorias(conn, cur, data_firebird, id_subgrupo)
            except Exception as e:
                aviso = (f"COBERTURA PROVISÓRIA NÃO INCLUÍDA no subgrupo {id_subgrupo}: {e}\n"
                         "A planilha foi gerada SEM os segurados provisórios. "
                         "Verifique a procedure GERA_REL_PLA_SISTEMA99.")

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

    if not df.empty:
        # --- FORMATAÇÃO DE DATAS ---
        colunas_data = ['NASC', 'DT_INI_VIG', 'DT_FIM_VIG']
        for col in colunas_data:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y')

    return df, id_sub_arquivo, aviso


def incluir_coberturas_provisorias(conn, cur, data_firebird, id_subgrupo):
    """Reproduz o fluxo do Delphi para os segurados com COBERTURA PROVISÓRIA
    (fatura temporária 99). Tudo numa transação única; em erro faz rollback e
    relança. Ver DOCUMENTACAO.md §4."""
    fat = FATURA_COB_PROV
    cur.execute("SELECT DISTINCT APOLICE FROM APOLICES WHERE SUBPORTO = ?", (id_subgrupo,))
    apolices = [r[0] for r in cur.fetchall()]
    if not apolices:
        return
    lista_apol = ",".join("'" + a.replace("'", "''") + "'" for a in apolices)

    chaves = ("p.administradora = m.administradora and p.posto = m.posto "
              "and p.seq_posto = m.seq_posto and p.matricula = m.matricula "
              "and p.seq_mat = m.seq_mat and p.apolice = m.apolice and p.seq = m.seq")
    try:
        # 1. marca as coberturas provisórias da vigência
        cur.execute(f"""
            UPDATE VIDA_COBERTURA_PROV D SET D.FATURA = {fat}
            WHERE D.FATURA IS NULL
              AND D.APOLICE IN ({lista_apol})
              AND D.DT_INI_COBERT = '{data_firebird}'
        """)
        if cur.rowcount == 0:
            conn.rollback()
            return  # nada provisório para esse subgrupo/vigência

        # 2. marca movimento e financeiro desses segurados.
        # STATUS <> 'C': a trigger VIDA_SEGURADOS_MOV_AU0 apaga os
        # movimentos/financeiros irmãos quando um MOV cancelado é atualizado.
        cur.execute(f"""
            UPDATE VIDA_SEGURADOS_MOV M SET M.FATURA = {fat}
            WHERE M.FATURA IS NULL
              AND M.STATUS <> 'C'
              AND EXISTS (SELECT 1 FROM VIDA_COBERTURA_PROV P
                          WHERE P.FATURA = {fat} AND {chaves})
        """)
        cur.execute(f"""
            UPDATE VIDA_SEGURADO_FIN M SET M.FATURA = {fat}
            WHERE M.FATURA = 0
              AND EXISTS (SELECT 1 FROM VIDA_COBERTURA_PROV P
                          WHERE P.FATURA = {fat} AND {chaves})
        """)

        # 3. gera e acumula
        cur.execute("EXECUTE PROCEDURE GERA_REL_PLA_SISTEMA99(?)", (fat,))
        cur.execute("INSERT INTO TEMP_RELATORIO_VIDA2 SELECT * FROM TEMP_RELATORIO_VIDA")

        # 3b. Complemento (não existe no Delphi): a procedure 99 junta
        # VIDA_SEGURADOS_MOV com "VSM.TIPO_FAT = VSM.TIPO_FAT", que é NULL
        # nos provisórios; preenche datas e subporto a partir do movimento 99.
        cur.execute(f"""
            UPDATE TEMP_RELATORIO_VIDA2 T SET
              T.DT_INI_VIG = (SELECT MIN(M.INICIO_VIG) FROM VIDA_SEGURADOS_MOV M
                              WHERE M.FATURA = {fat} AND M.ADMINISTRADORA = T.ADMINISTRADORA
                                AND M.POSTO = T.POSTO AND M.SEQ_POSTO = T.SEQ_POSTO
                                AND M.MATRICULA = T.MATRIC AND M.SEQ_MAT = T.SEQ_MAT
                                AND M.APOLICE = T.APOLICE AND M.SEQ = T.SEQ),
              T.DT_FIM_VIG = (SELECT MAX(M.FINAL_VIG) FROM VIDA_SEGURADOS_MOV M
                              WHERE M.FATURA = {fat} AND M.ADMINISTRADORA = T.ADMINISTRADORA
                                AND M.POSTO = T.POSTO AND M.SEQ_POSTO = T.SEQ_POSTO
                                AND M.MATRICULA = T.MATRIC AND M.SEQ_MAT = T.SEQ_MAT
                                AND M.APOLICE = T.APOLICE AND M.SEQ = T.SEQ),
              T.SUBPORTO = ?
            WHERE T.FATURA = {fat} AND T.DT_INI_VIG IS NULL
        """, (id_subgrupo,))

        # 4. limpeza — exatamente as três instruções do Delphi
        cur.execute(f"UPDATE VIDA_COBERTURA_PROV D SET D.FATURA = NULL WHERE D.FATURA = {fat}")
        cur.execute(f"UPDATE VIDA_SEGURADOS_MOV P SET P.FATURA = NULL WHERE P.FATURA = {fat}")
        cur.execute(f"UPDATE VIDA_SEGURADO_FIN P SET P.FATURA = 0 WHERE P.FATURA = {fat}")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def salvar_excel(df, caminho):
    """Grava o DataFrame e destaca em amarelo, na coluna FATURA, as linhas
    vindas da cobertura provisória (FATURA = 99)."""
    df.to_excel(caminho, index=False)
    if 'FATURA' not in df.columns:
        return
    marcar = df.index[pd.to_numeric(df['FATURA'], errors='coerce') == FATURA_COB_PROV].tolist()
    if not marcar:
        return
    wb = load_workbook(caminho)
    ws = wb.active
    col = list(df.columns).index('FATURA') + 1
    amarelo = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    negrito = Font(bold=True)
    for idx in marcar:
        cel = ws.cell(row=idx + 2, column=col)   # +1 cabeçalho, +1 base 1
        cel.fill = amarelo
        cel.font = negrito
    cab = ws.cell(row=1, column=col)
    cab.comment = Comment(f"Fatura {FATURA_COB_PROV} em amarelo = segurado com COBERTURA PROVISÓRIA",
                          "Sistema Envio Porto")
    wb.save(caminho)


def nome_arquivo(id_sub_arquivo, data_obj) -> str:
    return f"Subgrupo_{id_sub_arquivo}_Relatorio_{data_obj.strftime('%d-%m-%Y')}.xlsx"


def gerar_subgrupos(pasta, data_obj, nomes_subgrupos, log=print):
    """Etapa única para a web/robô: gera UM arquivo com os subgrupos informados.
    Devolve (caminho ou None, linhas, aviso)."""
    import os
    data_firebird = data_obj.strftime('%m/%d/%Y')
    conn = db.conectar()
    try:
        log(f"Gerando {len(nomes_subgrupos)} subgrupo(s) — vigência {data_obj:%d/%m/%Y}...")
        df, id_sub, aviso = montar_dataframe(conn, data_firebird, nomes_subgrupos)
    finally:
        conn.close()
    if aviso:
        log("[AVISO] " + aviso.splitlines()[0])
    if df.empty:
        log("Nenhum dado encontrado para os filtros selecionados.")
        return None, 0, aviso
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome_arquivo(id_sub, data_obj))
    salvar_excel(df, caminho)
    log(f"Planilha gravada: {caminho} ({len(df)} linhas)")
    return caminho, len(df), aviso
