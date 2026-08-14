#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "oslevel"  >>  AIX_oslevel-$today-$host.log
echo "---oslevel-------------------"  >>  AIX_oslevel-$today-$host.log
oslevel  >>  AIX_oslevel-$today-$host.log
echo "---oslevels------------------"  >>  AIX_oslevel-$today-$host.log
oslevel -s >>  AIX_oslevel-$today-$host.log
echo "============================="  >>  AIX_oslevel-$today-$host.log
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
