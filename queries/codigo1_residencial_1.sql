/* Código 1 - Residencial (parte 1): RESIDENCIAS SEM A apolice 15008
   Fonte: querys-porto-assit.sql. Parametro :inivig = data de inicio de vigencia. */
select
'INCEDNDIO' PRODUTO,ss.apolice,ss.administradora,pes.nome ADM,
ss.endereco,'' numero,ss.unidade complemento,ss.cep,ss.bairro,ss.cidade,ss.uf SIGLAestado,
ss.nome,ss.cpf_cnpj,ss.nascimento DataNascimento,'' NomeInquilino,
'' CpfCnpjINQUILINO
from segurados_inc ss left join pessoas pes on pes.pessoa = ss.administradora
where ss.status_seg <> 'C'
and ss.inicio_vig >= :inivig
and ((ss.apolice = '4008')  or (ss.apolice='10008') or (ss.apolice='13008') or (ss.apolice='6008') or (ss.apolice = '9008') or (ss.apolice like '%R'))
and ((ss.cpf_cnpj <> '') and (ss.cpf_cnpj <> '0'))
