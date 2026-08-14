#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Linux

Linux()
{
echo "running process"  >>  linux_running_process-$today-$host.log
echo "-safer------------------------"  >>  linux_running_process-$today-$host.log
ps -ef|grep safer >>  linux_running_process-$today-$host.log
echo "-polestar-------------------"  >>  linux_running_process-$today-$host.log
ps -ef|grep AGENT  >>  linux_running_process-$today-$host.log
echo "-cubeone----------------------"  >>  linux_running_process-$today-$host.log
ps -ef|grep cubeone >>  linux_running_process-$today-$host.log
echo "-Netbackup----------------------"  >>  linux_running_process-$today-$host.log
ps -ef|grep bp >>  linux_running_process-$today-$host.log
echo "-OSWatcher----------------------"  >>  linux_running_process-$today-$host.log
ps -ef|grep osw >>  linux_running_process-$today-$host.log
echo "============================="  >>  linux_running_process-$today-$host.log
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
