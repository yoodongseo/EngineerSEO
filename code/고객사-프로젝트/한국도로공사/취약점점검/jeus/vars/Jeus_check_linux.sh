#!/bin/bash


export LANG=ko_KR.utf8

ver=`su - wasadmin -c 'jeusadmin -version | egrep -i -o "JEUS 8.5|JEUS 8 Fix#1|JEUS 8.0|JEUS 7.0" |uniq;exit'`
nver=`su - wasadmin -c 'jeusadmin -version | egrep -i -o "JEUS 8.5|JEUS 8 Fix#1|JEUS 8.0|JEUS 7.0" |uniq;exit' |wc -l`
ver8="JEUS 8"
ver8_0="JEUS 8.0"
ver8_5="JEUS 8.5"


RED1="조치필요"
GREEN1="양호"
YELLOW1="확인필요"

RESET='\033[m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
GREEN='\033[32m'
BLUE='\033[1;34m'


i=`ps -ef | grep -i jeus | grep -v grep | grep -v root | head -1 | awk '{print $1}'| sed 's/[^a-zA-Z0-9]//g'`

jeusid=`grep $i /etc/passwd | cut -d : -f 1`

i2=`grep $jeusid /etc/passwd | cut -d : -f 6`

hostname=`hostname`

jhome=`grep -i "JEUS_HOME=" $i2/.bash_profile | cut -d = -f 2 | sed 's/"//g' | uniq`

jcfg=$jhome/config/$hostname/JEUSMain.xml

jcfgdir=$jhome/config/$hostname

syspwd=`grep example_user /etc/passwd |cut -d : -f 6`

washome=`grep $jeusid /etc/passwd |cut -d : -f 6`

gid=`grep $jeusid /etc/passwd | cut -d : -f 4`

gid1=`grep $jeusid /etc/group | cut -d : -f 1`

umask=`umask`


if [ $nver -eq 1 ]; then

   jver="1"
   break

else

   jver="2"
   break

fi

case $jver in

1) # JEUS 7.x ~ 8.x version


dname=`grep -i "DOMAIN_NAME=" $i2/.bash_profile | cut -d = -f 2 | uniq`

jhome8=`grep -i "JEUS_HOME=" $i2/.bash_profile | cut -d = -f 2 | sed 's/"//g' | uniq`

jcfg8=$jhome8/domains/$dname/config/domain.xml

cfgres8=`grep -i "<enable-webadmin>" $jcfg8 | sed 's/ *//g'`

cfgres8_1=`grep -i "<enable-webadmin>" $jcfg8 | sed 's/ *//g' > $syspwd/cfg8.txt`

cfgres8_2=`sed -i 's/<enable-webadmin>//' $syspwd/cfg8.txt`

cfgres8_3=`sed -i 's/<\/enable-webadmin>//' $syspwd/cfg8.txt`

cfgres8_4=`cat $syspwd/cfg8.txt`

baseport=`grep -i 9736 $jcfg8`

baseport1=`grep -i 9736 $jcfg8 | wc -l`

baseport2=`grep -i "<listen-port>" $jcfg8 | head -1 | sed 's/ *//g' > $syspwd/baseport.txt`

baseport3=`sed -i 's/<listen-port>//' $syspwd/baseport.txt`

baseport4=`sed -i 's/<\/listen-port>//' $syspwd/baseport.txt`

baseport5=`cat $syspwd/baseport.txt`


echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}============================== JEUS 7.x ~ 8.x VERSION START ==============================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-01 ----------------------------"
echo "확인사항: JEUS7, JEUS8 버전은 관리자 페이지 사용을 권고하고 있음"
echo "          JEUS 기본포트 9736 사용 X (ex:10000)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


if [ $cfgres8_4 = true ]; then
   echo "■ domain.xml file enable-webadmin 설정: $cfgres8_4"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo "■ domain.xml file enable-webadmin 설정: $cfgres8_4"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
fi

rm -rf $syspwd/cfg8.txt  

echo " "

if [ $baseport1 -eq 0 ]; then 
   echo "■ BASE PORT = $baseport5"  
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo "■ BASE PORT = $baseport5"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
fi

rm -rf $syspwd/baseport.txt



echo " "
echo " "
echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-02 ----------------------------"
echo "확인사항: accounts.xml 웹관리자 콘솔 계정administrator, wasadmin 등"
echo "          사용 금지 (유추하기 어려운 계정명으로 변경할 것)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


web8id=$jhome8/domains/$dname/config/security/SYSTEM_DOMAIN/accounts.xml

