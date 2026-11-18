#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "disk info"  >>  AIX_diskinfo-$today-$host.log
echo "---df_k----------------------"  >>  AIX_diskinfo-$today-$host.log
df -k  >>  AIX_diskinfo-$today-$host.log
echo "---lsdev_Cc_disk-------------"  >>  AIX_diskinfo-$today-$host.log
lsdev -Cc disk >>  AIX_diskinfo-$today-$host.log
echo "---lsvg_o--------------------"  >>  AIX_diskinfo-$today-$host.log
lsvg -o >>  AIX_diskinfo-$today-$host.log
echo "---lsvg_l---------------------"  >>  AIX_diskinfo-$today-$host.log
lsvg -o|lsvg -il >>  AIX_diskinfo-$today-$host.log
echo "---lspv-----------------------"  >>  AIX_diskinfo-$today-$host.log
lspv >>  AIX_diskinfo-$today-$host.log
echo "============================="  >>  AIX_diskinfo-$today-$host.log
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