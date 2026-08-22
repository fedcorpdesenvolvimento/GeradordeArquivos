/* Código 3 - Empresarial: EMPRESARIAIS (segurados_inc)
   Fonte: querys-porto-assit.sql. Parametro :inivig = data de inicio de vigencia. */
select
'INCEDNDIO' PRODUTO,ss.apolice,ss.administradora,pes.nome ADM,
ss.endereco,'' numero,ss.unidade complemento,ss.cep,ss.bairro,ss.cidade,ss.uf SIGLAestado,
ss.nome,ss.cpf_cnpj,ss.nascimento DataNascimento,'' NomeInquilino,
'' CpfCnpjINQUILINO
from segurados_inc ss left join pessoas pes on pes.pessoa = ss.administradora
where ss.status_seg <> 'C'
and ss.inicio_vig >= :inivig
and ((ss.apolice = '5008') or (ss.apolice='14008') or (ss.apolice = '7008') or (ss.apolice like '%C') or (ss.apolice like '%S'))
and ((ss.cpf_cnpj <> '') and (ss.cpf_cnpj <> '0'))
