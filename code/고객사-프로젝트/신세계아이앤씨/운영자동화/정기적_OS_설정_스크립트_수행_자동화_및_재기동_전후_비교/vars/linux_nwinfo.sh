#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "network info"  >>  linux_nwinfo-$today-$host.log
echo "----ifconfig-a---------------"  >>  linux_nwinfo-$today-$host.log
ifconfig -a  >>  linux_nwinfo-$today-$host.log
echo "------netstat_i---------------"  >>  linux_nwinfo-$today-$host.log
netstat -i >>  linux_nwinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  linux_nwinfo-$today-$host.log
netstat -rn >>  linux_nwinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  linux_nwinfo-$today-$host.log
netstat -a|grep -i listen >>  linux_nwinfo-$today-$host.log
echo "------bonding information--------------"  >>  linux_nwinfo-$today-$host.log
cat /proc/net/bonding/bond* >>  linux_nwinfo-$today-$host.log
echo "============================="  >>  linux_nwinfo-$today-$host.log
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
