#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "running process"  >>  AIX_running_process-$today-$host.log
echo "-safer--=---------------------"  >>  AIX_running_process-$today-$host.log
ps -ef|grep safer >>  AIX_running_process-$today-$host.log
echo "-polestar-------------------"  >>  AIX_running_process-$today-$host.log
ps -ef|grep AGENT  >>  AIX_running_process-$today-$host.log
echo "-cubeone----------------------"  >>  AIX_running_process-$today-$host.log
ps -ef|grep cubeone >>  AIX_running_process-$today-$host.log
echo "-Netbackup----------------------"  >>  AIX_running_process-$today-$host.log
ps -ef|grep bp >>  AIX_running_process-$today-$host.log
echo "-OSWatcher----------------------"  >>  AIX_running_process-$today-$host.log
ps -ef|grep osw >>  AIX_running_process-$today-$host.log
echo "============================="  >>  AIX_running_process-$today-$host.log
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
