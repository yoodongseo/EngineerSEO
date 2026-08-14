--*  ACT TOOL EXTRACTION SCRIPT FOR ORACLE DATABASE 11g AND ABOVE
 
--* REVISION HISTORY:
--* --------------------------------------------------------------------------------
--*   VERSION        DATE          AUTHOR                 ACTIVITY                                                    
--*   1.0            2/27/2013     SUCHITRA PRABHALA      SCRIPT CREATED                                       
--*   2.0            11/05/2013    SUCHITRA PRABHALA      SCRIPT MODIFIED
--*   3.0            10/06/2014    SUCHITRA PRABHALA      SCRIPT MODIFIED
--*   4.0            02/06/2015    SUCHITRA PRABHALA      SCRIPT MODIFIED - Req 952,1126
--*	  5.0			 03/11/2016	   Shashank Ramakrishna	  SCRIPT MODIFIED - Added table DBA_Objects and masked spare1 till spare6 under SYS.USER$ Req-1222, 1207
--*	  5.1			 06/28/2016	   Shashank Ramakrishna	  SCRIPT MODIFIED - Unmasked SPARE6 from SYS.USER$ table
--*	  				 07/28/2016	   Shashank Ramakrishna	  SCRIPT MODIFIED - removed SQL_TEXT column from the TABLE DBA_FGA_AUDIT_TRAIL to solve issue related to string concatenation
--*	  6.0			 03/21/2017	   Shashank Ramakrishna	  SCRIPT MODIFIED - removed SYS.LINK.ACTT, DBA_DB_LINKS.ACTT , DBA_FGA_AUDIT_TRAIL.ACTT, 	ALL_DEF_AUDIT_OPTS.ACTT
--*																		  -	Modified extraction query for VPARAMETER.ACTT
--*																		  -	Added V$INSTANCE table extraction
--*	  14.0			 08/09/2017	   Prakash Achanta		  SCRIPT MODIFIED - Modified ACTT_CONFIG_TABLERECORDCOUNT to support record count validation
--*					 08/26/2017	   Shashank Ramakrishna					  -	Changed extension of file VINSTANCE.ACTT to VINSTANCE.TXT
--*																		  -	Changed extension of file ACTT_CONFIG_TABLERECORDCOUNT.TXT to ACTT_CONFIG_TABLERECORDCOUNT.ACTT
--*																		  -	Modified extraction of V$PARAMETER to have case insensitive extraction
--*	  15.0			 01/29/2018	   Madhavi Mallavarapu	  SCRIPT MODIFIED - Removed PASSWORD and SPARE4 column from SYS.USER$
--*					 02/08/2018	   										  -	Updated query for VINSTANCE.TXT to fix the issue related to shuffling of column names
--*   15.1  		 07/31/2018    Madhavi Mallavarapu    SCRIPT MODIFIED - Added code to disable the timer to avoid the elapsed time entries in .ACTT files
--*   		 		 07/31/2018     					  SCRIPT MODIFIED - Updated query for SYS.DBA_OBJ_AUDIT_OPTS to obtain the row count
--*   16.0           05/12/2019    Madhavi Mallavarapu    SCRIPT MODIFIED - Audit start and end date accepted from client at the extractor level      
--*					 03/14/2019    Madhavi Mallavarapu    SCRIPT MODIFIED - Extracting DBA_REGISTRY_HISTORY & DBA_REGISTRY_SQLPATCH at DB level patch details
--*   16.1           11/20/2019    Madhavi Mallavarapu    SCRIPT MODIFIED - Changed extension of files 12C_DBA_REGISTRY_SQLPATCH.ACTT and 11G_DBA_REGISTRY_HISTORY.ACTT from ".ACTT" to "TXT"
--*   17.0           02/26/2019    Madhavi Mallavarapu    SCRIPT MODIFIED - Changed the position of NLS_TERRITORY, NLS_LANGUAGE parameters prior to accepting AUDIT dates
--*					 02/30/2020    Madhavi Mallavarapu    SCRIPT MODIFIED - Extracting list of temporary objects under DBA_OBJECTS_TEMPORARY										
--*                                                                       - Changed extension of file VINSTANCE.TXT to VINSTANCE.ACTT
--*                                                                       - Added static file ACTT_SYSTEM_Oracle_Database.ACTT for engine level Mapping
--*


