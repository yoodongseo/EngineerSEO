#!/bin/ksh

host=`hostname`
today=`date +%Y%m%d`
SYSTEM=`(uname -s) 2>/dev/null`

#AIX
aix()
{
echo "=============================" > sysinfo-$today-$host.log
echo "hostname" >>  sysinfo-$today-$host.log
echo "-----------------------------"  >>  sysinfo-$today-$host.log
hostname >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "HW info" >>  sysinfo-$today-$host.log
echo "-----------------------------"  >>  sysinfo-$today-$host.log
prtconf >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "oslevel"  >>  sysinfo-$today-$host.log
echo "---oslevel-------------------"  >>  sysinfo-$today-$host.log
oslevel  >>  sysinfo-$today-$host.log
echo "---oslevels------------------"  >>  sysinfo-$today-$host.log
oslevel -s >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "cluster"  >>  sysinfo-$today-$host.log
echo "---Diagnosis of HACMP--------"  >>  sysinfo-$today-$host.log
/usr/es/sbin/cluster/utilities/cllscf >>  sysinfo-$today-$host.log
echo "---cllsnode------------------"  >>  sysinfo-$today-$host.log
/usr/es/sbin/cluster/utilities/cllsnode >> sysinfo-$today-$host.log
echo "---lssrc---------------------"  >>  sysinfo-$today-$host.log
lssrc -g cluster                      >>  sysinfo-$today-$host.log
if ps -ef | grep crsd.bin | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  sysinfo-$today-$host.log
    echo "-crs stat -------------------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t  >>  sysinfo-$today-$host.log
    echo "-crs init process stat-------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t -init >>  sysinfo-$today-$host.log
fi
echo "============================="  >>  sysinfo-$today-$host.log

echo "network info"  >>  sysinfo-$today-$host.log
echo "----ifconfig-----------------"  >>  sysinfo-$today-$host.log
ifconfig -a  >>  sysinfo-$today-$host.log
echo "------netstat_i---------------"  >>  sysinfo-$today-$host.log
netstat -i >>  sysinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  sysinfo-$today-$host.log
netstat -rn >>  sysinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  sysinfo-$today-$host.log
netstat -a|grep -i listen >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "disk info"  >>  sysinfo-$today-$host.log
echo "---df_k----------------------"  >>  sysinfo-$today-$host.log
df -k  >>  sysinfo-$today-$host.log
echo "---lsdev_Cc_disk-------------"  >>  sysinfo-$today-$host.log
lsdev -Cc disk >>  sysinfo-$today-$host.log
echo "---lsvg_o--------------------"  >>  sysinfo-$today-$host.log
lsvg -o >>  sysinfo-$today-$host.log
echo "---lsvg_l---------------------"  >>  sysinfo-$today-$host.log
lsvg -o|lsvg -il >>  sysinfo-$today-$host.log
echo "---lspv-----------------------"  >>  sysinfo-$today-$host.log
lspv >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "running process"  >>  sysinfo-$today-$host.log
echo "-polestar-------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep AGENT  >>  sysinfo-$today-$host.log
echo "-ntp ---------------------"  >>  sysinfo-$today-$host.log
ntpq -p >>  sysinfo-$today-$host.log
echo "-castle-----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep castle >>  sysinfo-$today-$host.log
echo "-safer--=---------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep safer >>  sysinfo-$today-$host.log
echo "-cubeone----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep cube >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "all process"  >>  sysinfo-$today-$host.log
echo "-ps ef-------------------------"  >>  sysinfo-$today-$host.log
ps -ef  >>  sysinfo-$today-$host.log
echo "-ps au-------------------------"  >>  sysinfo-$today-$host.log
ps aux >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log
}



#Solaris

sun()
{
echo "=============================" > sysinfo-$today-$host.log
echo "hostname" >>  sysinfo-$today-$host.log
echo "-----------------------------"  >>  sysinfo-$today-$host.log
hostname >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "HW info" >>  sysinfo-$today-$host.log
echo "--/usr/sbin/prtdiag----------"  >>  sysinfo-$today-$host.log
/usr/sbin/prtdiag >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "oslevel"  >>  sysinfo-$today-$host.log
echo "---oslevel-------------------"  >>  sysinfo-$today-$host.log
uname -a  >>  sysinfo-$today-$host.log
echo "---showrev------------------"  >>  sysinfo-$today-$host.log
showrev >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "cluster"  >>  sysinfo-$today-$host.log
echo "---hvdisp -a-------------------"  >>  sysinfo-$today-$host.log
hvdisp -a  >>  sysinfo-$today-$host.log
if ps -ef | grep crsd.bin | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  sysinfo-$today-$host.log
    echo "-crs stat -------------------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t  >>  sysinfo-$today-$host.log
    echo "-crs init process stat-------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t -init >>  sysinfo-$today-$host.log
fi
echo "============================="  >>  sysinfo-$today-$host.log

echo "network info"  >>  sysinfo-$today-$host.log
echo "----ifconfig-a---------------"  >>  sysinfo-$today-$host.log
ifconfig -a  >>  sysinfo-$today-$host.log
echo "------netstat_i---------------"  >>  sysinfo-$today-$host.log
netstat -i >>  sysinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  sysinfo-$today-$host.log
netstat -rn >>  sysinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  sysinfo-$today-$host.log
netstat -a|grep -i listen >>  sysinfo-$today-$host.log
echo "------dsphanet--------------"  >>  sysinfo-$today-$host.log
dsphanet >>  sysinfo-$today-$host.log
echo "------dsppoll--------------"  >>  sysinfo-$today-$host.log
dsppoll >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "disk info"  >>  sysinfo-$today-$host.log
echo "---df_k----------------------"  >>  sysinfo-$today-$host.log
df -k  >>  sysinfo-$today-$host.log
echo "---sdxinfo-------------------"  >>  sysinfo-$today-$host.log
sdxinfo >>  sysinfo-$today-$host.log
echo "---iostat -En--------------------"  >>  sysinfo-$today-$host.log
iostat -En >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "running process"  >>  sysinfo-$today-$host.log
echo "-polestar-------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep AGENT  >>  sysinfo-$today-$host.log
echo "-ntp ---------------------"  >>  sysinfo-$today-$host.log
ntpq -p >>  sysinfo-$today-$host.log
echo "-castle-----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep castle >>  sysinfo-$today-$host.log
echo "-safer--=---------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep safer >>  sysinfo-$today-$host.log
echo "-cubeone----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep cube >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "all process"  >>  sysinfo-$today-$host.log
echo "-ps ef-------------------------"  >>  sysinfo-$today-$host.log
ps -ef  >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log
}

