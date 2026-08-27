/* PORTO DENTAL — Query 1: faturas da vigência a serem enviadas.
   Parâmetro :inivig = data de início de vigência.

   Contrato com o gerador (modulos/gerador_dental.py):
   - FATURA alimenta a query 2; VIDAS (alias de qtd_itens) é somada no
     totalizador de vidas; as demais colunas aparecem no log.
   Fonte: query passada pelo usuário em 27/08/2026 (data fixa trocada
   por :inivig; qtd_itens ganhou o alias VIDAS para o totalizador). */
SELECT F.fatura, AP.apolice, F.administradora, F.qtd_itens VIDAS
from FATURAS F LEFT JOIN APOLICES AP ON AP.administradora=F.administradora AND AP.apolice=F.apolice AND AP.seq = F.seq
WHERE AP.status = 'A'
  AND AP.tipo_dental = 'P'
  AND F.dt_ini_vig = :inivig
