#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "cluster"  >>  sun_cluster-$today-$host.log
echo "---hvdisp -a-------------------"  >>  sun_cluster-$today-$host.log
hvdisp -a  >>  sun_cluster-$today-$host.log
if ps -ef | grep crsd.bin | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  sun_cluster-$today-$host.log
    echo "-crs stat -------------------"  >>  sun_cluster-$today-$host.log
    crsctl stat res -t  >>  sun_cluster-$today-$host.log
    echo "-crs init process stat-------"  >>  sun_cluster-$today-$host.log
    crsctl stat res -t -init >>  sun_cluster-$today-$host.log
fi
echo "============================="  >>  sun_cluster-$today-$host.log
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
