#!/bin/sh

LANG=C
export LANG


echo "********************************************************************"
echo "*                      CAS(Oracle_LINUX) Checklist                 *"
echo "********************************************************************"
echo "*          Copyright 2021 CAS Co. Ltd. All right Reserved          *"
echo "********************************************************************"
echo " "

alias ls=ls
alias grep=/bin/grep

if [ -f /usr/ucb/echo ]
   then
      alias echo=/usr/ucb/echo
fi

_HOSTNAME=`/bin/hostname`
_PWD=`/bin/pwd`

mkdir $_PWD/tmp
_TMP_DIR=$_PWD/tmp

# Oracle 진단 스크립트 실행
echo ""
echo "################# Run the Oracle Diagnostics Script #################"
echo ""
echo ""
echo "[ Currently running ORACLE path ]"
echo $ORACLE_HOME 
echo ""
echo ""
echo ""
echo "   > Enter your Oracle home directory. "
while true
do 
   if [ -d $ORACLE_HOME/network ]
      then 
         break
      else
         echo "   The directory you entered does not exist. Please enter again."
         echo " "
   fi
done
echo " "
echo $_ORA_HOME > $_TMP_DIR/ora_home_dir.txt

# end script
