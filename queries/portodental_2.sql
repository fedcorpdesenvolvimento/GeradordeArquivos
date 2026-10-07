/* PORTO DENTAL — Query 2: segurados das faturas (planilha final).
   O marcador :faturas é substituído pelo gerador com os números de
   fatura vindos da query 1 (em blocos, limite do IN no Firebird).
   As colunas do resultado viram o cabeçalho da planilha, nesta ordem.
   11/09/2026: incluída VSM.apolice (código da apólice) após a fatura, a
   pedido do usuário (mesma alteração do Sempre Odonto, para as duas
   queries 2 continuarem idênticas) — coluna APOLICE na planilha.
   Fonte: query passada pelo usuário em 27/08/2026, com dois ajustes:
   - "VSM.fatura = :FATURA" -> "VSM.fatura IN (:faturas)" (busca em blocos);
   - "VS.seq_mat=VS.seq_mat" -> "VS.seq_mat=VSM.seq_mat" (comparava a
     coluna com ela mesma; corrigido no padrão do join do codigo2_auto). */
SELECT VSM.fatura,VSM.apolice,VSM.administradora,PES.nome,VP.nome_posto,
       VS.nome_segurado,VS.cpf_cnpj,VS.sexo,VS.nascimento,VS.nome_mae
FROM vida_segurados_mov VSM LEFT JOIN vida_segurados VS ON VS.administradora=VSM.administradora
                                                       AND VS.posto=VSM.posto
                                                       AND VS.seq_posto=VSM.seq_posto
                                                       AND VS.matricula=VSM.matricula
                                                       AND VS.seq_mat=VSM.seq_mat
                            LEFT JOIN PESSOAS PES ON PES.pessoa = VSM.administradora
                            LEFT JOIN vida_postos VP ON VP.administradora=VSM.administradora
                                                    AND VP.posto=VSM.posto
                                                    AND VP.seq_posto=VSM.seq_posto
WHERE VSM.fatura IN (:faturas)
  AND VSM.status <> 'C'
