#!/bin/bash


export LANG=ko_KR.utf8


RED1="조치필요"
GREEN1="양호"
YELLOW1="확인필요"

RESET='\033[m'
YELLOW='  '
RED=' '
GREEN=' '
BLUE=' '
THICK=' '



i=`ps -ef | grep -i webtob |grep -v grep | grep -v root | head -1 | awk '{print $1}' | sed 's/[^a-zA-Z0-9]//g'`

i1=`grep $i /etc/passwd | cut -d : -f 1`

i2=`grep $i /etc/passwd | cut -d : -f 6`

gid=`grep $i /etc/passwd | cut -d : -f 4`

gid1=`grep $gid /etc/group | cut -d : -f 1`

id=`grep -w $i /etc/passwd |cut -d : -f 6`

WEBTOBDIR=`grep -i "webtobdir=" $i2/.bash_profile | cut -d = -f 2 | sed 's/"//g' | uniq`

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}====================================== WEBTOB START ======================================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "
echo "----------------------- WEB/WAS-WEBTOB-01-01-----------------------" 
echo "확인사항: WebtoB 데몬 계정이 root 권한으로 운영되지 않도록 해야함"
echo "          서비스포트가 1024 이하인 경우 root 권한 필요함"
echo "-------------------------------------------------------------------"

res=`grep -i -w port $WEBTOBDIR/config/http.m`

echo " "
echo " "
echo "[PORT STATUS]"
#echo "*" $res
echo " "

for res1 in `grep -i -w port $WEBTOBDIR/config/http.m |  sed 's/[^0-9]//g'`
do
if [ $res1 -lt 1024 ]; then
   echo -e "* $res1 = ${YELLOW}$YELLOW1${RESET}"
else
   echo -e "* $res1 = ${GREEN}$GREEN1${RESET}"
fi
done
echo " "
echo "[WBIN ROOT PERMISSION FILE]"
echo " "

wbindir=$WEBTOBDIR/bin
#wbinfile=`find $wbindir -type f -perm 4755 -o -perm 4750 -o -perm 4700 -o -perm 4775 `
#wbinfile1=`ls -lart $wbinfile`
#wbinfilenum=`find $wbindir -type f -perm 4755 -o -perm 4750 -o -perm 4700 -o -perm 4775| wc -l`

wbinrfile=`find $wbindir -type f -user root`
wbinrfile1=`ls -lart $wbinrfile`
wbinrfilenum=`find $wbindir -type f -user root | wc -l`


if [ $wbinrfilenum -eq 0 ]; then
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo -e "* 현황 : $wbinrfile1"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}" 
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-02-----------------------"
echo "확인사항: WebtoB 홈디렉터리이하 모든 디렉터리는 750이하로 변경"
echo "-------------------------------------------------------------------"

WEBTOBOSDIR=`grep -i "webtobdir=" $i2/.bash_profile | cut -d = -f 2 | sed 's/"//g'| cut -d / -f 2 | uniq`

echo " "
ii=`ps -ef | grep -i webtob |grep -v grep | grep -v root | head -1 | awk '{print $1}'`
#cd $i2
echo "[Directory]"
echo " "

