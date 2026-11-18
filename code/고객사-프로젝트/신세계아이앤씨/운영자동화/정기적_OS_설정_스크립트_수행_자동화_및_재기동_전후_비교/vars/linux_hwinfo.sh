#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`
#Linux

Linux()
{
echo "HW info" >>  linux_hwinfo-$today-$host.log
echo "--dmidecode for BIOS------------------"  >>  linux_hwinfo-$today-$host.log
/usr/sbin/dmidecode -t bios      >>  linux_hwinfo-$today-$host.log
echo "--dmidecode for SYSTEM----------------"  >>  linux_hwinfo-$today-$host.log
/usr/sbin/dmidecode -t system    >>  linux_hwinfo-$today-$host.log
echo "--dmidecode for PROCESSOR-------------"  >>  linux_hwinfo-$today-$host.log
/usr/sbin/dmidecode -t processor >>  linux_hwinfo-$today-$host.log
echo "--dmidecode for MEMORY----------------"  >>  linux_hwinfo-$today-$host.log
/usr/sbin/dmidecode -t memory    >>  linux_hwinfo-$today-$host.log
echo "============================="  >>  linux_hwinfo-$today-$host.log
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
