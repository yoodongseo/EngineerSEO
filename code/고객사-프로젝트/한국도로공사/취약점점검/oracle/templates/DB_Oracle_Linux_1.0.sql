-- "********************************************************************"
-- "*                      CAS(Oracle_LINUX) Checklist                 *"
-- "********************************************************************"
-- "*          Copyright 2021 CAS Co. Ltd. All right Reserved          *"
-- "********************************************************************"


WHENEVER SQLERROR EXIT SQL.SQLCODE

HOST sh ./oracle_main.sh

PROMPT
PROMPT
SET pagesize 1000
SET linesize 100
set feedback off
set term off

PROMPT
PROMPT
PROMPT  D-01. 기본 계정의 패스워드 정책 등을 변경하여 사용
PROMPT  =====================================================================
PROMPT
col username format a20
col profile format a20
col password format a20
col account_status format a20
SPOOL ./tmp/D-1.txt
select username, profile, password, account_status from dba_users where account_status='OPEN';
SPOOL OFF


PROMPT
PROMPT
PROMPT	D-02. 데이터베이스의 불필요 계정을 제거하거나 잠금설정 후 사용
PROMPT  =====================================================================
PROMPT
col username format a30
col account_status format a20
col lock_date format a15
col expiry_date format a15
col profile format a15
SPOOL ./tmp/D-2.txt
SELECT username,account_status,lock_date,expiry_date,profile from dba_users;
SPOOL OFF


PROMPT
PROMPT
PROMPT	D-03. 패스워드의 사용기간 및 복잡도를 기관 정책에 맞도록 설정
PROMPT  =====================================================================
PROMPT
col username format a20
col profile format a20
col password format a10
col account_status format a20
SPOOL ./tmp/D-3.txt
select username, profile, password, account_status from dba_users where account_status='OPEN';
SPOOL OFF

col profile format a30
col resource_name format a30
col limit format a30
SPOOL ./tmp/D-3-1.txt
select profile, resource_name, limit from dba_profiles where resource_name='PASSWORD_VERIFY_FUNCTION' OR resource_name='PASSWORD_LIFE_TIME' order by profile;
SPOOL OFF


PROMPT
PROMPT
PROMPT 	D-04. 데이터베이스 관리자 권한을 꼭 필요한 계정 및 그룹에 허용
PROMPT  =====================================================================
PROMPT
col username format a30
SPOOL ./tmp/D-4.txt
SELECT username FROM v$pwfile_users where username NOT IN (select grantee from dba_role_privs where granted_role='dba') and username !='INTERNAL' and sysdba='TRUE';
SPOOL OFF

col grantee format a30
col granted_role format a20
col admin_option format a20
SPOOL ./tmp/D-4-1.txt
SELECT grantee, granted_role, admin_option FROM dba_role_privs WHERE granted_role='DBA';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-05. 원격에서 DB 서버로의 접속 제한
PROMPT  =====================================================================
PROMPT 
col name format a30
col value format a20
SPOOL ./tmp/D-5.txt
select name, value from gv$parameter where name='remote_os_authent' order by name;
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-06. DBA 이외의 인가되지 않은 사용자가 시스템 테이블에 접근할 수 없도록 설정
PROMPT  =====================================================================
PROMPT
col grantee| format a10
col privilege format a30
col table_name format a30
SPOOL ./tmp/D-6.txt
select grantee, privilege, table_name from dba_tab_privs where (owner='SYS' or table_name like 'DBA_%') and privilege <> 'EXECUTE' and grantee not in('PUBLIC','AQ_ADMINISTRATOR_ROLE','AQ_USER_ROLE','AURORA$JIS$UTILITY$','OSE$HTTP$ADMIN','TRACESVR','CTXSYS','DBA','DELETE_CATALOG_ROLE','EXECUTE_CATALOG_ROLE','EXP_FULL_DATABASE','GATHER_SYSTEM_STATISTICS','HS_ADMIN_ROLE','IMP_FULL_DATABASE','LOGSTDBY_ADMINISTRATOR','MDSYS','ODM','OEM_MONITOR','OLAPSYS','ORDSYS','OUTLN','RECOVERY_CATALOG_OWNER','SELECT_CATALOG_ROLE','SNMPAGENT','SYSTEM','WKSYS','WKUSER','WMSYS','WM_ADMIN_ROLE','XDB','LBACSYS','PERFSTAT','XDBADMIN') and grantee not in(select grantee from dba_role_privs where granted_role='DBA') order by grantee;
SPOOL OFF