dirhome=`find /$WEBTOBOSDIR -maxdepth 1 -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | grep -i "webtob*" | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
dirhomenum=`find /$WEBTOBOSDIR -maxdepth 1 -type d -not -perm 750 -not -perm 700 -exec ls -ld {} \; | grep -i "webtob*" | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'|wc -l`
dirhome1=`find $WEBTOBDIR/* -prune -type d -not -perm 750 -not -perm 700 -not -perm 740 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
dirhome1num=`find $WEBTOBDIR/* -prune -type d -not -perm 750 -not -perm 700 -not -perm 740 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' |wc -l`

if [ $dirhomenum -gt 0 ];then
   echo "-OS HOME-"
   echo " "
   echo "$dirhome"
   echo -e "* 결과 : ${RED}$RED1${RESET}"
   echo " " 
else
   echo "-OS HOME-"
   echo " "
   echo "* OS HOME has no directory"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
   echo " " 
fi

if [ $dirhome1num -gt 0 ];then
   echo "-WEBTOB HOME-"
   echo " "
   echo "$dirhome1"
   echo -e "* 결과 : ${RED}$RED1${RESET}"
   echo " " 
else
   echo " "
   echo "-WEBTOB HOME-"
   echo " "
   echo "* WEBTOB HOME has no directory"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
   echo " "
fi

echo " "
echo " "
echo "[File]"
echo " "

file=`find $WEBTOBDIR/* -prune -type f -not -perm 640 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
filenum=`find $WEBTOBDIR/* -prune -type f -not -perm 640 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

if [ $filenum -gt 0 ]; then
   echo "$file"
   echo -e "* 결과 : ${RED}$RED1${RESET}"
   echo " "
else
   echo "-WEBTOB HOME-"
   echo " "
   echo "* WEBTOB HOME has no file"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
   echo " "
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-03-----------------------"
echo "확인사항: WebtoB 설정파일 퍼미션 600 이하 혹은 700 이하로 변경"
echo "-------------------------------------------------------------------"
echo " "

httpmod=`find $WEBTOBDIR/config/ -type f  -exec ls -lrt {} \; |grep -w http.m | grep -v "http.m.[0-9]" | grep -v "http.m.[A-Za-z]"`
echo "* 현황 : $httpmod"


httpm=`find $WEBTOBDIR/config/http.m -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
httpm1=`find $WEBTOBDIR/config/http.m -not -perm 600 -not -perm 700 -exec ls -alrt {} \; | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`
httpm2=`find $WEBTOBDIR/config/http.m -type f -exec ls -lart {} \; | awk '{print $3}'`
httpm3=`find $WEBTOBDIR/config/http.m -type f -exec ls -lart {} \; | awk '{print $4}'`


echo " "

if [ $httpm1 -eq 0 ] && [ $httpm2 = $i1 ] && [ $httpm3 = $gid1 ]; then
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}($httpmod)"
else
   echo -e "* 결과 : ${RED}$RED1${RESET}($httpmod)"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-04-----------------------"
echo "확인사항: 소스파일 퍼미션 640 이하로 변경"
echo "-------------------------------------------------------------------"
echo " "

echo -e "* 결과 : ${YELLOW}예외처리${RESET}(업무단 조치 필요 소스디렉터리 750, 소스파일 640 조치 필요"
echo "         Other쪽 권한이 꼭 필요한 경우만 소스파일 644)"

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "


echo "----------------------- WEB/WAS-WEBTOB-01-05-----------------------"
echo "확인사항: WebtoB 노드절에 DIRINDEX 옵션값 -index 되어 있는지 확인"
echo "          설정이 없으면 기본적으로 양호함"
echo "-------------------------------------------------------------------"
echo " "

#for id in `grep $i1 /etc/passwd |cut -d : -f 6`
#do
index=`find $WEBTOBDIR/config/http.m -type f -exec grep -i index {} \;| awk '{gsub(/^ */, ""); print}' |uniq`
innum=`grep -i index $WEBTOBDIR/config/http.m | wc -l`

if [ $innum -eq 0 ];then
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
else
   echo -e "* 결과 : ${YELLOW}$YELLOW1${RESET} ($index)"
fi
#done

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-06-----------------------"
echo "확인사항: 로그디렉터리 750 이하, 로그 파일 640 이하로 변경(umask 027)"
echo "-------------------------------------------------------------------"
echo " "


wumask6=`su - $i1 -c '
umask
exit'`

echo "[USMAK]"
echo " "
if [ $wumask6 -eq 027 ]; then
   echo -e "* umask : $wumask6 (${GREEN}$GREEN1${RESET})"
else
   echo -e "* umask : $wumask6 (${RED}$RED1${RESET})"
fi

echo " "
echo " "

su - $i1 -c '
alias wlog | cut -d = -f 2 | xargs > wlog.sh
sed -e "s/\$/;pwd;/" wlog.sh > wlog1.sh
sh wlog1.sh > wlog.txt
exit'

webpwd=`grep $i1 /etc/passwd |cut -d : -f 6`
syspwd=`grep example_user /etc/passwd |cut -d : -f 6`

wlogfile=`find $webpwd -name wlog.txt`
wlogfilenum=`find $webpwd -name wlog.txt|wc -l`

if [ $wlogfilenum -eq 1 ]; then
   echo `mv $wlogfile $syspwd`
else
   echo "확인필요"
fi 


su - $i1 -c '
rm -rf wlog.sh
rm -rf wlog1.sh
exit'

echo "[Directory]"
echo " "

wlog=`cat $syspwd/wlog.txt`

wlogdir=`find $wlog -type d -not -perm 750 -not -perm 700 -not -perm 740 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
wlogdir1=`find $wlog -type d -not -perm 750 -not -perm 700 -not -perm 740 -exec ls -ld {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' | wc -l`

if [ $wlogdir1 -gt 0 ]; then
   echo "- WLOG HOME -"
   echo " "
   echo "* $wlogdir"
   echo -e "* 결과 : ${RED}$RED1${RESET}"
   echo " "
else 
   echo "- WLOG HOME -"
   echo " "
   echo "* WLOG HOME has no directory"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
   echo " "
fi

echo " "
echo " "
echo "[File]"
echo " "

wlogfile=`find $wlog -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \; | awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'`
wlogfile1=`find $wlog -type f -not -perm 640 -not -perm 600 -exec ls -lart {} \;| awk '{print "* "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10}'| wc -l`

if [ $wlogfile1 -gt 0 ]; then
   echo "- WLOG FILE -"
   echo " "
   echo "$wlogfile"
   echo -e "* 결과 : ${RED}$RED1${RESET}"
   echo " "
else
   echo "- WLOG FILE -"
   echo " "
   echo "* WLOG HOME has no file"
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}"
   echo " "
