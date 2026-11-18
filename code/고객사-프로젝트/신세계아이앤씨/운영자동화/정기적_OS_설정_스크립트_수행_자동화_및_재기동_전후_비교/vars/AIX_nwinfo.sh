#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "network info"  >>  AIX_nwinfo-$today-$host.log
echo "----ifconfig-----------------"  >>  AIX_nwinfo-$today-$host.log
ifconfig -a  >>  AIX_nwinfo-$today-$host.log
echo "------netstat_i---------------"  >>  AIX_nwinfo-$today-$host.log
netstat -i >>  AIX_nwinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  AIX_nwinfo-$today-$host.log
netstat -rn >>  AIX_nwinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  AIX_nwinfo-$today-$host.log
netstat -a|grep -i listen >>  AIX_nwinfo-$today-$host.log
echo "============================="  >>  AIX_nwinfo-$today-$host.log
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
