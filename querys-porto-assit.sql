/* relação porto assistencia residencial  */
select
'BOAT' produto, M.apolice,m.administradora,pes.nome ADM,
VS.endereco,VS.numero,VS.complemento,VS.cep,VS.bairro,VS.cidade,VS.uf SIGLAestado,
VS.nome_segurado nome,VS.cpf_cnpj,VS.nascimento DataNascimento, '' NomeInquilino,
'' CpfCnpjINQUILINO
from vida_segurados_mov m LEFT JOIN vida_segurados VS ON VS.administradora=M.administradora
AND VS.posto=M.posto AND VS.seq_posto=M.seq_posto AND VS.matricula=M.matricula AND VS.seq_mat=M.seq_mat
                          LEFT JOIN PESSOAS PES ON PES.pessoa=M.administradora
                          left join vida_postos vp on vp.administradora=m.administradora AND Vp.posto=M.posto AND Vp.seq_posto=M.seq_posto
where m.apolice like 'BOAT%'
  AND M.status <> 'C'
  AND M.inicio_vig = :inivig
  and m.fatura > 0
/*RESIDENCIAS SEM A apolice 15008*/
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

/*RESIDENCIAS da apolice  15008*/
select
'INCEDNDIO' PRODUTO,ss.apolice,ss.administradora,pes.nome ADM,
ss.endereco,'' numero,ss.unidade complemento,ss.cep,ss.bairro,ss.cidade,ss.uf SIGLAestado,
ss.nome,ss.cpf_cnpj,ss.nascimento DataNascimento,'' NomeInquilino,
'' CpfCnpjINQUILINO
from segurados_inc ss left join pessoas pes on pes.pessoa = ss.administradora
where ss.status_seg <> 'C'
and ss.inicio_vig >= :inivig
and ss.apolice = '15008'
and ((ss.cpf_cnpj <> '') and (ss.cpf_cnpj <> '0'))




/*EMPRESARIAIS*/
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