web8id1=`grep -A3 -i -w "<user>" $web8id | grep -v "<user>" | head -1 | sed 's/ *//g' > $syspwd/web8id.txt`

web8id2=`sed -i 's/<name>//' $syspwd/web8id.txt`

web8id3=`sed -i 's/<\/name>//' $syspwd/web8id.txt`

web8id4=`cat $syspwd/web8id.txt`


if [ "$web8id4" = "administrator" ] || [ "$web8id4" = "Administrator" ] || [ "$web8id4" = "wasadmin" ]; then
   echo "■ 설정: $web8id4"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
else
   echo "■ 설정: $web8id4"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
fi

rm -rf $syspwd/web8id.txt


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-03 ----------------------------"
echo "확인사항: accounts.xml 파일 패스워드는 유추하기 쉬운 패스워드 사용X"
echo "          AES방식으로 암호화 (base64 사용 X)"
echo "-------------------------------------------------------------------"
echo " "
echo " "

web8pass=`grep -i "<password>" $web8id | grep -o '{[^>]*}' | sed 's/{//' | sed 's/}//'`


if [ "$web8pass" = "base64" ] || [ "$web8pass" = "BASE64" ]; then
   echo "■ 설정: $web8pass"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
else
   echo "■ 설정: $web8pass"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
fi


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-04 ----------------------------"
echo "확인사항: accounts.xml 파일 퍼미션 600 혹은 700 이하로 변경"
echo "-------------------------------------------------------------------"
echo " "
echo " "
ac8perm=`find $web8id -type f -exec ls -lrt {} \; |grep -w accounts.xml | grep -v "accounts.xml.[0-9]" | grep -v "accounts.xml.[A-Za-z]"`

echo "■ 현황: $ac8perm"

ac8perm1=`find $web8id -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
ac8perm2=`find $web8id -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`


if [ $ac8perm2 -eq 0 ]; then
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo -e "■ 결과 : ${RED}$RED1${RESET}"
fi


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-01 ----------------------------"
echo "확인사항: JEUS 데몬 계정이 root 권한으로 미운영 필요"
echo "-------------------------------------------------------------------"
echo " "
echo " "


if [ $i = $jeusid ]; then
   echo "■ 현황: $i"
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo " "
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
fi



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-02 ----------------------------"
echo "확인사항: JEUS 홈디렉터리 750 이하로 변경할 것 (UMASK 027로 할것)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


echo "[UMASK]"
echo " "

jumask=`su - $jeusid -c '
umask
exit'`

echo "■ 설정: $jumask"
if [ $jumask -eq 027 ] ; then
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo -e "■ 결과: ${RED}$RED1${RESET}"
fi

echo " "
echo " "


jhome8dir1=`find $jhome8/* -prune -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jhome8dir1num=`find $jhome8/* -prune -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' |wc -l`


if [ $jhome8dir1num -ne 0 ]; then
   echo "[JEUS HOME]"
   echo ""
   echo "■ $jhome8dir1"
   echo -e "■ 결과 : ${RED}$RED1${RESET}"
else
   echo "[JEUS HOME]"
   echo " "
   echo "■ 현황 : JEUS HOME has no directory"
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
fi


echo " "

jhome8file1=`find $jhome8/* -prune -type f -not -perm 640 -exec ls -lrt {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jhome8file1num=`find $jhome8/* -prune -type f -not -perm 640 -exec ls -lrt {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' |wc -l`

if [ $jhome8file1num -ne 0 ]; then
   echo "[JEUS HOME FILE]"
   echo ""
   echo "■ $jhome8file1"
   echo -e "■ 결과 : ${RED}$RED1${RESET}"
else
   echo "[JEUS HOME FILE]"
   echo " "
   echo "■ 현황 : JEUS HOME has no file"
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-03 ----------------------------"
echo "확인사항: 소스파일 퍼미션 640 이하, JEUS 설정파일 퍼미션 600 이하"
echo "          혹은 700 이하로 변경할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "



echo "■ 결과: 미조치(업무단 조치 필요 소스디렉터리 750, 소스파일 640,"
echo "               Other쪽 권한이 꼭 필요한 경우만 소스파일 644)"

#spath=`egrep -i "<path>|</path>" $jcfg8 | sed 's/ *//g' > $syspwd/sourcedi.txt`

#spath1=`sed -i 's/<path>//' $syspwd/sourcedi.txt`

#spath2=`sed -i 's/<\/path>//' $syspwd/sourcedi.txt`


