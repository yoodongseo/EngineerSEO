#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "ntp"  >>  AIX_ntp-$today-$host.log
echo "-ntp------------------------"  >>  AIX_ntp-$today-$host.log
ps –ef |grep xntpd >>  AIX_ntp-$today-$host.log
}


start()
{
case $SYSTEM in
        SunOS)
                sun
                ;;
        AIX)
                aix
                ;;
        HP-UX)
                hp
                ;;
        Linux)
                Linux
                ;;
        *)
                ;;
esac
}

start