PROMPT
PROMPT
PROMPT	D-07. 리스너의 패스워드를 설정하여 사용
PROMPT  =====================================================================
PROMPT



PROMPT
PROMPT
PROMPT  D-08. 응용프로그램 또는 DBA 계정의 Role이 Public으로 설정되지 않도록 조정
PROMPT  =====================================================================
PROMPT
col granted_role||':'||grantee format a35
SPOOL ./tmp/D-8.txt
select granted_role, grantee from dba_role_privs where grantee='PUBLIC';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-09. OS_ROLES, REMOTE_OS_AUTHENTICATION, REMOTE_OS_ROLES를 FALSE로 설정
PROMPT  =====================================================================
PROMPT
col name format a20
col value format a10
SPOOL ./tmp/D-9.txt
select name, value from gv$parameter where name='os_roles' or name='remote_os_authent' or name='remote_os_roles';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-10. 데이터베이스에 대해 최신 보안패치와 벤더 권고사항을 모두 적용
PROMPT  =====================================================================
PROMPT
col banner format a80
SPOOL ./tmp/D-10.txt
select banner from v$version where banner like 'Oracle%';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-11. 데이터베이스의 접근, 변경, 삭제 등의 감사기록이 기관의 감사기록 정책에 적합하도록 설정
PROMPT  =====================================================================
PROMPT
col name format a30
col value format a10
SPOOL ./tmp/D-11.txt
SELECT name, value FROM gv$parameter WHERE name = 'audit_trail';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-12. 패스워드 재사용에 대한 제약의 설정
PROMPT  =====================================================================
PROMPT
col username format a20
col profile format a30
col account_status format a15
SPOOL ./tmp/D-12.txt
select username, profile, account_status from dba_users where account_status='OPEN';
SPOOL OFF

col profile format a20
col resource_name format a30
col limit format a15
SPOOL ./tmp/D-12-1.txt
select profile, resource_name, limit from dba_profiles where resource_name like '%PASSWORD_REUSE%' order by profile;
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-13. DB 사용자 계정을 개별적으로 부여하여 사용
PROMPT  =====================================================================
PROMPT
col username format a20
col profile format a30
col account_status format a15
SPOOL ./tmp/D-13.txt
select username, profile, account_status from dba_users where account_status='OPEN';
SPOOL OFF


PROMPT
PROMPT
PROMPT	D-14. 불필요한 ODBC/OLE-DB 데이터 소스와 드라이브를 제거 하여 사용
PROMPT  =====================================================================
PROMPT



PROMPT
PROMPT
PROMPT	D-15. 일정 횟수의 로그인 실패 시 이에 대한 잠금정책 적용
PROMPT  =====================================================================
PROMPT
col username format a20
col profile format a30
col account_status format a15
SPOOL ./tmp/D-15.txt
select username, profile, account_status from dba_users where account_status='OPEN';
SPOOL OFF

col profile format a20
col resource_name format a30
col limit format a15
SPOOL ./tmp/D-15-1.txt
select profile, resource_name, limit from dba_profiles where resource_name='FAILED_LOGIN_ATTEMPTS' OR resource_name='PASSWORD_LOCK_TIME' order by profile;
SPOOL OFF


PROMPT
PROMPT
PROMPT	D-16. DB 계정의 umask를 022 이상으로 설정
PROMPT  =====================================================================
PROMPT