#echo "[Directory]"
#echo " "
#for source in `cat $syspwd/sourcedi.txt | cut -d / -f 2 | uniq`

#do

#sourcedir=`find /$source -mindepth 1 -not -path "$i2/*" -not -path "$syspwd/*" -type d -not -perm 750 -not -perm 700 -not -user "root" -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
#sourcedirnum=`find /$source -mindepth 1 -not -path "$i2/*" -not -path "$syspwd/*" -type d -not -perm 750 -not -perm 700 -not -user "root" -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

#if [ $sourcedirnum -ne 0 ]; then
#   echo "$sourcedir"
#   echo -e "■ 결과 : ${RED}$RED1${RESET}"
#else
#   echo "■ 현황 : SOURCE HOME has no directory"
#   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
#fi

#done


#echo " "

#echo "[FILE]"
#echo " "
#for source in `cat $syspwd/sourcedi.txt | cut -d / -f 2 | uniq`

#do

#sourcefile=`find /$source -mindepth 1 -not -path "$i2/*" -not -path "$syspwd/*" -type f -not -perm 640 -not -perm 600 -not -user "root" -exec ls -lrt {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
#sourcefilenum=`find /$source -mindepth 1 -not -path "$i2/*" -not -path "$syspwd/*" -type f -not -perm 640 -not -perm 600 -not -user "root" -exec ls -lrt {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

#if [ $sourcefilenum -ne 0 ]; then
#  echo "$sourcefile"
#   echo -e "■ 결과 : ${RED}$RED1${RESET}"
#else
#   echo "■ 현황 : SOURCE HOME has no file"
#   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
#fi

#done

#rm -rf $syspwd/sourcedi.txt

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-04 ----------------------------"
echo "확인사항: 모든 로그 디렉터리 750 이하, 로그파일 640 이하로 변경"
echo "-------------------------------------------------------------------"

su - $jeusid -c '
alias jlog | cut -d = -f 2 | xargs > jlog.sh
sed -e "s/\$/;pwd;/" jlog.sh > jlog1.sh
sh jlog1.sh > jlog.txt
exit'

chmod 700 $washome/jlog.txt

jlog8file=`find $washome -name jlog.txt`
jlog8filenum=`find $washome -name jlog.txt | wc -l`


if [ $jlog8filenum -eq 1 ]; then
   echo `mv $jlog8file $syspwd`
else
   echo "**로그경로 확인필요**"
fi

jsh8_1=`find $washome -name jlog.sh | wc -l`
jsh8_2=`find $washome -name jlog1.sh | wc -l`


if [ $jsh8_1 -eq 1 ];then
   echo `rm -rf $washome/jlog.sh`
else
   echo "**로그경로 확인필요**"
fi

if [ $jsh8_2 -eq 1 ];then
   echo `rm -rf $washome/jlog1.sh`
else
   echo "**로그경로 확인필요**"
fi


jlog8=`cat $syspwd/jlog.txt`
jlog8dir=`find $jlog8 -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jlog8dir1=`find $jlog8 -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' | wc -l`


echo "[DIRECTORY]"
echo " "

if [ $jlog8dir1 -gt 0 ]; then
   echo "$jlog8dir"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
   echo " "
else 
   echo "■ 현황: JLOG has no directory"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"  
   echo " "
fi

echo " "


jlog8file=`find $jlog8 -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jlog8file1=`find $jlog8 -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \;| awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`


echo "[FILE]"
echo " "

if [ $jlog8file1 -gt 0 ]; then
   echo "$jlog8file"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
   echo " "
else
   echo "■ 현황: JLOG has no file"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
   echo " "
fi


#echo " "
#echo "[RESOLUTION]"
#echo " "
#echo "- Directory -"

#for jlog8dir1_1 in `find $jlog8 -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' | wc -l`

#do

#jlog8dir_sol=`find $jlog8 -type d -not -perm 750 -not -perm 700 -print | awk '{print "* chmod 750 " $1}'`

#if [ $jlog8dir1_1 -eq 0 ]; then
#   echo "* No action"
#else
#   echo "$jlog8dir_sol"
#fi

#done



#echo " "
#echo "- File -"

#for jlog8file1_1 in `find $jlog8 -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \;| awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

#do

#jlog8file_sol=`find $jlog8 -type f -not -perm 640 -not -perm 600 -print | awk '{print "* chmod 640 " $1}'`

#if [ $jlog8file1_1 -eq 0 ]; then
#   echo "* No action"
#else
#   echo "$jlog8file_sol"
#fi