#Linux

Linux()
{
echo "=============================" > sysinfo-$today-$host.log
echo "hostname" >>  sysinfo-$today-$host.log
echo "-----------------------------"  >>  sysinfo-$today-$host.log
hostname >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "HW info" >>  sysinfo-$today-$host.log
echo "--dmidecode for BIOS------------------"  >>  sysinfo-$today-$host.log
/usr/sbin/dmidecode -t bios      >>  sysinfo-$today-$host.log
echo "--dmidecode for SYSTEM----------------"  >>  sysinfo-$today-$host.log
/usr/sbin/dmidecode -t system    >>  sysinfo-$today-$host.log
echo "--dmidecode for PROCESSOR-------------"  >>  sysinfo-$today-$host.log
/usr/sbin/dmidecode -t processor >>  sysinfo-$today-$host.log
echo "--dmidecode for MEMORY----------------"  >>  sysinfo-$today-$host.log
/usr/sbin/dmidecode -t memory    >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "oslevel"  >>  sysinfo-$today-$host.log
echo "---oslevel-------------------"  >>  sysinfo-$today-$host.log
uname -a  >>  sysinfo-$today-$host.log
echo "---Linux Release------------------"  >>  sysinfo-$today-$host.log
/usr/bin/lsb_release -a >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "cluster"  >>  sysinfo-$today-$host.log
echo "---clustat-------------------"  >>  sysinfo-$today-$host.log
/usr/sbin/clustat  >>  sysinfo-$today-$host.log
if ps -ef | grep crsd.bin | grep -v grep > /dev/null 2>&1
then 
    echo "crs stat"  >>  sysinfo-$today-$host.log
    echo "-crs stat -------------------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t  >>  sysinfo-$today-$host.log
    echo "-crs init process stat-------"  >>  sysinfo-$today-$host.log
    crsctl stat res -t -init >>  sysinfo-$today-$host.log
fi
echo "============================="  >>  sysinfo-$today-$host.log

echo "network info"  >>  sysinfo-$today-$host.log
echo "----ifconfig-a---------------"  >>  sysinfo-$today-$host.log
ifconfig -a  >>  sysinfo-$today-$host.log
echo "------netstat_i---------------"  >>  sysinfo-$today-$host.log
netstat -i >>  sysinfo-$today-$host.log
echo "------netstat_rn--------------"  >>  sysinfo-$today-$host.log
netstat -rn >>  sysinfo-$today-$host.log
echo "------netstat_a listen--------------"  >>  sysinfo-$today-$host.log
netstat -a|grep -i listen >>  sysinfo-$today-$host.log
echo "------bonding information--------------"  >>  sysinfo-$today-$host.log
cat /proc/net/bonding/bond* >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "disk info"  >>  sysinfo-$today-$host.log
echo "---df_k-------------------------"  >>  sysinfo-$today-$host.log
df -k  >>  sysinfo-$today-$host.log
echo "---fdisk_l----------------------"  >>  sysinfo-$today-$host.log
fdisk -l  >>  sysinfo-$today-$host.log
echo "---multipath_ll-----------------"  >>  sysinfo-$today-$host.log
multipath -ll >>  sysinfo-$today-$host.log
echo "---pv info----------------------"  >>  sysinfo-$today-$host.log
pvs >>  sysinfo-$today-$host.log
echo "---lv info----------------------"  >>  sysinfo-$today-$host.log
lvs >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "running process"  >>  sysinfo-$today-$host.log
echo "-polestar-------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep AGENT  >>  sysinfo-$today-$host.log
echo "-ntp ---------------------"  >>  sysinfo-$today-$host.log
ntpq -p >>  sysinfo-$today-$host.log
echo "-castle-----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep castle >>  sysinfo-$today-$host.log
echo "-safer--=---------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep safer >>  sysinfo-$today-$host.log
echo "-cubeone----------------------"  >>  sysinfo-$today-$host.log
ps -ef|grep cube >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log

echo "all process"  >>  sysinfo-$today-$host.log
echo "-ps ef-------------------------"  >>  sysinfo-$today-$host.log
ps -ef  >>  sysinfo-$today-$host.log
echo "============================="  >>  sysinfo-$today-$host.log
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
svradm