#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`
#Linux

Linux()
{
echo "HW info" >>  sysinf2o-$today-$host.log
echo "--dmidecode for BIOS------------------"  >>  sysinf2o-$today-$host.log
/usr/sbin/dmidecode -t bios      >>  sysinf2o-$today-$host.log
echo "--dmidecode for SYSTEM----------------"  >>  sysinf2o-$today-$host.log
/usr/sbin/dmidecode -t system    >>  sysinf2o-$today-$host.log
echo "--dmidecode for PROCESSOR-------------"  >>  sysinf2o-$today-$host.log
/usr/sbin/dmidecode -t processor >>  sysinf2o-$today-$host.log
echo "--dmidecode for MEMORY----------------"  >>  sysinf2o-$today-$host.log
/usr/sbin/dmidecode -t memory    >>  sysinf2o-$today-$host.log
echo "============================="  >>  sysinf2o-$today-$host.log
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