#done






rm -rf $syspwd/jlog.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-05 ----------------------------"
echo "확인사항: 사용자 브라우저로 에러 메시지 반환 관련 항목을 false 설정"
echo "          <attach-stacktrace-on-error>false</attach-stacktrace-on-error>"
echo "          (고의적으로 다양한 에러를 유발하여 돌아오는 에러 메시지를"
echo "          통해 웹 프로그램의 구조 및 환경 설정을 추정할 수 없게해야함)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


attach=`grep -i "attach-stacktrace" $jcfg8 | uniq | head -1 | sed 's/ *//g' > $syspwd/attach.txt`

attach1=`sed -i 's/<attach-stacktrace-on-error>//' $syspwd/attach.txt`

attach2=`sed -i 's/<\/attach-stacktrace-on-error>//' $syspwd/attach.txt`

attach3=`cat $syspwd/attach.txt | wc -l`

attach4=`cat $syspwd/attach.txt`


if [ $attach3 -eq 0 ] || [ $attach4 = "false" ];then
   echo "■ 설정: false"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"

elif [ $attach3 -ne 0 ]; then
   echo "■ 설정: $attach4"
   echo -e "■ 결과: ${RED}$RED1${RESET}"

else
   echo -e "■ 결과: 수동확인 필요"
fi


rm -rf $syspwd/attach.txt




echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-06 ----------------------------"
echo "확인사항: JEUS DB Connection Pool 설정의 DB계정 패스워드를"
echo "          AES 방식으로 암호화할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "


enc8=`grep -i "<password>" $jcfg8 | sed 's/ *//g' > $syspwd/enc8.txt`
enc8num=`cat $syspwd/enc8.txt | wc -l`
enc8_1=`grep -i "{aes}" $syspwd/enc8.txt | sed 's/ *//g' > $syspwd/enc8_1.txt`
enc8_1num=`cat $syspwd/enc8_1.txt | wc -l`
enc8_2=`grep -i "<password>" $jcfg8 | grep -i -v "{aes}" | sed 's/^/-/g' > $syspwd/enc8_2.txt`
enc8_2num=`cat $syspwd/enc8_2.txt | wc -l`


echo "■ 현황:"

if [ $enc8num -eq 0 ]; then
   echo -e "${YELLOW}- 암호화 미설정${RESET}"
else
   for pwd_li in `grep -i "<password>" $jcfg8`
   do
   echo "- $pwd_li"
   done
fi

echo " "
echo "■ 결과:"

if [ $enc8_1num -ne 0 ]; then

   for pwd_lii in `grep -i "<password>" $jcfg8`
   do
    echo -e "- $pwd_lii (${GREEN}$GREEN1${RESET})"
   done

elif [ $enc8_2num -ne 0 ]; then

   for pwd_liii in `cat $syspwd/enc8_2.txt`
   do
    echo -e "- $pwd_liii (${RED}$RED1{RESET})"
   done

else

   echo -e "${YELLOW}- 암호화 미설정${RESET}"

fi

rm -rf $syspwd/enc8.txt
rm -rf $syspwd/enc8_1.txt
rm -rf $syspwd/enc8_2.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-07 ----------------------------"
echo "확인사항: HTTP 요청에 대한 응답 시에 헤더에 서버의 이름, 버전 등의"
echo "          정보를 제공하는 경우, 공격자가 해당 정보를 이용해 공격에"
echo "          이용할 수 있다. "
echo " "
echo "          <Djeus.servlet.response.header.serverInfo=false>"
echo "          위 설정은 기본 설정(false)이므로 필요하면 JEUSMain.xml 에"
echo "          추가 해주면됨 "
echo "-------------------------------------------------------------------"
echo " "
echo " "

respon8=`grep -i "djeus.servlet.response" $jcfg8 | uniq | sed 's/ *//g' > $syspwd/respon8.txt`

respon8_1=`sed -i 's/<jvm-option>//' $syspwd/respon8.txt` 

respon8_2=`sed -i 's/<\/jvm-option>//' $syspwd/respon8.txt` 

respon8_3=`cat $syspwd/respon8.txt`

respon8_4=`cat $syspwd/respon8.txt | cut -d = -f 2`

gap=""

if [ "$respon8_4" = "false" ] || [ "$respon8_4" = "FALSE" ]; then
   echo "■ 현황: $respon8_3" 
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"

elif [ "$respon8_4" = "$gap" ]; then
   echo "■ 현황: Djeus.servlet.response.header.serverInfo=false"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"  
