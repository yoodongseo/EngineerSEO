#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "HW info" >>  AIX_hwinfo-$today-$host.log
echo "-----------------------------"  >>  AIX_hwinfo-$today-$host.log
prtconf >>  AIX_hwinfo-$today-$host.log
echo "============================="  >>  AIX_hwinfo-$today-$host.log
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
