#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "cluster"  >>  AIX_cluster-$today-$host.log
echo "---Diagnosis of HACMP--------"  >>  AIX_cluster-$today-$host.log
/usr/es/sbin/cluster/utilities/cllscf >>  AIX_cluster-$today-$host.log
echo "---cllsnode------------------"  >>  AIX_cluster-$today-$host.log
/usr/es/sbin/cluster/utilities/cllsnode >> AIX_cluster-$today-$host.log
echo "---lssrc---------------------"  >>  AIX_cluster-$today-$host.log
lssrc -g cluster                      >>  AIX_cluster-$today-$host.log
if ps -ef | grep crsd.bin | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  AIX_cluster-$today-$host.log
    echo "-crs stat -------------------"  >>  AIX_cluster-$today-$host.log
    crsctl stat res -t  >>  AIX_cluster-$today-$host.log
    echo "-crs init process stat-------"  >>  AIX_cluster-$today-$host.log
    crsctl stat res -t -init >>  AIX_cluster-$today-$host.log
fi
echo "============================="  >>  AIX_cluster-$today-$host.log
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