else
   echo "■ 현황: $respon8_3"
   echo -e "■ 결과: ${RED}$RED1${RESET}" 
fi

rm -rf $syspwd/respon8.txt


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-08 ----------------------------"
echo "확인사항: JEUS 컨피그 설정 10분으로 하고, 타임아웃시간이 더 필요한"
echo "          경우 소스쪽 설정으로 늘릴 것"
echo "          timeout 설정file : webcommon.xml"
echo "-------------------------------------------------------------------"
echo " "
echo " "

echo "■ 현황"

for tmt8 in `find $jhome8/domains/$dname/config/ -type f -name "domain.xml"`

do

tmttxt8=`cat $tmt8 | grep -i "<timeout>" | sed '/-[1]/d' | sed 's/ *//g' > $syspwd/tmt8.txt`

tmtf=`find $jhome8/domains/$dname/config -name "domain.xml"`


echo " "
echo "- FILE "
echo "* $tmt8"
echo " "
echo "- CONFIG "

    for cfgtmt8 in `cat $tmt8 | grep -i "<timeout>" | sed '/-[1]/d' | sed 's/ *//g'`
    do

      echo "* $cfgtmt8"

    done

done

echo " "
echo " "


echo "■ 결과"
echo " "
for stout8 in "<timeout>10</timeout>"

do

    for stouttmt8 in `cat $syspwd/tmt8.txt`

    do

      if [ $stouttmt8 = $stout8 ]; then
         echo -e "* ${GREEN}$GREEN1${RESET}($stouttmt8)"
      else
         echo -e "* ${RED}$RED1${RESET}($stouttmt8)"
      fi

    done

done


rm -rf $syspwd/tmt8.txt


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-03-01 ----------------------------"
echo "확인사항: 운영상 불필요한 샘플 디렉터리 삭제할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "


echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"




echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-04-01 ----------------------------"
echo "확인사항: 마이너업그레이드 포함하여 최신 패치 진행"
echo "-------------------------------------------------------------------"
echo " "
echo " "

jver8=`su - $jeusid -c '
jeusadmin -version | egrep -i -o "JEUS 8.5|JEUS 8 Fix#1|JEUS 8.0|JEUS 7.0" | uniq
exit'`


jever8="JEUS 8 Fix#1"
jever8i="JEUS 8.0 (Fix#1)"
jever8_5="JEUS 8.5"

jever7_5="JEUS 7.0 Fix#5"
jever7_5i="JEUS 7 Fix#5"
jever7_5ii="JEUS 7 (Fix#5)"


echo "■ 현황: $jver8"

if [ "$jver8" = "$jever8" ] || [ "$jver8" = "$jever8i" ] || [ "$jver8" = "$jever8_5" ] || [ "$jver8" = "$jever7_5" ] || [ "$jver8" = "$jever7_5i" ] || [ "$jver8" = "$jever7_5ii" ]; then
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}($jver8)"
else
   echo -e "■ 결과: ${RED}$RED1${RESET}($jver8)"
fi












echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}=========================================== END ==========================================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"






#============================================================================================================
#========================================== JEUS 8 version END ==============================================
#============================================================================================================


;;


2)  # JEUS 6.x version


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}================================= JEUS 6.x VERSION START =================================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-01 ----------------------------" 
echo "확인사항: JEUS7, JEUS8 버전은 관리자 페이지 사용을 권고하고 있음"
echo "          JEUS 기본포트 9736 사용 X (ex:10000)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


cfgres=`grep -i "<enable-webadmin>" $jcfg | sed 's/ *//g'`

cfg1=`grep -i "<enable-webadmin>" $jcfg | sed 's/ *//g' > $syspwd/cfg.txt`

cfg2=`sed -i 's/<enable-webadmin>//' $syspwd/cfg.txt`

cfg3=`sed -i 's/<\/enable-webadmin>//' $syspwd/cfg.txt`

cfg4=`cat $syspwd/cfg.txt`

bincfg=`grep -i "JEUS_BASEPORT=" $jhome/bin/jeus.properties`

bincfg1=`grep -i "JEUS_BASEPORT=" $jhome/bin/jeus.properties | cut -d = -f 2`

echo "[JEUSMain.xml]" 
echo " "
if [ $cfg4 = true ]; then
   echo "■ 설정: $cfgres"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo "■ 설정: $cfgres"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
fi

echo " "
echo " "
echo "[JEUS.properties]"

if [ $bincfg1 -eq 9736 ]; then
   echo " "
   echo "■ 설정: $bincfg"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
   echo " "
