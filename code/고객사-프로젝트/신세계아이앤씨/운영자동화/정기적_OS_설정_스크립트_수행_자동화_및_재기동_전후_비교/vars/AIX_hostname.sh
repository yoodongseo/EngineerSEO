#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "=============================" > AIX_hostname-$today-$host.log
echo "hostname" >>  AIX_hostname-$today-$host.log
echo "-----------------------------"  >>  AIX_hostname-$today-$host.log
hostname >>  AIX_hostname-$today-$host.log
echo "============================="  >>  AIX_hostname-$today-$host.log
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
