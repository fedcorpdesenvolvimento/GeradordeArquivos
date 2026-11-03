/* Procedure GERA_REL_PLA_SISTEMA99 — versão APLICADA no banco pelo Alberto
   em 03/11/2026 (fonte extraído de RDB$PROCEDURES após a alteração).
   Mudanças em relação à versão anterior:
     - declare variable COBERTURA varchar(30) -> varchar(50)
     - declare variable BAIRRO    varchar(30) -> varchar(50)
   Motivo: 27 coberturas têm nome > 30 caracteres (ex.: 'AUX DIAGNOSTICO
   CANCER MAMA E PROSTATA'); BAIRRO costumava dar o mesmo erro SQLCODE -802
   "string right truncation", derrubando a procedure para o segurado
   provisório inteiro. Este arquivo serve para reaplicar em outro banco
   (homologação/restauração). NÃO é executado pelo sistema. */
SET TERM ^ ;
ALTER PROCEDURE GERA_REL_PLA_SISTEMA99 (FATURA INTEGER)
AS
declare variable ADMINISTRADORA varchar(10);
declare variable APOLICE varchar(20);
declare variable SEQ integer;
declare variable MATRICULA varchar(30);
declare variable NOME varchar(50);
declare variable NASC date;
declare variable DOCUMENTO varchar(14);
declare variable PREMIO decimal(15,2);
declare variable COBERTURA varchar(50);
declare variable CAPITAL_FEDCORP decimal(15,2);
declare variable I integer;
declare variable MAT varchar(30);
declare variable VCONTINUE integer;
declare variable PREMIO_SEGURADORA decimal(15,2);
declare variable STATUS varchar(1);
declare variable PRODUTO varchar(50);
declare variable PROD varchar(50);
declare variable FAT integer;
declare variable TP_FAT varchar(1);
declare variable DT_INI_VIG date;
declare variable DT_FIM_VIG date;
declare variable NOME_POSTO varchar(60);
declare variable CNPJ varchar(14);
declare variable COESTIP varchar(50);
declare variable ENDERECO varchar(90);
declare variable UNIDADE varchar(40);
declare variable UF varchar(2);
declare variable BAIRRO varchar(50);
declare variable CIDADE varchar(30);
declare variable CEP varchar(8);
declare variable CEDENTE varchar(2);
declare variable SEQ_MAT integer;
declare variable POSTO varchar(10);
declare variable SEQ_POSTO integer;
declare variable PST varchar(10);
declare variable SEQM integer;
declare variable PREMTOT decimal(15,2);
declare variable BENEFICIO varchar(1);
declare variable BENE varchar(3);
declare variable COMPLEMENTO varchar(40);
declare variable SEXO varchar(1);
declare variable SQ integer;
declare variable PREMSEG decimal(15,2);
declare C cursor for (
    select ADMINISTRADORA, APOLICE, SEQ, MATRICULA, SEQ_MAT, NOME, NASC,
           case
             when character_length(trim(DOCUMENTO)) > 11 then lpad(DOCUMENTO, 14, 0)
             else lpad(DOCUMENTO, 11, 0)
           end DOCUMENTO,
           PREMIO, COBERTURA, CAPITAL_FEDCORP, PREMIO_SEGURADORA, STATUS, PRODUTO, PROD, FATURA, TIPO_FAT, DT_INI_VIG,
           DT_FIM_VIG, NOME_POSTO, CNPJ, CO_ESTIP, ENDERECO, UNIDADE, UF, BAIRRO, CIDADE, CEP, CEDENTE, POSTO,
           SEQ_POSTO, BENEFICIO, COMPLEMENTO, SEXO
    from (select COB.ORDEM, VSF.APOLICE, VSF.SEQ, VSM.INICIO_VIG DT_INI_VIG, VSM.FINAL_VIG DT_FIM_VIG, '99' FATURA,
                 'A' TIPO_FAT, VP.POSTO, VP.SEQ_POSTO, VP.NOME_POSTO, VP.CNPJ,
                 (select P.NOM_PRODUTO
                  from PRODUTO P
                  where P.COD_PRODUTO = VSF.COD_PRODUTO) PROD, VSF.MATRICULA, VSF.SEQ_MAT, VS.NOME_SEGURADO NOME,
                 VS.NASCIMENTO NASC, VS.CPF_CNPJ DOCUMENTO, VSM.STATUS, VSF.COD_PRODUTO, PRD.NOM_PRODUTO PRODUTO,
                 VSF.COD_COBERTURA, COB.NOME_COBERTURA COBERTURA,
                 (
                 case VSF.APOLICE
                   when '216' then VSF.CAPITAL_SEGURADORA
                   else VSF.CAPITAL_FEDCORP
                 end) CAPITAL_FEDCORP,
                 VSF.PREMIO_SEGURADORA, VSF.PREMIO_FEDCORP PREMIO, PES.NOME CO_ESTIP, VS.ENDERECO,
                 VS.COMPLEMENTO UNIDADE, VS.UF, VS.BAIRRO, VS.CIDADE, VS.CEP, VSF.ADMINISTRADORA, '02' CEDENTE,
                 COB.BENEFICIO, VS.COMPLEMENTO, VS.SEXO
          from VIDA_SEGURADO_FIN VSF
          left join PRODUTO PRD on PRD.COD_PRODUTO = VSF.COD_PRODUTO
          left join COBERTURAS COB on COB.COD_COBERTURA = VSF.COD_COBERTURA
          left join VIDA_SEGURADOS VS on VS.ADMINISTRADORA = VSF.ADMINISTRADORA and
                VS.POSTO = VSF.POSTO and
                VS.SEQ_POSTO = VSF.SEQ_POSTO and
                VS.MATRICULA = VSF.MATRICULA and
                VS.SEQ_MAT = VSF.SEQ_MAT
          left join VIDA_POSTOS VP on VP.ADMINISTRADORA = VSF.ADMINISTRADORA and
                VP.POSTO = VSF.POSTO and
                VP.SEQ_POSTO = VSF.SEQ_POSTO
          left join VIDA_SEGURADOS_MOV VSM on VSM.ADMINISTRADORA = VSF.ADMINISTRADORA and
                VSM.POSTO = VSF.POSTO and
                VSM.SEQ_POSTO = VSF.SEQ_POSTO and
                VSM.MATRICULA = VSF.MATRICULA and
                VSM.SEQ_MAT = VSF.SEQ_MAT and
                VSM.FATURA = VSF.FATURA and
                VSM.TIPO_FAT = VSM.TIPO_FAT
          left join PESSOAS PES on PES.PESSOA = VSF.ADMINISTRADORA
          where VSF.FATURA = 99
          order by VSF.POSTO, VSF.SEQ_POSTO, VSF.MATRICULA || '-' || VSF.SEQ_MAT, COB.ORDEM, COB.BENEFICIO, COB.NOME_COBERTURA));