--*																			
--*  NOTICE:
--*  -------------------------------------------------------------------------------
--*		The purpose of this “read only” script is to download data that can be analyzed as part of our audit.  
--*		We expect that you will follow your company’s regular change management policies and procedures prior to running the script.
--*		To the extent permitted by law, regulation and our professional standards, this script is provided “as is,” 
--*		without any warranty, and the Deloitte Network and its contractors will not be liable for any damages relating to this script or its use.  
--*		As used herein, “we” and “our” refers to the Deloitte Network entity that provided the script to you, and the “Deloitte Network” refers to 
--*		Deloitte Touche Tohmatsu Limited (“DTTL”), the member firms of DTTL, and each of their affiliates and related entities.
--*
--*		© 2016.  For more information, contact Deloitte Touche Tohmatsu Limited.  All rights reserved.
--*  -------------------------------------------------------------------------------


--*  --------------------- ACTUAL SCRIPT BEGINS FROM HERE --------------------------
set echo off
set ver off
set heading off

clear screen
CLEAR BUFFER

prompt
prompt
prompt
prompt
prompt Note: DBA privileges on "SYS" schema are required 
prompt since the script extracts data from this schema.
prompt Please confirm if the USERID that you used to login to 
prompt Oracle DB has the required DBA privileges
prompt 
prompt At any point during execution you can 
prompt kill the script by pressing < ctrl + c > 
prompt 
prompt Select ENTER to proceed with extraction.
prompt 

pause


SET TIMING OFF
ALTER SESSION SET NLS_TERRITORY = AMERICA NLS_LANGUAGE = AMERICAN;

ACCEPT AUDIT_START_DATE DATE FORMAT 'DD-MON-YYYY' prompt "Enter AUDIT_START_DATE in the format DD-MON-YYYY: "
ACCEPT AUDIT_END_DATE DATE FORMAT 'DD-MON-YYYY' prompt "Enter AUDIT_END_DATE in the format DD-MON-YYYY: "

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
SET SHOW OFF VER OFF
SET LINE 4000

DEFINE C_SEP   = '|^|';
DEFINE V_COUNT = 0;
DEFINE C_MAX_PRECISION = 38;
DEFINE C_MAX_SCALE = 127;
COLUMN row_cnt_col  NOPRINT NEW_VALUE row_cnt

SET TRIMSPOOL ON

/******************************************** writing the control data into the file ****************************************/

Spool ACTT_CONFIG_SETTINGS.ACTT

SELECT 'SettingName VARCHAR(100)'||'&C_SEP'||'SettingValue VARCHAR(1000)' FROM DUAL;
SELECT 'Extract Script Version'||'&C_SEP'||'17.0' FROM DUAL;
SELECT 'Database Version'||'&C_SEP'||BANNER FROM V$VERSION WHERE BANNER LIKE '%Oracle%';
SELECT 'Extract Script Start Time'||'&C_SEP'||TO_CHAR(SYSDATE, 'DD-MON-YYYY HH:MI PM')  FROM DUAL;


SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

/**************************** writing the seperator i.e., feild terminator or delimiter data into the file ********************/

SPOOL ACTT_CONFIG_FIELDTERMINATOR.ACTT

SELECT '&C_SEP' FROM DUAL;

SPOOL OFF

SPOOL ACTT_SYSTEM_Oracle_Database.ACTT

SELECT 'Script_Version VARCHAR(10)' FROM DUAL;
SELECT '17.0' FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

/************************* writing the header line of this file ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT 

SELECT 'TableName VARCHAR(300)'||'&C_SEP'||'RecordCount VARCHAR(MAX)' FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/


/**************************************** WRITING EACH QUERY OUTPUT DATA INTO AN INPUT FILE ***********************************************/



SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT
PROMPT TRYING TO EXTRACT DATA FROM DBA_SYS_PRIVS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
/*1==============START OF QUERY FROM DBA_SYS_PRIVS TABLE ==============*/

Select '0'  AS row_cnt_col FROM DUAL;
SET TRIMSPOOL ON

