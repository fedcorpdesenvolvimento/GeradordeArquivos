/* GERAR ARQUIVO FUNERAL — segurados de Vida com cobertura de FUNERAL ou
   CERIMONIAL nas faturas ativas da vigência. Parâmetro :inivig.

   Critério de vigência (decisão do usuário, 03/11/2026, vale para todos
   os geradores): a fatura entra se :inivig está entre DT_INI_VIG e
   DT_FIM_VIG ou se começa exatamente em :inivig — assim apólices não
   mensais (APOLICES.NOME_VIGENCIA = ANUAL, 60 MESES, ...) com segurados
   ativos também são enviadas.

   Fontes: FATURAS (ramo V, status A) -> VIDA_SEGURADO_FIN (cobertura)
   -> VIDA_SEGURADOS_MOV (movimento do segurado na fatura, não cancelado)
   -> VIDA_SEGURADOS (nome, CPF, nascimento) -> PESSOAS (administradora).
   A cobertura é identificada pelo NOME em COBERTURAS contendo FUNERAL ou
   CERIMONIAL (9 coberturas em 03/11/2026: 0009, 0015, 0084, 0129, 0189,
   0209, 0216, 0219, 0244). Duplicidade de CPF é removida no Python
   (modulos/gerador_funeral.py), mantendo a primeira ocorrência. */
SELECT DISTINCT
       PES.NOME          ADMINISTRADORA,
       F.APOLICE         APOLICE,
       VS.NOME_SEGURADO  NOME,
       VS.CPF_CNPJ       CPF,
       VS.NASCIMENTO     NASCIMENTO
FROM FATURAS F
JOIN VIDA_SEGURADO_FIN VSF ON VSF.FATURA = F.FATURA AND VSF.TIPO_FAT = F.TIPO_FAT
JOIN COBERTURAS C ON C.COD_COBERTURA = VSF.COD_COBERTURA
JOIN VIDA_SEGURADOS_MOV VSM ON VSM.ADMINISTRADORA = VSF.ADMINISTRADORA
                           AND VSM.POSTO = VSF.POSTO AND VSM.SEQ_POSTO = VSF.SEQ_POSTO
                           AND VSM.MATRICULA = VSF.MATRICULA AND VSM.SEQ_MAT = VSF.SEQ_MAT
                           AND VSM.APOLICE = VSF.APOLICE AND VSM.SEQ = VSF.SEQ
                           AND VSM.FATURA = VSF.FATURA
LEFT JOIN VIDA_SEGURADOS VS ON VS.ADMINISTRADORA = VSF.ADMINISTRADORA
                           AND VS.POSTO = VSF.POSTO AND VS.SEQ_POSTO = VSF.SEQ_POSTO
                           AND VS.MATRICULA = VSF.MATRICULA AND VS.SEQ_MAT = VSF.SEQ_MAT
LEFT JOIN PESSOAS PES ON PES.PESSOA = F.ADMINISTRADORA
WHERE F.STATUS = 'A'
  AND F.RAMO = 'V'
  AND ((:inivig BETWEEN F.DT_INI_VIG AND F.DT_FIM_VIG) OR (F.DT_INI_VIG = :inivig))
  AND VSM.STATUS <> 'C'
  AND (UPPER(C.NOME_COBERTURA) LIKE '%FUNERAL%' OR UPPER(C.NOME_COBERTURA) LIKE '%CERIMONIAL%')
ORDER BY 1, 2, 3
