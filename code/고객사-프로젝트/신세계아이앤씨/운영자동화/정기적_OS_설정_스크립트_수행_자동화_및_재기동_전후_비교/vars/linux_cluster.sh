#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "cluster"  >>  linux_cluster-$today-$host.log 2>&1
echo "---clustat-------------------"  >>  linux_cluster-$today-$host.log 2>&1
/usr/sbin/clustat  >>  linux_cluster-$today-$host.log 2>&1
if ps -ef | grep oracleFALCON | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  linux_cluster-$today-$host.log 2>&1
    echo "-crs stat -------------------"  >>  linux_cluster-$today-$host.log 2>&1
    /oracle/app/oracle/product/grid/bin/crsctl stat res -t  >>  linux_cluster-$today-$host.log 2>&1
    echo "-crs init process stat-------"  >>  linux_cluster-$today-$host.log 2>&1
    /oracle/app/oracle/product/grid/bin/crsctl stat res -t -init >>  linux_cluster-$today-$host.log 2>&1
fi
echo "============================="  >>  linux_cluster-$today-$host.log 2>&1
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