else
   echo " "
   echo "■ 설정: $bincfg"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
   echo " "
fi

rm -rf $syspwd/cfg.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-02 ----------------------------"
echo "확인사항: accounts.xml 웹관리자 콘솔 계정administrator, wasadmin 등"
echo "          사용 금지 (유추하기 어려운 계정명으로 변경할 것)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


webid=$jhome/config/$hostname/security/SYSTEM_DOMAIN/accounts.xml

webid1=`grep -A3 -i -w "<user>" $webid | grep -v "<user>" | head -1 | sed 's/ *//g' > $syspwd/webid.txt`

webid2=`sed -i 's/<name>//' $syspwd/webid.txt`

webid3=`sed -i 's/<\/name>//' $syspwd/webid.txt`

webid4=`cat $syspwd/webid.txt`


if [ "$webid4" = "administrator" ] || [ "$webid4" = "Administrator" ] || [ "$webid4" = "wasadmin" ]; then
   echo "■ 설정: $webid4"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
else
   echo "■ 설정: $webid4"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
fi

rm -rf $syspwd/webid.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-03 ----------------------------"
echo "확인사항: accounts.xml 파일 패스워드는 유추하기 쉬운 패스워드 사용X" 
echo "          AES방식으로 암호화 (base64 사용 X)"
echo "-------------------------------------------------------------------"
echo " "
echo " "

webpass=`grep -i "<password>" $webid | grep -o '{[^>]*}' | sed 's/{//' | sed 's/}//'`


if [ "$webpass" = "base64" ] || [ "$webpass" = "BASE64" ]; then
   echo "■ 설정: $webpass"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
else
   echo "■ 설정: $webpass"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
fi


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-01-04 ----------------------------"
echo "확인사항: accounts.xml 파일 퍼미션 600 혹은 700 이하로 변경"
echo "-------------------------------------------------------------------"
echo " "
echo " "

acperm=`find $webid -type f -exec ls -lrt {} \; |grep -w accounts.xml | grep -v "accounts.xml.[0-9]" | grep -v "accounts.xml.[A-Za-z]"`

echo "■ 현황: $acperm"

acperm1=`find $webid -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
acperm2=`find $webid -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

echo " "

if [ $acperm2 -eq 0 ]; then
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo -e "■ 결과 : ${RED}$RED1${RESET}"
fi


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-01 ----------------------------"
echo "확인사항: JEUS 데몬 계정이 root 권한으로 미운영 필요"
echo "-------------------------------------------------------------------"
echo " "
echo " "


if [ $i = $jeusid ]; then
   echo "■ 현황: $i"
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo " "
   echo -e "■ 결과 : ${GREEN}$GREEN1${RESET}"
fi



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-02 ----------------------------"
echo "확인사항: JEUS 홈디렉터리 750 이하로 변경할 것 (UMASK 027로 할것)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


echo "[UMASK]"
echo " "

jumask6=`su - $jeusid -c '
umask
exit'`


echo "■ 설정: $jumask6"
if [ $jumask6 -eq 027 ] ; then
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo -e "■ 결과: ${RED}$RED1${RESET}"
fi

echo " "
echo " "


