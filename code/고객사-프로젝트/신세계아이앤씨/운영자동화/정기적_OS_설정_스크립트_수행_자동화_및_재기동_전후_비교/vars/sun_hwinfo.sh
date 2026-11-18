#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "HW info" >>  sun_hwinfo-$today-$host.log
echo "--/usr/sbin/prtdiag----------"  >>  sun_hwinfo-$today-$host.log
/usr/sbin/prtdiag >>  sun_hwinfo-$today-$host.log
echo "============================="  >>  sun_hwinfo-$today-$host.log
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