fi
   
rm -rf $syspwd/wlog.txt

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-07-----------------------"
echo "확인사항: 400, 401, 403, 404, 500, 503 등 모든에러코드에 대하여"
echo "          별도의 에러 메시지를 설정한 경우만 양호"
echo "-------------------------------------------------------------------"
echo " "

echo "[ERRORDOCUMENT]"
document=`grep -i "status =" $WEBTOBDIR/config/http.m`
documentnum=`grep -i "status =" $WEBTOBDIR/config/http.m | wc -l`

if [ $documentnum -ge 2 ]; then
   echo "$document"
   echo " "
   echo -e "* 결과: ${GREEN}$GREEN1${RESET}"
else
   echo "$document"
   echo " "
   echo -e "* 결과: ${RED}$RED1${RESET}"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-01-08-----------------------"
echo "확인사항: 컨피그 파일 등이 WEB엔진계정 전용소유이고"
echo "          600 또는 700의 퍼미션으로 되어있을 때 양호"
echo "-------------------------------------------------------------------"
echo " "

own=`ls -alrt $WEBTOBDIR/config/http.m` 
own1=`ls -alrt $WEBTOBDIR/config/http.m| awk '{print $3}'` 
mod=`find $WEBTOBDIR/config/ -type f -perm 600 -o -perm 700 -name "http.m" |grep -w http.m | grep -v "http.m.[0-9]" | grep -v "http.m.[A-Za-z]"`
mod2=`find $WEBTOBDIR/config/ -type f -name "http.m" |grep -w http.m | grep -v "http.m.[0-9]" | grep -v "http.m.[A-Za-z]"`
modnum=`find $WEBTOBDIR/config/ -type f -perm 600 -o -perm 700 -name "http.m" |grep -w http.m | grep -v "http.m.[0-9]" | grep -v "http.m.[A-Za-z]" | wc -l`

mod3=`ls -lart $mod2 | awk '{print $1}'`
#mod4=`ls -alrt $i2/webtob*/config/http.m| awk '{print $1}'` 

echo "[http.m file]"
echo " "
echo "$own"
echo " "

if [ $own1 == $i1 ]; then
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}( 소유자: $own1 ) "
else
   echo -e "* 결과 : ${RED}$RED1${RESET}( 소유자 : $own1 )"
fi

if [ $modnum -ne 0 ]; then 
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}( 권한 : $mod3 ) "
else
   echo -e "* 결과 : ${RED}$RED1${RESET}( 권한 : $mod3 )"
fi

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-02-01-----------------------"
echo "확인사항: 불필요한 샘플 디렉터리 삭제"
echo "-------------------------------------------------------------------"
echo " "

echo -e "* 결과 : ${GREEN}완료처리${RESET}"

echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo " "
echo " "

echo "----------------------- WEB/WAS-WEBTOB-03-01-----------------------"
echo "확인사항: 마이너업그레이드 포함하여 최신 패치 진행"
echo "-------------------------------------------------------------------"
echo " "

ver=`su - $i1 -c "wscfl -version > ver.txt"`

verfile=`find $webpwd -name "ver.txt"`
verfilenum=`find $webpwd -name "ver.txt"|wc -l`


if [ $verfilenum -eq 1 ]; then
   echo `mv $verfile $syspwd`
else
   echo "확인필요"
fi 



version=`cat $syspwd/ver.txt | awk '{print $1,$2,$3,$4,$5,$6}' > $syspwd/ver1.txt`

versionfile=`find $syspwd -name "ver.txt"`
versionfilenum=`find $syspwd -name "ver.txt" | wc -l`

if [ $versionfilenum -eq 1 ]; then
   echo `rm -rf $syspwd/ver.txt`
else
   echo "확인필요"
fi 

ver4="WebtoB 4.1 SP 9 Fix #1"
ver5="WebtoB 5.0 SP 0 Fix #4"

wver=`cat $syspwd/ver1.txt`

echo "Version : $wver"

#patch="패치필요"

echo " "

if [ "$wver" = "$ver4" ] || [ "$wver" = "$ver5" ]; then
   echo -e "* 결과 : ${GREEN}$GREEN1${RESET}( $wver )"
else
   echo -e "* 결과 : ${YELLOW}패치필요${RESET}( $wver )"
fi


rm -rf $syspwd/ver1.txt



echo " "
echo " "
echo -e "${YELLOW}==========================================================================================${RESET}"
echo -e "${YELLOW}=========================================== END ==========================================${RESET}"
echo -e "${YELLOW}==========================================================================================${RESET}"