jhomedir1=`find $jhome/* -prune -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jhomedir1num=`find $jhome/* -prune -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' |wc -l`


if [ $jhomedir1num -ne 0 ]; then
   echo "[JEUS HOME]"
   echo "" 
   echo "* $jhomedir1"
   echo -e "■ 결과 : ${RED}$RED1${RESET}"
else 
   echo "[JEUS HOME]"
   echo " "
   echo "■ 현황: JEUS HOME has no directory"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
fi


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-03 ----------------------------"
echo "확인사항: 소스파일 퍼미션 640 이하, JEUS 설정파일 퍼미션 600 이하" 
echo "          혹은 700 이하로 변경할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "

echo "■ 결과: 미조치(업무단 조치 필요 소스디렉터리 750, 소스파일 640,"
echo "               Other쪽 권한이 꼭 필요한 경우만 소스파일 644)"


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-04 ----------------------------"
echo "확인사항: 모든 로그 디렉터리 750 이하, 로그파일 640 이하로 변경"
echo "-------------------------------------------------------------------"


su - $jeusid -c '
alias jlog | cut -d = -f 2 | xargs > jlog.sh
sed -e "s/\$/;pwd;/" jlog.sh > jlog1.sh
sh jlog1.sh > jlog.txt
exit'


jlogfile=`find $washome -name jlog.txt`
jlogfilenum=`find $washome -name jlog.txt | wc -l`


if [ $jlogfilenum -eq 1 ]; then
   echo `mv $jlogfile $syspwd`
else
   echo "**로그경로 확인필요**"
fi


jsh1=`find $washome -name jlog.sh | wc -l`
jsh2=`find $washome -name jlog1.sh | wc -l`


if [ $jsh1 -eq 1 ];then
   echo `rm -rf $washome/jlog.sh`
else
   echo "**로그경로 확인필요**"
fi

if [ $jsh2 -eq 1 ];then
   echo `rm -rf $washome/jlog1.sh`
else
   echo "**로그경로 확인필요**"
fi


jlog=`cat $syspwd/jlog.txt`
jlogdir=`find $jlog -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jlogdir1=`find $jlog -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' | wc -l`


echo "[DIRECTORY]"
echo " "

if [ $jlogdir1 -gt 0 ]; then
   echo "$jlogdir"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
   echo " "
else 
   echo "■ 현황: JLOG has no directory"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"  
   echo " "
fi

echo " "

jlogfile=`find $jlog -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
jlogfile1=`find $jlog -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \;| awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`


echo "[FILE]"
echo " "

if [ $jlogfile1 -gt 0 ]; then
   echo "$jlogfile"
   echo -e "■ 결과: ${RED}$RED1${RESET}"
   echo " "
else
   echo "■ 현황: JLOG has no file"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
   echo " "
fi

echo " "
echo "[RESOLUTION]"
echo " "
echo "- Directory -"

for jlogdir1_1 in `find $jlog -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' | wc -l`

do

jlogdir_sol=`find $jlog -type d -not -perm 750 -not -perm 700 -print | awk '{print "* chmod 750 " $1}'`

if [ $jlogdir1_1 -eq 0 ]; then
   echo "* No action"
else
   echo "$jlogdir_sol"
fi

done



echo " "
echo "- File -"

for jlogfile1_1 in `find $jlog -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \;| awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

do

jlogfile_sol=`find $jlog -type f -not -perm 640 -not -perm 600 -print | awk '{print "* chmod 640 " $1}'`

if [ $jlogfile1_1 -eq 0 ]; then
   echo "* No action"
else
   echo "$jlogfile_sol"
fi

done








rm -rf $syspwd/jlog.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-05 ----------------------------"
echo "확인사항: 사용자 브라우저로 에러 메시지 반환 관련 항목을 false 설정"
echo "          <attach-stacktrace-on-error>false</attach-stacktrace-on-error>"
echo "          (고의적으로 다양한 에러를 유발하여 돌아오는 에러 메시지를" 
echo "          통해 웹 프로그램의 구조 및 환경 설정을 추정할 수 없게해야함)"
echo "-------------------------------------------------------------------"
echo " "
echo " "


attach=`grep -i "attach-stacktrace" $jcfg | uniq | head -1 | sed 's/ *//g' > $syspwd/attach.txt`

attach1=`sed -i 's/<attach-stacktrace-on-error>//' $syspwd/attach.txt`

attach2=`sed -i 's/<\/attach-stacktrace-on-error>//' $syspwd/attach.txt`

attach3=`cat $syspwd/attach.txt | wc -l`

attach4=`cat $syspwd/attach.txt`



if [ $attach3 -eq 0 ] || [ $attach4 = "false" ];then
   echo "■ 설정: false"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"

elif [ $attach3 -ne 0 ]; then
   echo "■ 설정: $attach4"
   echo -e "■ 결과: ${RED}$RED1${RESET}"

else
   echo -e "■ 결과: 수동확인 필요"
fi


rm -rf $syspwd/attach.txt




echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-06 ----------------------------"
echo "확인사항: JEUS DB Connection Pool 설정의 DB계정 패스워드를" 
echo "          AES 방식으로 암호화할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "


enc=`grep -i "<password>" $jcfg | sed 's/ *//g' > $syspwd/enc.txt`
enc1=`grep -i "{aes}" $syspwd/enc.txt | sed 's/ *//g' > $syspwd/enc1.txt`
enc1num=`cat $syspwd/enc1.txt | wc -l`
enc2=`cat $syspwd/enc1.txt`
enc3=`cat $syspwd/enc.txt`
enc4=`cat $syspwd/enc1.txt | sed 's/^/* /'`
enc3num=`cat $syspwd/enc.txt | wc -l`


