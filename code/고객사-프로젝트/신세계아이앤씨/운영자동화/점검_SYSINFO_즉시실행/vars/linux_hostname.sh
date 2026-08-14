#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "=============================" > sysinfo-$today-$host.log
echo "hostname" >>  sysinfo-$today-$host.log
echo "-----------------------------"  >>  sysinfo-$today-$host.log
hostname >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log
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