SPOOL DBA_SYS_PRIVS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_SYS_PRIVS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('GRANTEE','PRIVILEGE','ADMIN_OPTION');

SELECT
replace(replace(ADMIN_OPTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRANTEE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PRIVILEGE,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col 
FROM SYS.DBA_SYS_PRIVS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*1 ==============END OF QUERY FROM DBA_SYS_PRIVS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_SYS_PRIVS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_USERS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
/*2==============START OF QUERY FROM DBA_USERS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_USERS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_USERS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('ACCOUNT_STATUS','CREATED','DEFAULT_TABLESPACE','EDITIONS_ENABLED','EXPIRY_DATE','EXTERNAL_NAME','INITIAL_RSRC_CONSUMER_GROUP','LOCK_DATE','PASSWORD','PASSWORD_VERSIONS','PROFILE','TEMPORARY_TABLESPACE','USERNAME','USER_ID');

SELECT 
replace(replace(ACCOUNT_STATUS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
CREATED ||'&C_SEP' ||
replace(replace(DEFAULT_TABLESPACE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(EDITIONS_ENABLED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
EXPIRY_DATE ||'&C_SEP' ||
replace(replace(EXTERNAL_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(INITIAL_RSRC_CONSUMER_GROUP,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
LOCK_DATE ||'&C_SEP' ||
decode(PASSWORD, upper('EXTERNAL'),PASSWORD,length(replace(replace(PASSWORD,CHR(13),''),CHR(10),' '))) ||'&C_SEP' ||
replace(replace(PASSWORD_VERSIONS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PROFILE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(TEMPORARY_TABLESPACE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(USERNAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
USER_ID,COUNT (*) OVER () AS row_cnt_col 
FROM  SYS.DBA_USERS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*2 ==============END OF QUERY FROM DBA_USERS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_USERS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_TAB_PRIVS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
/*3==============START OF QUERY FROM DBA_TAB_PRIVS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_TAB_PRIVS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_TAB_PRIVS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('GRANTABLE','GRANTEE','GRANTOR','HIERARCHY','OWNER','PRIVILEGE','TABLE_NAME');

SELECT 
replace(replace(GRANTABLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRANTEE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRANTOR,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(HIERARCHY,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PRIVILEGE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(TABLE_NAME,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col 
FROM  SYS.DBA_TAB_PRIVS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*3 ==============END OF QUERY FROM DBA_TAB_PRIVS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_TAB_PRIVS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_ROLE_PRIVS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
/*4==============START OF QUERY FROM DBA_ROLE_PRIVS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_ROLE_PRIVS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_ROLE_PRIVS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('ADMIN_OPTION','DEFAULT_ROLE','GRANTED_ROLE','GRANTEE');

SELECT 
replace(replace(ADMIN_OPTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(DEFAULT_ROLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRANTED_ROLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRANTEE,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col
FROM  SYS.DBA_ROLE_PRIVS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*4 ==============END OF QUERY FROM DBA_ROLE_PRIVS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_ROLE_PRIVS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM V$PWFILE_USERS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*5==============START OF QUERY FROM V$PWFILE_USERS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL VPWFILE_USERS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'V_$PWFILE_USERS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('SYSASM','SYSDBA','SYSOPER','USERNAME');

SELECT 
replace(replace(SYSASM,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SYSDBA,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SYSOPER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
USERNAME,COUNT (*) OVER () AS row_cnt_col 
FROM  SYS.V_$PWFILE_USERS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*5 ==============END OF QUERY FROM V$PWFILE_USERS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.V_$PWFILE_USERS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM PRODUCT_USER_PROFILE;
SPOOL OFF


SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*6==============START OF QUERY FROM PRODUCT_USER_PROFILE TABLE ==============*/
SET TRIMSPOOL ON


SPOOL PRODUCT_USER_PROFILE.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'PRODUCT_PRIVS' 
AND UPPER(OWNER) ='SYSTEM'
AND COLUMN_NAME IN ('ATTRIBUTE','CHAR_VALUE','DATE_VALUE','NUMERIC_VALUE','PRODUCT','SCOPE','USERID');

SELECT 
replace(replace(ATTRIBUTE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(CHAR_VALUE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
DATE_VALUE ||'&C_SEP' ||
NUMERIC_VALUE ||'&C_SEP' ||
replace(replace(PRODUCT,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SCOPE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(USERID,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  PRODUCT_USER_PROFILE
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*6 ==============END OF QUERY FROM PRODUCT_USER_PROFILE TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'PRODUCT_USER_PROFILE'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_PROFILES;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*7==============START OF QUERY FROM  DBA_PROFILES TABLE ==============*/
SET TRIMSPOOL ON


SPOOL  DBA_PROFILES.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_PROFILES' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('LIMIT','PROFILE','RESOURCE_NAME','RESOURCE_TYPE');

SELECT 
replace(replace(LIMIT,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PROFILE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(RESOURCE_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(RESOURCE_TYPE,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col 
FROM   SYS.DBA_PROFILES
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*7 ==============END OF QUERY FROM  DBA_PROFILES TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_PROFILES'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM SYS.USER$;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*8==============START OF QUERY FROM SYS.USER$ TABLE ==============*/
/*8==============ReqID: 1207 (extracting only length of spare1,spare2,spare3,spare4,spare5,spare6) ==============*/
SET TRIMSPOOL ON


SPOOL SYS.USER.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'USER$' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('ASTATUS','AUDIT$','CTIME','DATATS#','DEFGRP#','DEFGRP_SEQ#','DEFROLE','DEFSCHCLASS','EXPTIME','EXT_USERNAME','LCOUNT','LTIME','NAME','PTIME','RESOURCE$','SPARE1','SPARE2','SPARE3','SPARE5','SPARE6','TEMPTS#','TYPE#','USER#');

SELECT 
ASTATUS ||'&C_SEP' ||
replace(replace(AUDIT$,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
CTIME ||'&C_SEP' ||
DATATS# ||'&C_SEP' ||
DEFGRP# ||'&C_SEP' ||
DEFGRP_SEQ# ||'&C_SEP' ||
DEFROLE ||'&C_SEP' ||
replace(replace(DEFSCHCLASS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
EXPTIME ||'&C_SEP' ||
replace(replace(EXT_USERNAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
LCOUNT ||'&C_SEP' ||
LTIME ||'&C_SEP' ||
replace(replace(NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
PTIME ||'&C_SEP' ||
RESOURCE$ ||'&C_SEP' ||
length(SPARE1) ||'&C_SEP' ||
length(SPARE2) ||'&C_SEP' ||
length(SPARE3) ||'&C_SEP' ||
length(SPARE5) ||'&C_SEP' ||
SPARE6 ||'&C_SEP' ||
TEMPTS# ||'&C_SEP' ||
TYPE# ||'&C_SEP' ||
USER#,COUNT (*) OVER () AS row_cnt_col 
FROM  SYS.USER$
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*8 ==============END OF QUERY FROM SYS.USER$ TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.USER$'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM V$PARAMETER;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*9 ==============START OF QUERY FROM V$PARAMETER TABLE ==============*/

SET TRIMSPOOL ON
SPOOL VPARAMETER.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= UPPER('V_$PARAMETER')
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('DESCRIPTION','DISPLAY_VALUE','HASH','ISADJUSTED','ISBASIC','ISDEFAULT','ISDEPRECATED','ISINSTANCE_MODIFIABLE','ISMODIFIED','ISSES_MODIFIABLE','ISSYS_MODIFIABLE','NAME','NUM','TYPE','UPDATE_COMMENT','VALUE');

SELECT 
replace(replace(description,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(DISPLAY_VALUE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
HASH ||'&C_SEP' ||
replace(replace(ISADJUSTED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISBASIC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISDEFAULT,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISDEPRECATED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISINSTANCE_MODIFIABLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISMODIFIED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISSES_MODIFIABLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(ISSYS_MODIFIABLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
NUM ||'&C_SEP' ||
TYPE ||'&C_SEP' ||
replace(replace(UPDATE_COMMENT,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(VALUE,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM SYS.V_$PARAMETER WHERE UPPER(NAME) in ('OS_AUTHENT_PREFIX', 'REMOTE_OS_AUTHENT', 'OS_ROLES', 'REMOTE_OS_ROLES', 'SQL92_SECURITY', 'AUDIT_TRAIL', 'AUDIT_SYS_OPERATIONS', 'AUDIT_FILE_DEST', 'AUDIT_SYSLOG_LEVEL')
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*9 ==============END OF QUERY FROM V$PARAMETER TABLE ==============*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.V_$PARAMETER'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_STMT_AUDIT_OPTS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*10==============START OF QUERY FROM DBA_STMT_AUDIT_OPTS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_STMT_AUDIT_OPTS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_STMT_AUDIT_OPTS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('AUDIT_OPTION','FAILURE','PROXY_NAME','SUCCESS','USER_NAME');

SELECT 
replace(replace(AUDIT_OPTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(FAILURE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PROXY_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SUCCESS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(USER_NAME,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_STMT_AUDIT_OPTS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*10 ==============END OF QUERY FROM DBA_STMT_AUDIT_OPTS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_STMT_AUDIT_OPTS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_PRIV_AUDIT_OPTS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*11==============START OF QUERY FROM DBA_PRIV_AUDIT_OPTS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_PRIV_AUDIT_OPTS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_PRIV_AUDIT_OPTS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('FAILURE','PRIVILEGE','PROXY_NAME','SUCCESS','USER_NAME');

SELECT 
replace(replace(FAILURE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PRIVILEGE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PROXY_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SUCCESS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(USER_NAME,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_PRIV_AUDIT_OPTS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*11 ==============END OF QUERY FROM DBA_PRIV_AUDIT_OPTS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_PRIV_AUDIT_OPTS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_OBJ_AUDIT_OPTS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*12==============START OF QUERY FROM DBA_OBJ_AUDIT_OPTS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_OBJ_AUDIT_OPTS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_OBJ_AUDIT_OPTS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('ALT','AUD','COM','CRE','DEL','EXE','FBK','GRA','IND','INS','LOC','OBJECT_NAME','OBJECT_TYPE','OWNER','REA','REF','REN','SEL','UPD','WRI');

SELECT 
replace(replace(ALT,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(AUD,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(COM,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(CRE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(DEL,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(EXE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(FBK,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GRA,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(IND,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(INS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(LOC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_TYPE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(REA,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(REF,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(REN,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SEL,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(UPD,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(WRI,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_OBJ_AUDIT_OPTS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*12 ==============END OF QUERY FROM DBA_OBJ_AUDIT_OPTS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_OBJ_AUDIT_OPTS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM V$VERSION ;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*13==============START OF QUERY FROM V$VERSION TABLE ==============*/
SET TRIMSPOOL ON


SPOOL VVERSION.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'V_$VERSION' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('BANNER');

SELECT 
BANNER,COUNT (*) OVER () AS row_cnt_col
FROM  SYS.V_$VERSION
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*13 ==============END OF QUERY FROM V$VERSION TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.V_$VERSION'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_JOBS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*14==============START OF QUERY FROM DBA_JOBS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_JOBS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_JOBS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('BROKEN','FAILURES','INSTANCE','INTERVAL','JOB','LAST_DATE','LAST_SEC','LOG_USER','MISC_ENV','NEXT_DATE','NEXT_SEC','NLS_ENV','PRIV_USER','SCHEMA_USER','THIS_DATE','THIS_SEC','TOTAL_TIME','WHAT');

SELECT 
replace(replace(BROKEN,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
FAILURES ||'&C_SEP' ||
INSTANCE ||'&C_SEP' ||
replace(replace(INTERVAL,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
JOB ||'&C_SEP' ||
LAST_DATE ||'&C_SEP' ||
replace(replace(LAST_SEC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(LOG_USER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(MISC_ENV,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
NEXT_DATE ||'&C_SEP' ||
replace(replace(NEXT_SEC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(NLS_ENV,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(PRIV_USER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SCHEMA_USER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
THIS_DATE ||'&C_SEP' ||
replace(replace(THIS_SEC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
TOTAL_TIME ||'&C_SEP' ||
replace(replace(WHAT,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_JOBS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*14 ==============END OF QUERY FROM DBA_JOBS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_JOBS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_JOBS_RUNNING;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*15==============START OF QUERY FROM DBA_JOBS_RUNNING TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_JOBS_RUNNING.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_JOBS_RUNNING' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('FAILURES','INSTANCE','JOB','LAST_DATE','LAST_SEC','SID','THIS_DATE','THIS_SEC');

SELECT 
FAILURES ||'&C_SEP' ||
INSTANCE ||'&C_SEP' ||
JOB ||'&C_SEP' ||
LAST_DATE ||'&C_SEP' ||
replace(replace(LAST_SEC,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
SID ||'&C_SEP' ||
THIS_DATE ||'&C_SEP' ||
replace(replace(THIS_SEC,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_JOBS_RUNNING
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*15 ==============END OF QUERY FROM DBA_JOBS_RUNNING TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_JOBS_RUNNING'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM ALL_SCHEDULER_RUNNING_JOBS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*16==============START OF QUERY FROM ALL_SCHEDULER_RUNNING_JOBS TABLE ==============*/
SET TRIMSPOOL ON


SPOOL ALL_SCHEDULER_RUNNING_JOBS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'ALL_SCHEDULER_RUNNING_JOBS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('CPU_USED','DETACHED','ELAPSED_TIME','JOB_NAME','JOB_STYLE','JOB_SUBNAME','OWNER','RESOURCE_CONSUMER_GROUP','RUNNING_INSTANCE','SESSION_ID','SLAVE_OS_PROCESS_ID','SLAVE_PROCESS_ID');

SELECT 
CPU_USED ||'&C_SEP' ||
replace(replace(DETACHED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
ELAPSED_TIME ||'&C_SEP' ||
replace(replace(JOB_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(JOB_STYLE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(JOB_SUBNAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(RESOURCE_CONSUMER_GROUP,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
RUNNING_INSTANCE ||'&C_SEP' ||
SESSION_ID ||'&C_SEP' ||
replace(replace(SLAVE_OS_PROCESS_ID,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
SLAVE_PROCESS_ID,COUNT (*) OVER () AS row_cnt_col 
FROM  SYS.ALL_SCHEDULER_RUNNING_JOBS
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*16 ==============END OF QUERY FROM ALL_SCHEDULER_RUNNING_JOBS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.ALL_SCHEDULER_RUNNING_JOBS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM SCHUEDULER_JOB_LOG;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*17==============START OF QUERY FROM DBA_SCHEDULER_JOB_LOG TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_SCHEDULER_JOB_LOG.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_SCHEDULER_JOB_LOG' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('CLIENT_ID','DESTINATION','GLOBAL_UID','JOB_CLASS','JOB_NAME','JOB_SUBNAME','LOG_DATE','LOG_ID','OPERATION','OWNER','STATUS','USER_NAME');

SELECT 
replace(replace(CLIENT_ID,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(DESTINATION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GLOBAL_UID,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(JOB_CLASS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(JOB_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(JOB_SUBNAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
to_char(log_date,'yyyy-mm-dd hh24:mi:ss') ||'&C_SEP' ||
LOG_ID ||'&C_SEP' ||
replace(replace(OPERATION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(STATUS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(USER_NAME,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col  
FROM  SYS.DBA_SCHEDULER_JOB_LOG where LOG_DATE between TO_DATE('&AUDIT_START_DATE','DD-MON-YYYY') and TO_DATE('&AUDIT_END_DATE','DD-MON-YYYY') order by LOG_DATE
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*17 ==============END OF QUERY FROM DBA_SCHEDULER_JOB_LOG TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_SCHEDULER_JOB_LOG'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_USERS_WITH_DEFPWD;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*18 ==============START OF QUERY FROM DBA_USERS_WITH_DEFPWD TABLE ==============*/
SET TRIMSPOOL ON


SPOOL DBA_USERS_WITH_DEFPWD.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_USERS_WITH_DEFPWD' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('USERNAME');

SELECT 
USERNAME ,COUNT (*) OVER () AS row_cnt_col
FROM  SYS.DBA_USERS_WITH_DEFPWD
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*18 ==============END OF QUERY FROM DBA_USERS_WITH_DEFPWD TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_USERS_WITH_DEFPWD'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

/**************************************** Req ID: 1222 ***********************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_OBJECTS;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF
/*19 ==============START OF QUERY FROM DBA_OBJECTS TABLE ==============*/

SET TRIMSPOOL ON

SPOOL DBA_OBJECTS.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_OBJECTS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('CREATED','DATA_OBJECT_ID','EDITION_NAME','GENERATED','LAST_DDL_TIME','NAMESPACE','OBJECT_ID','OBJECT_NAME','OBJECT_TYPE','OWNER','SECONDARY','STATUS','SUBOBJECT_NAME','TEMPORARY','TIMESTAMP');


SELECT
CREATED ||'&C_SEP' ||
replace(replace(DATA_OBJECT_ID,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(EDITION_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(GENERATED,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
LAST_DDL_TIME ||'&C_SEP' ||
replace(replace(NAMESPACE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_ID,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_TYPE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SECONDARY,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(STATUS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(SUBOBJECT_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(TEMPORARY,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
TIMESTAMP,COUNT (*) OVER () AS row_cnt_col
FROM SYS.DBA_OBJECTS where LAST_DDL_TIME between TO_DATE('&AUDIT_START_DATE','DD-MON-YYYY') and TO_DATE('&AUDIT_END_DATE','DD-MON-YYYY') order by LAST_DDL_TIME
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*19 ==============END OF QUERY FROM DBA_OBJECTS TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_OBJECTS'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_OBJECTS_TEMPORARY;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*20 ==============START OF QUERY FROM DBA_OBJECTS_TEMPORARY TABLE ==============*/

SET TRIMSPOOL ON

SPOOL DBA_OBJECTS_TEMPORARY.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= 'DBA_OBJECTS' 
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('OBJECT_NAME','OBJECT_TYPE','OWNER');


SELECT
replace(replace(OBJECT_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OBJECT_TYPE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(OWNER,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col
FROM SYS.DBA_OBJECTS where TEMPORARY='Y'
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*20 ==============END OF QUERY FROM DBA_OBJECTS_TEMPORARY TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_OBJECTS_TEMPORARY'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF


/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_REGISTRY_HISTORY;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*21 ==============START OF QUERY FROM DBA_REGISTRY_HISTORY TABLE ==============*/

SET TRIMSPOOL ON

SPOOL 11G_DBA_REGISTRY_HISTORY.TXT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS
WHERE UPPER(TABLE_NAME)= 'DBA_REGISTRY_HISTORY'
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('ACTION_TIME','ACTION','NAMESPACE','VERSION','ID','COMMENTS');


SELECT
replace(replace(ACTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
to_char(ACTION_TIME,'yyyy-mm-dd hh24:mi:ss') ||'&C_SEP' ||
replace(replace(COMMENTS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
ID ||'&C_SEP' ||
replace(replace(NAMESPACE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(VERSION,CHR(13),''),CHR(10),' '),COUNT (*) OVER () AS row_cnt_col
FROM SYS.DBA_REGISTRY_HISTORY
/
SPOOL OFF

V_COUNT = V_COUNT+1;

/*21 ==============END OF QUERY FROM DBA_REGISTRY_HISTORY TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_REGISTRY_HISTORY'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM DBA_REGISTRY_SQLPATCH;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*22 ==============START OF QUERY FROM DBA_REGISTRY_SQLPATCH TABLE ==============*/

SET TRIMSPOOL ON

SPOOL 12C_DBA_REGISTRY_SQLPATCH.TXT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS
WHERE UPPER(TABLE_NAME)= 'DBA_REGISTRY_SQLPATCH'
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('PATCH_ID','PATCH_UID','VERSION','FLAGS','ACTION','STATUS','ACTION_TIME','DESCRIPTION','BUNDLE_ID','BUNDLE_SERIES','BUNDLE_DATA','LOGFILE');


SELECT
replace(replace(ACTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
to_char(ACTION_TIME,'yyyy-mm-dd hh24:mi:ss') ||'&C_SEP' ||
replace(replace(BUNDLE_DATA,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
BUNDLE_ID ||'&C_SEP' ||
replace(replace(BUNDLE_SERIES,CHR(13),''),CHR(10),' ')  ||'&C_SEP' ||
replace(replace(DESCRIPTION,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(FLAGS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(LOGFILE,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
PATCH_ID ||'&C_SEP' ||
PATCH_UID ||'&C_SEP' ||
replace(replace(STATUS,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(VERSION,CHR(13),''),CHR(10),' ') ,COUNT (*) OVER () AS row_cnt_col
FROM SYS.DBA_REGISTRY_SQLPATCH
/
SPOOL OFF

V_COUNT = V_COUNT+1;

/*22 ==============END OF QUERY FROM DBA_REGISTRY_SQLPATCH TABLE ================*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.DBA_REGISTRY_SQLPATCH'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/
Select '0'  AS row_cnt_col FROM DUAL;

SET TERM ON

SPOOL ACTT_EXTRACTION_LOG.TXT APP
PROMPT TRYING TO EXTRACT DATA FROM V$INSTANCE;
SPOOL OFF

SET TERMOUT OFF PAGES 0 HEADING OFF ECHO OFF FEEDBACK OFF

/*23 ==============START OF QUERY FROM V$INSTANCE TABLE ==============*/

SET TRIMSPOOL ON
SPOOL VINSTANCE.ACTT

SELECT RTRIM (XMLAGG (XMLELEMENT (E,COLUMN_NAME || ' ' || DATA_TYPE || '('|| CASE  WHEN DATA_type = 'NUMBER' THEN  CASE  WHEN DATA_PRECISION IS NULL THEN '&C_MAX_PRECISION,&C_MAX_SCALE'  ELSE DATA_PRECISION || ','|| DATA_SCALE  END ELSE  ''||DATA_LENGTH  END || ')'|| '&C_SEP') ORDER BY COLUMN_NAME).EXTRACT ('//text()'),'&C_SEP')
FROM  ALL_TAB_COLUMNS 
WHERE UPPER(TABLE_NAME)= UPPER('V_$INSTANCE')
AND UPPER(OWNER) ='SYS'
AND COLUMN_NAME IN ('DATABASE_STATUS','INSTANCE_ROLE','INSTANCE_NUMBER','INSTANCE_NAME','HOST_NAME','VERSION');

SELECT 
DATABASE_STATUS ||'&C_SEP' ||
replace(replace(HOST_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
replace(replace(INSTANCE_NAME,CHR(13),''),CHR(10),' ') ||'&C_SEP' ||
INSTANCE_NUMBER ||'&C_SEP' ||
INSTANCE_ROLE ||'&C_SEP' ||
VERSION,COUNT (*) OVER () AS row_cnt_col
FROM SYS.V_$INSTANCE 
/ 
SPOOL OFF

V_COUNT = V_COUNT+1;

/*23 ==============END OF QUERY FROM V$INSTANCE TABLE ==============*/

/************************* appending the record count of each table that is extracted based on the conditions used ************/

SPOOL ACTT_CONFIG_TABLERECORDCOUNT.ACTT APP

SELECT 'SYS.V_$INSTANCE'||'&C_SEP'||(Select &row_cnt     AS total_rows_found FROM DUAL) FROM DUAL;

SPOOL OFF

/******************************************* stop writing into the file after metadata ***************************************/

/*************************************************** Script Ending details captured **************************************************/

/******************************************** appending the control data into the file ****************************************/

Spool ACTT_CONFIG_SETTINGS.ACTT APP

SELECT 'AUDIT_START_DATE'||'&C_SEP'||TO_CHAR(TO_DATE('&AUDIT_START_DATE','DD-MON-YYYY'),'DD-MON-YYYY') FROM DUAL;
SELECT 'AUDIT_END_DATE'||'&C_SEP'||TO_CHAR(TO_DATE('&AUDIT_END_DATE','DD-MON-YYYY'),'DD-MON-YYYY') FROM DUAL;
SELECT 'Extract Script End Time'||'&C_SEP'||TO_CHAR(SYSDATE, 'DD-MON-YYYY HH:MI PM') FROM DUAL;
SELECT 'Data Extraction Date'||'&C_SEP'||TO_CHAR(SYSDATE, 'DD-MON-YYYY HH:MI PM') FROM DUAL;



SPOOL OFF
/*SELECT 'Number of Tables Extracted'||'&C_SEP'||LTRIM('&V_COUNT') FROM DUAL;*/

/******************************************* stop writing into the file after metadata ***************************************/


/************************************************************* END *******************************************************************/

EXIT

/************************************************************* END *******************************************************************/