BEGIN
  DELETE FROM TEMP_RELATORIO_VIDA  ;
  open c ;
  VCONTINUE = 1 ;
  FETCH C INTO ADMINISTRADORA,apolice,seq,matricula,seq_mat,nome,nasc,documento,premio,cobertura,capital_fedcorp,premio_seguradora,status,produto,prod, fat,TP_FAT,dt_ini_vig,dt_fim_vig,NOME_POSTO,CNPJ,coestip,ENDERECO,UNIDADE,UF,bairro,CIDADE,CEP,CEDENTE,POSTO,SEQ_POSTO,BENEFICIO,complemento,SEXO;
  WHILE (VCONTINUE=1) DO
  BEGIN
    if (ROW_COUNT=0) then
        BREAK ;                                                                                                                                 
    INSERT INTO temp_relatorio_vida (ADMINISTRADORA,APOLICE,SEQ, MATRIC,seq_mat, NOME, NASC, DOCUMENTO,PREMIO,PREMIO_SEGURADORA,STATUS,PRODUTO,prod, fatura,TIPO_FAT,dt_ini_vig,dt_fim_vig,NOME_POSTO,CNPJ,coestip,ENDERECO,UNIDADE,UF,BAIRRO,CIDADE,cep,CEDENTE, POSTO,SEQ_POSTO,complemento,sexo) VALUES (:administradora, :APOLICE,:seq ,:matricula,:seq_mat, :NOME, :nasc, :documento,:premio,:premio_seguradora,:status,:produto,:prod, :fat,:TP_FAT,:dt_ini_vig,:dt_fim_vig,:nome_posto,:CNPJ,:coestip,:endereco,:UNIDADE,:uf, :bairro, :cidade, :cep,:cedente,:posto,:seq_posto,:complemento,:sexo);
    MAT = :matricula ;
    PST = :POSTO ;
    SEQM= :seq_mat ;
    I = 1 ;
    PREMTOT = 0 ;
    PREMSEG = 0 ;
    SQ= :seq_posto ;
    WHILE (MAT=:matricula AND SEQM=:seq_mat AND PST=:posto AND SQ=:seq_posto) DO
          BEGIN
           premtot = PREMTOT + :premio ;
           premseg = premseg + :premio_seguradora ;
           bene = 'NAO' ;
           if (:beneficio='S') then
             bene = 'SIM' ;
           UPDATE temp_relatorio_vida T SET T.premio=:premtot,T.premio_seguradora=:premseg WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=1) then
             UPDATE temp_relatorio_vida T SET T.cobertura1=:cobertura,T.valor1=:capital_fedcorp,T.beneficio1=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=2) then
             UPDATE temp_relatorio_vida T SET T.cobertura2=:cobertura, T.valor2=:capital_fedcorp,T.beneficio2=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=3) then
             UPDATE temp_relatorio_vida T SET T.cobertura3=:cobertura, T.valor3=:capital_fedcorp,T.beneficio3=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=4) then
             UPDATE temp_relatorio_vida T SET T.cobertura4=:cobertura, T.valor4=:capital_fedcorp,T.beneficio4=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=5) then
             UPDATE temp_relatorio_vida T SET T.cobertura5=:cobertura, T.valor5=:capital_fedcorp,T.beneficio5=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=6) then
             UPDATE temp_relatorio_vida T SET T.cobertura6=:cobertura, T.valor6=:capital_fedcorp,T.beneficio6=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=7) then
             UPDATE temp_relatorio_vida T SET T.cobertura7=:cobertura, T.valor7=:capital_fedcorp,T.beneficio7=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;

           if (I=8) then                                                                                                                                                                                        
             UPDATE temp_relatorio_vida T SET T.cobertura8=:cobertura, T.valor8=:capital_fedcorp,T.beneficio8=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=9) then
             UPDATE temp_relatorio_vida T SET T.cobertura9=:cobertura, T.valor9=:capital_fedcorp,T.beneficio9=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=10) then
             UPDATE temp_relatorio_vida T SET T.cobertura10=:cobertura, T.valor10=:capital_fedcorp,T.beneficio10=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=11) then
             UPDATE temp_relatorio_vida T SET T.cobertura11=:cobertura, T.valor11=:capital_fedcorp,T.beneficio11=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=12) then
             UPDATE temp_relatorio_vida T SET T.cobertura12=:cobertura, T.valor12=:capital_fedcorp,T.beneficio12=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=13) then
             UPDATE temp_relatorio_vida T SET T.cobertura13=:cobertura, T.valor13=:capital_fedcorp,T.beneficio13=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=14) then
             UPDATE temp_relatorio_vida T SET T.cobertura14=:cobertura, T.valor14=:capital_fedcorp,T.beneficio14=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=15) then
             UPDATE temp_relatorio_vida T SET T.cobertura15=:cobertura, T.valor15=:capital_fedcorp,T.beneficio15=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=16) then
             UPDATE temp_relatorio_vida T SET T.cobertura16=:cobertura, T.valor16=:capital_fedcorp,T.beneficio16=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=17) then
             UPDATE temp_relatorio_vida T SET T.cobertura17=:cobertura, T.valor17=:capital_fedcorp,T.beneficio17=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=18) then
             UPDATE temp_relatorio_vida T SET T.cobertura18=:cobertura, T.valor18=:capital_fedcorp,T.beneficio18=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=19) then
             UPDATE temp_relatorio_vida T SET T.cobertura19=:cobertura, T.valor19=:capital_fedcorp,T.beneficio19=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;
           if (I=20) then
             UPDATE temp_relatorio_vida T SET T.cobertura20=:cobertura, T.valor20=:capital_fedcorp,T.beneficio20=:bene WHERE T.matric=:MAT and T.posto = :posto AND T.seq_posto=:seq_posto AND T.seq_mat=:seq_mat ;


           FETCH C INTO ADMINISTRADORA,apolice,seq,matricula,seq_mat,nome,nasc,documento,premio,cobertura,capital_fedcorp,premio_seguradora,status,produto,prod, fat,TP_FAT,dt_ini_vig,dt_fim_vig,NOME_POSTO,CNPJ,coestip,ENDERECO,UNIDADE,UF,bairro,CIDADE,CEP,CEDENTE,POSTO,SEQ_POSTO,BENEFICIO,complemento,sexo;
           I = I + 1 ;
           if (ROW_COUNT=0) then
              BREAK ;
        END
  END
  close c ;
END
^
SET TERM ; ^
COMMIT^