if [ $enc1num -ne 0 ]; then
   echo "■ 현황" 
   echo " "
   echo "$enc4"
   echo " "
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   if [ $enc3num -eq 0 ]; then
      echo "■ 현황: 미설정"
      echo " "
      echo -e "■ 결과: ${RED}DB connection pool 미사용${RESET}"
   else
      echo "■ 설정: $enc4"
      echo " "
      echo -e "■ 결과: ${RED}$RED1${RESET}"
   fi
fi

rm -rf $syspwd/enc.txt
rm -rf $syspwd/enc1.txt


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-07 ----------------------------"
echo "확인사항: HTTP 요청에 대한 응답 시에 헤더에 서버의 이름, 버전 등의"
echo "          정보를 제공하는 경우, 공격자가 해당 정보를 이용해 공격에"
echo "          이용할 수 있다. "
echo " "
echo "          <Djeus.servlet.response.header.serverInfo=false>"
echo "          위 설정은 기본 설정(false)이므로 필요하면 JEUSMain.xml 에"
echo "          추가 해주면됨 "
echo "-------------------------------------------------------------------"
echo " "
echo " "


respon=`grep -i -o "jeus.servlet.response.header.serverInfo=false" $jcfg | uniq | sed 's/ *//g' > $syspwd/respon.txt`

respon1=`grep -i -o "jeus.servlet.response.header.serverInfo=false" $jcfg | uniq | sed 's/ *//g' > $syspwd/respon.txt | wc -l`


respon3=`cat $syspwd/respon.txt`

respon4=`cat $syspwd/respon.txt | cut -d = -f 2`



if [ "$respon4" = "false" ] || [ "$respon4" = "FALSE" ]; then
   echo "■ 현황: $respon3" 
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
elif [ $respon1 -eq 0 ]; then
   echo "■ 현황: 미설정(미설정시 false 처리 이므로 정상)"
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"
else
   echo "■ 현황: $respon3"
   echo -e "■ 결과: ${RED}$RED1${RESET}" 
fi


rm -rf $syspwd/respon.txt




echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-02-08 ----------------------------"
echo "확인사항: JEUS 컨피그 설정 10분으로 하고, 타임아웃시간이 더 필요한"
echo "          경우 소스쪽 설정으로 늘릴 것"
echo "          timeout 설정file : webcommon.xml"
echo "-------------------------------------------------------------------"
echo " "
echo " "



echo "■ 현황"

for tmt in `find $jcfgdir -type f -name "webcommon.xml"`

do

#tmtf=`find $jcfgdir -type f -name "webcommon.xml" | grep -i -v "engine"`

tmtfile=`cat $tmt | grep -i "session-timeout" | sed 's/ *//g'` 

tmttxt=`cat $tmt | grep -i "session-timeout" | sed 's/ *//g' >> $syspwd/tmt.txt` 


echo " "
echo "- FILE & CONFIG "
echo "* $tmt"

    for cfgtmt in `cat $tmt | grep -i "session-timeout" | sed 's/ *//g'`
    do

      echo "* $cfgtmt"

    done

done

echo " "
echo " "


echo "■ 결과"
echo " "
for stout in "<session-timeout>10</session-timeout>"

do

for stouttmt in `cat $syspwd/tmt.txt`

do

if [ $stouttmt = $stout ]; then
   echo -e "* ${GREEN}$GREEN1${RESET}($stouttmt)"
else
   echo -e "* ${RED}$RED1${RESET}($stouttmt)"
fi

done

done



rm -rf $syspwd/tmt.txt


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-03-01 ----------------------------"
echo "확인사항: 운영상 불필요한 샘플 디렉터리 삭제할 것"
echo "-------------------------------------------------------------------"
echo " "
echo " "


echo -e "■ 결과: ${GREEN}$GREEN1${RESET}"


echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "--------------------------- JEUS-04-01 ----------------------------"
echo "확인사항: 마이너업그레이드 포함하여 최신 패치 진행" 
echo "-------------------------------------------------------------------"
echo " "
echo " "

jver6=`su - $jeusid -c '
jeusadmin -version
exit'`

jever="JEUS 6.0 (Fix#9)"

echo "■ 현황: $jver6"

if [ "$jver6" = "$jever" ] || [ "$jver6" = "$jever" ]; then
   echo -e "■ 결과: ${GREEN}$GREEN1${RESET}($jver6)"
else
   echo -e "■ 결과: ${RED}$RED1${RESET}($jver6)"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}=========================================== END ==========================================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"





#============================================================================================================
#========================================== JEUS 6 version END ==============================================
#============================================================================================================



;;

esac
