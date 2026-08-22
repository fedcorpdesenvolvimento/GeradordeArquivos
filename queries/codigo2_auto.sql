/* Código 2 - Auto: apolices BOAT (vida_segurados_mov)
   Fonte: querys-porto-assit.sql. Parametro :inivig = data de inicio de vigencia. */
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
