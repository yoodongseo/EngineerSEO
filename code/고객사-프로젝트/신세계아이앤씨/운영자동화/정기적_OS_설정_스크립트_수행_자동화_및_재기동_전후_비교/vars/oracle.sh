#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#Oracle
oracle()
{
echo "crsctl stat res -t"  >>  oracle-$today-$host.log
echo "---crsctl stat res -t----------------------"  >>  sysinfo-$today-$host.log
crsctl stat res -t  >>  sysinfo-$today-$host.log
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
        Oracle)
                oracle
                ;;
        *)
                ;;
esac
}

start
