/* Vigência (03/11/2026): entra também a fatura/segurado cuja vigência em curso contém :inivig — apólices não mensais (ANUAL, N MESES) com segurados ativos. */
/* PORTO DENTAL — Query 1: faturas da vigência a serem enviadas.
   Parâmetro :inivig = data de início de vigência.

   Contrato com o gerador (modulos/gerador_dental.py):
   - FATURA alimenta a query 2; VIDAS (alias de qtd_itens) é somada no
     totalizador de vidas; as demais colunas aparecem no log.
   Fonte: query passada pelo usuário em 27/08/2026 (versão com nome da
   administradora e descrição do produto; data fixa trocada por :inivig;
   qtd_itens ganhou o alias VIDAS para o totalizador). */
SELECT F.fatura,AP.apolice,pes.nome,F.qtd_itens VIDAS,fdp.des_prod,fdp.des_prod_master
from FATURAS F LEFT JOIN APOLICES AP ON AP.administradora=F.administradora AND AP.apolice=F.apolice AND AP.seq = F.seq
               left join pessoas pes on pes.pessoa=f.administradora
               left join fatura_dsc_prod fdp on fdp.fatura=f.fatura
WHERE AP.status = 'A'
  AND AP.tipo_dental = 'P'
  AND ((F.dt_ini_vig = :inivig) OR (:inivig BETWEEN F.dt_ini_vig AND F.dt_fim_vig))
order by 3,2
