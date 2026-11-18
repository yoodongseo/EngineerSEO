#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "disk info"  >>  linux_diskinfo-$today-$host.log
echo "---df_k-------------------------"  >>  linux_diskinfo-$today-$host.log
df -k  >>  linux_diskinfo-$today-$host.log
echo "---fdisk_l----------------------"  >>  linux_diskinfo-$today-$host.log
fdisk -l  >>  linux_diskinfo-$today-$host.log
echo "---multipath_ll-----------------"  >>  linux_diskinfo-$today-$host.log
multipath -ll >>  linux_diskinfo-$today-$host.log
echo "---pv info----------------------"  >>  linux_diskinfo-$today-$host.log
pvs >>  linux_diskinfo-$today-$host.log
echo "---lv info----------------------"  >>  linux_diskinfo-$today-$host.log
lvs >>  linux_diskinfo-$today-$host.log
echo "============================="  >>  linux_diskinfo-$today-$host.log
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
