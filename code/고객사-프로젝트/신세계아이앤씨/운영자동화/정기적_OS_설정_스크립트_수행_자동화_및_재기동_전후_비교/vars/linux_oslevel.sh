#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "oslevel"  >>  linux_oslevel-$today-$host.log
echo "---oslevel-------------------"  >>  linux_oslevel-$today-$host.log
uname -a  >>  linux_oslevel-$today-$host.log
echo "---Linux Release------------------"  >>  linux_oslevel-$today-$host.log
/usr/bin/lsb_release -a >>  linux_oslevel-$today-$host.log
echo "============================="  >>  linux_oslevel-$today-$host.log
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
