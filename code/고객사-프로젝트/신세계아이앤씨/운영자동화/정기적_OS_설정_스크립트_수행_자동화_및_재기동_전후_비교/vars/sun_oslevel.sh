#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "oslevel"  >>  sun_oslevel-$today-$host.log
echo "---oslevel-------------------"  >>  sun_oslevel-$today-$host.log
uname -a  >>  sun_oslevel-$today-$host.log
echo "---showrev------------------"  >>  sun_oslevel-$today-$host.log
showrev >>  sun_oslevel-$today-$host.log
echo "============================="  >>  sun_oslevel-$today-$host.log
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
