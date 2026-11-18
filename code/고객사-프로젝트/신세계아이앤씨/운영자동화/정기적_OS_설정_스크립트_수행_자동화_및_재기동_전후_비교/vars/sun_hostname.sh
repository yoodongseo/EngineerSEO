#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "=============================" > sun_hostname-$today-$host.log
echo "hostname" >>  sun_hostname-$today-$host.log
echo "-----------------------------"  >>  sun_hostname-$today-$host.log
hostname >>  sun_hostname-$today-$host.log
echo "============================="  >>  sun_hostname-$today-$host.log
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
