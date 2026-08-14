#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "network info"  >>  sun_nwinfo-$today-$host.log
echo "----ifconfig-a---------------"  >>  sun_nwinfo-$today-$host.log
ifconfig -a  >>  sun_nwinfo-$today-$host.log
echo "------netstat_i---------------"  >>  sun_nwinfo-$today-$host.log
netstat -i >>  sun_nwinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  sun_nwinfo-$today-$host.log
netstat -rn >>  sun_nwinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  sun_nwinfo-$today-$host.log
netstat -a|grep -i listen >>  sun_nwinfo-$today-$host.log
echo "------dsphanet--------------"  >>  sun_nwinfo-$today-$host.log
dsphanet >>  sun_nwinfo-$today-$host.log
echo "------dsppoll--------------"  >>  sun_nwinfo-$today-$host.log
dsppoll >>  sun_nwinfo-$today-$host.log
echo "============================="  >>  sun_nwinfo-$today-$host.log
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
