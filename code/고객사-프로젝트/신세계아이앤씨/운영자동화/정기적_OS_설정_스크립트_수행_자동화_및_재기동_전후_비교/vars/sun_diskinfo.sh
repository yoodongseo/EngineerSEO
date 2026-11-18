#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "disk info"  >>  sun_diskinfo-$today-$host.log
echo "---df_k----------------------"  >>  sun_diskinfo-$today-$host.log
df -k  >>  sun_diskinfo-$today-$host.log
echo "---sdxinfo-------------------"  >>  sun_diskinfo-$today-$host.log
sdxinfo >>  sun_diskinfo-$today-$host.log
echo "---iostat -En--------------------"  >>  sun_diskinfo-$today-$host.log
iostat -En >>  sun_diskinfo-$today-$host.log
echo "============================="  >>  sun_diskinfo-$today-$host.log
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
