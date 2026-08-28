/* DENTAL SEMPRE ODONTO — Query 1: faturas da vigência a serem enviadas.
   Idêntica à portodental_1.sql, com AP.tipo_dental = 'S' em vez de 'P'
   (decisão do usuário, 28/08/2026). Parâmetro :inivig.

   Contrato com o gerador (modulos/gerador_dental.py):
   - FATURA alimenta a query 2; VIDAS (alias de qtd_itens) é somada no
     totalizador de vidas; as demais colunas aparecem no log. */
SELECT F.fatura,AP.apolice,pes.nome,F.qtd_itens VIDAS,fdp.des_prod,fdp.des_prod_master
from FATURAS F LEFT JOIN APOLICES AP ON AP.administradora=F.administradora AND AP.apolice=F.apolice AND AP.seq = F.seq
               left join pessoas pes on pes.pessoa=f.administradora
               left join fatura_dsc_prod fdp on fdp.fatura=f.fatura
WHERE AP.status = 'A'
  AND AP.tipo_dental = 'S'
  AND F.dt_ini_vig = :inivig
order by 3,2