PROMPT
PROMPT
PROMPT	D-17. 데이터베이스의 주요 설정파일, 패스워드 파일 등과 같은 주요파일들의 접근 권한이 적절하게 설정
PROMPT  =====================================================================
PROMPT
SPOOL ./tmp/D-17-1.txt
set heading off
col member format a150
select member from v$logfile;
SPOOL OFF

SPOOL ./tmp/D-17-2.txt
col name format a150
select name from v$datafile;
SPOOL OFF

SPOOL ./tmp/D-17-3.txt
col name format a150
select name from v$controlfile;
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-18. 관리자 이외의 사용자가 오라클 리스너의 접속을 통해 리스너 로그 및 trace 파일에 대한 변경 제한
PROMPT  =====================================================================
PROMPT


PROMPT
PROMPT
PROMPT  D-19. 패스워드 확인함수가 설정되어 적용
PROMPT  =====================================================================
PROMPT
set heading on
col profile format a20
col resource_name format a30
col limit format a30
SPOOL ./tmp/D-19.txt
select profile, resource_name, limit from dba_profiles where resource_name like '%FUNCTION%' order by profile;
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-20. 인가되지 않은 Object Owner의 제한
PROMPT  =====================================================================
PROMPT
col owner format a30
col OBJECT_NAME format a30
col OBJECT_TYPE format a20
col STATUS format a15
SPOOL ./tmp/D-20.txt
Select distinct owner, OBJECT_NAME, OBJECT_TYPE, STATUS from dba_objects where owner not in ('SYS','SYSTEM','MDSYS','CTXSYS','ORDSYS','ORDPLUGINS','AURORA$JIS$UTILITY$','HR','ODM','ODM_MTR','OE','OLAPDBA','OLAPSYS','OSE$HTTP$ADMIN','OUTLN','LBACSYS','MTSYS','PM','PUBLIC','QS','QS_ADM','QS_CB','QS_CBADM','DBSNMP','QS_CS','QS_ES','QS_OS','QS_WS','RMAN','SH','WKSYS','WMSYS','XDB')and owner not in (select grantee from dba_role_privs where granted_role='DBA');
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-21. 인가되지 않은 GRANT OPTION 사용 제한
PROMPT  =====================================================================
PROMPT
col grantee format a15
col owner format a30
col table_name format a30
col grantable format a10
SPOOL ./tmp/D-21.txt
Select grantee, owner, table_name, grantable from dba_tab_privs where grantable='YES' and owner not in ('SYS','MDSYS','ORDPLUGINS','ORDSYS','SYSTEM','WMSYS','SDB','LBACSYS') and grantee not in (select grantee from dba_role_privs where granted_role='DBA') order by grantee;
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-22. 데이터베이스의 자원 제한 기능을 TRUE로 설정
PROMPT  =====================================================================
PROMPT
col name format a20
col value format a15
SPOOL ./tmp/D-22.txt
select name, value from v$parameter where name='resource_limit';
SPOOL OFF


PROMPT
PROMPT
PROMPT  D-23. 보안에 취약하지 않은 버전의 데이터베이스를 사용
PROMPT  =====================================================================
PROMPT
col banner format a80
SPOOL ./tmp/D-23.txt
select banner from v$version where banner like 'Oracle%';
SPOOL OFF

PROMPT
PROMPT
PROMPT  D-24. Audit Table은 데이터베이스 관리자 계정으로만 접근하도록 제한
PROMPT  =====================================================================
PROMPT
col table_name format a15
col owner format a15
SPOOL ./tmp/D-24.txt
select table_name, owner from dba_tables where table_name='AUD$';
SPOOL OFF


set term on
PROMPT
PROMPT
PROMPT ....Outputting results. Please wait a moment....

HOST sh ./make_result_ver1.0.sh

PROMPT
PROMPT

EXIT
