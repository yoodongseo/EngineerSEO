#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Solaris

sun()
{
echo "running process"  >>  sun_running_process-$today-$host.log
echo "-safer--=---------------------"  >>  sun_running_process-$today-$host.log
ps -ef|grep safer >>  sun_running_process-$today-$host.log
echo "-polestar-------------------"  >>  sun_running_process-$today-$host.log
ps -ef|grep AGENT  >>  sun_running_process-$today-$host.log
echo "-cubeone----------------------"  >>  sun_running_process-$today-$host.log
ps -ef|grep cubeone >>  sun_running_process-$today-$host.log
echo "-Netbackup----------------------"  >>  sun_running_process-$today-$host.log
ps -ef|grep bp >>  sun_running_process-$today-$host.log
echo "-OSWatcher----------------------"  >>  sun_running_process-$today-$host.log
ps -ef|grep osw >>  sun_running_process-$today-$host.log
echo "============================="  >>  sun_running_process-$today-$host.log
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
