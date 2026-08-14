#!/bin/bash


LANG=C
export LANG

clear


echo -e "\033[1m"　▶ plese wait...."\033[m"
echo ""
sleep 3

echo ""
echo ""
echo -e "\033[1m"==============================  START  =============================="\033[m" 
echo ""


IP=`ifconfig -a | grep  "inet addr" | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | awk -F: '{print $2}'`

RESULT_FILE=./Linux"│"`hostname`"│"$IP.txt
CHECK_FILE=`ls ./"$RESULT_FILE" 2>/dev/null | wc -l`

echo "===============  Linux Server Security Check  ==============="                                                                 > $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo "Copyright (c) 2019 Norma Co. Ltd. All right Reserved"                                                                     	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1



echo [U-1]root 계정 원격 접속 제한
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-1]root 계정 원격 접속 제한                                                                                                 	   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [1-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ `find /etc -type f -name "sshd_config" | wc -l` -eq 0 ]
	then
		echo "sshd_config 파일을 찾을 수 없음"                                                                                    	   	>> $RESULT_FILE 2>&1
		echo [1-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-1]Result : MANUAL                                                                                                  	>> $RESULT_FILE 2>&1
	else
		SSHCONFIG=`find /etc -type f -name "sshd_config"`
		if [ `grep -i "permitrootlogin" $SSHCONFIG | grep -v "setting" | grep -v "#" | grep -i "no" | wc -l` -eq 0 ]
			then
				echo "root 계정 원격 접속이 제한되지 않으므로 취약함"                                                              		   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"    																								   	>> $RESULT_FILE 2>&1
				grep -i "permitrootlogin" $SSHCONFIG | grep -v "setting" | grep -v "without"                                       	>> $RESULT_FILE 2>&1
				echo [1-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-1]Result : VULNERABLE                                                      						           	>> $RESULT_FILE 2>&1
				
			else
				echo "root 계정 원격 접속이 제한되므로 양호함"                                                                     		   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                       				   	>> $RESULT_FILE 2>&1
				grep -i "permitrootlogin" $SSHCONFIG | grep -v "setting" | grep -v "without"                                       	>> $RESULT_FILE 2>&1
				echo [1-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-1]Result : GOOD                                                                                            	>> $RESULT_FILE 2>&1
		fi
		
fi 
echo                                                                                                                             	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1                                                             


echo [U-2]패스워드 복잡성 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-2]패스워드 복잡성 설정                                                                                                     	   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [2-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ `find /etc -name "system-auth" | wc -l` -eq 0 ]
	then
		echo "system-auth 파일을 찾을 수 없음"                                                                                     	   	>> $RESULT_FILE 2>&1
		echo [2-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-2]Result : MANUAL                                                                                                  	>> $RESULT_FILE 2>&1
	else
		SYSAUTH=`find /etc -name "system-auth"`
		if [ `grep -i "password" $SYSAUTH | grep "requisite" | grep "lcredit" | grep "dcredit" | grep "ocredit" | wc -l` -eq 0 ]
			then
				echo "패스워드 복잡성 설정이 적용되어 있지 않으므로 취약함"                                                        		   	   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                               		   	>> $RESULT_FILE 2>&1
				grep -i "password" $SYSAUTH                                                                                        	>> $RESULT_FILE 2>&1
				echo [2-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-2]Result : VULNERABLE                                                                                      	>> $RESULT_FILE 2>&1
			else
				echo "패스워드 복잡성 설정이 적용되어 있으므로 양호함"                                                             			  	>> $RESULT_FILE 2>&1
				echo                                                                                                              	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				grep -i "password" $SYSAUTH                                                                                        	>> $RESULT_FILE 2>&1
				echo [2-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-2]Result : GOOD                                                                                            	>> $RESULT_FILE 2>&1
		fi
fi 
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-3]계정 잠금 임계값 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-3]계정 잠금 임계값 설정                                                                                                    		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [3-START]                                                                                                                     	>> $RESULT_FILE 2>&1
Var_3_1=`cat /etc/pam.d/system-auth | grep "pam_tally" | grep "deny" | wc -l`
Var_3_2=`cat /etc/pam.d/sshd | grep "pam_tally" | grep "deny" | wc -l`
if [ $Var_3_1 -eq 1 -a $Var_3_2 -eq 1 ]
	then
		echo "system-auth, sshd 파일에 임계값 설정이 적용되어 있으므로 양호함"                                                     				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo "1) /etc/pam.d/system-auth"                                                                                           	>> $RESULT_FILE 2>&1
		cat /etc/pam.d/system-auth | grep "pam_tally" | grep "deny"                                                                	>> $RESULT_FILE 2>&1
		echo "2) /etc/pam.d/sshd"                                                                                                  	>> $RESULT_FILE 2>&1
		cat /etc/pam.d/sshd| grep "pam_tally" | grep "deny"                                                                        	>> $RESULT_FILE 2>&1
		echo [3-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1			
		echo [U-3]Result : GOOD                                                                                                    	>> $RESULT_FILE 2>&1
elif [ $Var_3_1 -eq 1 -a $Var_3_2 -eq 0 ]
	then
		echo "system-auth 파일에 임계값 설정이 적용되어 있으나, sshd 파일에는 적용되어 있지 않으므로 취약함"                       						>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo "1) /etc/pam.d/system-auth"                                                                                           	>> $RESULT_FILE 2>&1 
		cat /etc/pam.d/system-auth | grep "pam_tally" | grep "deny"                                                                	>> $RESULT_FILE 2>&1
		echo [3-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1			
		echo [U-3]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
elif [ $Var_3_1 -eq 0 -a $Var_3_2 -eq 1 ]
	then
		echo "sshd 파일에 임계값 설정이 적용되어 있으나, system-auth 파일에는 적용되어 있지 않으므로 취약함"                       						>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo "1) /etc/pam.d/sshd"                                                                                                  	>> $RESULT_FILE 2>&1
		cat /etc/pam.d/sshd | grep "pam_tally" | grep "deny"                                                                       	>> $RESULT_FILE 2>&1
		echo [3-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1			
		echo [U-3]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
	else
		echo "/etc/pam.d/system-auth(sshd) 파일에 임계값 설정이 적용되어 있지 않으므로 취약함"                                    	 			>> $RESULT_FILE 2>&1
		echo [3-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1			
		echo [U-3]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-4]패스워드 파일 보호
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-4]패스워드 파일 보호                                                                                                       		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [4-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ `head -1 /etc/passwd | awk -F: '{print $2}' | egrep "^x" | wc -c` -eq 2 ]
	then
		echo "패스워드를 /etc/passwd 파일에 저장하지 않고 별도의 파일에 저장하므로 양호함"                                         					>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		head -1 /etc/passwd                                                                                                        	>> $RESULT_FILE 2>&1
		echo [4-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-4]Result : GOOD                                                                                                    	>> $RESULT_FILE 2>&1
	else
		echo "패스워드를 /etc/passwd 파일에 저장하므로 취약함"                                                                     			>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		head -1 /etc/passwd                                                                                                        	>> $RESULT_FILE 2>&1
		echo [4-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1	
		echo [U-4]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-5]root 이외의 UID가 '0' 금지
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-5]root 이외의 UID가 '0' 금지                                                                                               		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [5-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ `awk -F: '$3==0 {print $0}' /etc/passwd | grep -v 'root' | wc -l` -eq 0 ]
	then
		echo "root 이외의 UID가 '0'인 계정이 존재하지 않으므로 양호함"                                                             				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		awk -F: '$3==0 {print $0}' /etc/passwd                                                                                     	>> $RESULT_FILE 2>&1
		echo [5-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-5]Result : GOOD                                                                                                    	>> $RESULT_FILE 2>&1
	else
		echo "root 이외의 UID가 '0'인 계정이 존재하므로 취약함"                                                                   		 	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		awk -F: '$3==0 {print $0}' /etc/passwd                                                                                     	>> $RESULT_FILE 2>&1
		echo [5-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-5]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-6]root 계정 su 제한
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-6]root 계정 su 제한                                                                                                        	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [6-START]                                                                                                                     	>> $RESULT_FILE 2>&1
ls -lL `which su` > tmp_6_1.txt
if [ `grep "wheel.so" /etc/pam.d/su | grep -v "trust" | grep -v "#" | grep "use_uid" | wc -l` -eq 0 ]
	then
		if [ `cat tmp_6_1.txt | grep "^........--" | wc -l` -eq 0 ]
			then
				echo "su 명령 사용이 특정 그룹으로 제한되어 있지 않으므로 취약함"                                                  				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				echo "1) /etc/pam.d/su 설정"                                                                                       	>> $RESULT_FILE 2>&1
				grep "wheel.so" /etc/pam.d/su | grep -v "trust"                                                                    	>> $RESULT_FILE 2>&1
				echo "2) su 명령어 퍼미션"                                                                                         		>> $RESULT_FILE 2>&1
				cat tmp_6_1.txt                                                                                                    	>> $RESULT_FILE 2>&1
				echo [6-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-6]Result : VULNERABLE                                                                                      	>> $RESULT_FILE 2>&1
			else
				echo "su 명령 사용이 특정 그룹으로 제한되어 있으므로 양호함"                                                       				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				cat tmp_6_1.txt                                                                                                    	>> $RESULT_FILE 2>&1
				echo [6-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-6]Result : GOOD                                                                                            	>> $RESULT_FILE 2>&1
		fi
	else
		echo "su 명령 사용이 특정 그룹으로 제한되어 있으므로 양호함"                                                               				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		grep "wheel.so" /etc/pam.d/su | grep -v "trust"                                                                            	>> $RESULT_FILE 2>&1
		echo [6-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-6]Result : GOOD                                                                                                    	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_6_1.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-7]패스워드 최소 길이 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-7]패스워드 최소 길이 설정                                                                                                  		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [7-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ `find /etc -name "system-auth" | wc -l` -eq 0 ]
	then
		echo "system-auth 파일을 찾을 수 없음"                                                                                     		>> $RESULT_FILE 2>&1
		echo [7-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-7]Result : MANUAL                                                                                                  	>> $RESULT_FILE 2>&1
	else
		SYSAUTH=`find /etc -name "system-auth"`
		if [ `grep -i "password" /etc/pam.d/system-auth | grep "minlen" | wc -l` -eq 0 ]
			then
				echo "패스워드 최소 길이 설정이 적용되어 있지 않으므로 취약함"                                                     				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				grep -i "password" $SYSAUTH                                                                                        	>> $RESULT_FILE 2>&1
				echo [7-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-7]Result : VULNERABLE                                                                                      	>> $RESULT_FILE 2>&1
			else
				if [ `grep -i "password" /etc/pam.d/system-auth | awk -F "minlen=" '{print $2}' | awk '{print $1}'` -gt 7 ]
					then
						echo "패스워드 최소 길이 설정이 정책에 맞게 적용되어 있으므로 양호함"                                      					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						grep -i "password" $SYSAUTH                                                                                	>> $RESULT_FILE 2>&1
						echo [7-END]                                                                                               	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-7]Result : GOOD                                                                                    	>> $RESULT_FILE 2>&1
					else
						echo "패스워드 최소 길이 설정이 적용되어 있으나 정책에 맞지 않으므로 취약함"                               					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						grep -i "password" $SYSAUTH                                                                                	>> $RESULT_FILE 2>&1
						echo [7-END]                                                                                               	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-7]Result : VULNERABLE                                                                              	>> $RESULT_FILE 2>&1
				fi
		fi
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-8]패스워드 최대 사용 기간 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-8]패스워드 최대 사용 기간 설정                                                                                             		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [8-START]                                                                                                                     	>> $RESULT_FILE 2>&1
RE_8_1=1
RE_8_2=1
if [ `grep "PASS_MAX_DAYS" /etc/login.defs | grep -v "#" | wc -l` -eq 0 ]
	then
		RE_8_1=0
	else
		if [ `grep "PASS_MAX_DAYS" /etc/login.defs | grep -v "#" | awk '{print $2}'` -gt 90 ]
			then
				RE_8_1=0
		fi
fi
cat /etc/shadow | awk -F: '$2!="*" {print $0}' | awk -F: '$2!="!!" {print $1,":",$5}' > tmp_8_1.txt
for var in `cat tmp_8_1.txt | awk '{print $NF}'`
do
	if [ $var == ":" ]
		then
			RE_8_2=0
	elif [ $var -gt 90 ]
		then
			RE_8_2=0
		else
			true
	fi
done
if [ $RE_8_1 -eq 1 ]
	then
		if [ $RE_8_2 -eq 1 ]
			then
				echo "PASS_MAX_DAYS 값 및 각 계정에 적용된 패스워드 최대 사용기간이 정책에 맞게 적용되어 있으므로 양호함"          						>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				echo "1) PASS_MAX_DAYS 설정"                                                                                       	>> $RESULT_FILE 2>&1
				grep "PASS_MAX_DAYS" /etc/login.defs | grep -v "#"                                                                 	>> $RESULT_FILE 2>&1
				echo "2) 각 계정별 패스워드 최대 사용기간 설정"                                                                    			>> $RESULT_FILE 2>&1
				cat tmp_8_1.txt                                                                                                    	>> $RESULT_FILE 2>&1
				echo [8-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1					
				echo [U-8]Result : GOOD                                                                                            	>> $RESULT_FILE 2>&1
			else
				echo "PASS_MAX_DAYS 값은 기준에 맞게 설정되어 있으나, 각 계정에 적용된 패스워드 최대 사용기간이 정책에 맞지 
				      않는 계정이 존재함"                                                                                         	 	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				echo "1) PASS_MAX_DAYS 설정"                                                                                       	>> $RESULT_FILE 2>&1
				grep "PASS_MAX_DAYS" /etc/login.defs | grep -v "#"                                                                 	>> $RESULT_FILE 2>&1
				echo "2) 각 계정별 패스워드 최대 사용기간 설정"                                                                    			>> $RESULT_FILE 2>&1
				cat tmp_8_1.txt                                                                                                    	>> $RESULT_FILE 2>&1
				echo [8-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1					
				echo [U-8]Result : MANUAL                                                                                          	>> $RESULT_FILE 2>&1
		fi
	else
		echo "PASS_MAX_DAYS 값 및 각 계정에 적용된 패스워드 최대 사용기간이 정책에 맞지 않으므로 취약함"                           					>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo "1) PASS_MAX_DAYS 설정"                                                                                               	>> $RESULT_FILE 2>&1
		grep "PASS_MAX_DAYS" /etc/login.defs | grep -v "#"                                                                         	>> $RESULT_FILE 2>&1
		echo "2) 각 계정별 패스워드 최대 사용기간 설정"                                                                            			>> $RESULT_FILE 2>&1
		cat tmp_8_1.txt                                                                                                            	>> $RESULT_FILE 2>&1
		echo [8-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1					
		echo [U-8]Result : VULNERABLE                                                                                              	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_8_1.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-9]패스워드 최소 사용기간 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-9]패스워드 최소 사용기간 설정                                                                                              		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [9-START]                                                                                                                     	>> $RESULT_FILE 2>&1
if [ -f /etc/login.defs ]
	then
		if [ `grep "PASS_MIN_DAYS" /etc/login.defs | grep -v "#" | wc -l` -eq 0 ]
			then
				echo "패스워드 최소 사용 기간 설정이 적용되어 있지 않으므로 취약함"                                                					>> $RESULT_FILE 2>&1
				echo [9-END]                                                                                                       	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-9]Result : VULNERABLE                                                                                      	>> $RESULT_FILE 2>&1
			else
				if [ `grep "PASS_MIN_DAYS" /etc/login.defs | grep -v "#" | awk '{print $2}'` -eq 1 ]
					then
						echo "패스워드 최소 사용 기간 설정이 정책에 맞게 적용되어 있으므로 양호함"                                	 				>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						grep "PASS_MIN_DAYS" /etc/login.defs | grep -v "#"                                                         	>> $RESULT_FILE 2>&1
						echo [9-END]                                                                                               	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1	
						echo [U-9]Result : GOOD                                                                                    	>> $RESULT_FILE 2>&1
					else
						echo "패스워드 최소 사용 기간 설정이 적용되어 있으나 정책에 맞지 않으므로 취약함"                          					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						grep "PASS_MIN_DAYS" /etc/login.defs | grep -v "#"                                                         	>> $RESULT_FILE 2>&1
						echo [9-END]                                                                                               	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-9]Result : VULNERABLE                                                                              	>> $RESULT_FILE 2>&1
				fi
		fi
	else
		echo "/etc/login.defs 파일을 찾을 수 없음"                                                                                 		>> $RESULT_FILE 2>&1
		echo [9-END]                                                                                                               	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-9]Result : MANUAL                                                                                                  	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-10]불필요한 계정 제거
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-10]불필요한 계정 제거                                                                                                      		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [10-START]                                                                                                                    	>> $RESULT_FILE 2>&1
tshells="/bin/sh|/bin/bash|/bin/dash|/bin/tcsh|/bin/csh|/bin/mksh|/bin/ksh|/bin/zsh"
cat /etc/passwd | egrep "$tshells" | awk -F: '{print $1}' > tmp_10_1.txt
for i in `cat tmp_10_1.txt`; do lastlog -b 90 | grep "^$i "; done > tmp_10_2.txt
if [ `cat tmp_10_2.txt | wc -l` -eq 0 ]
	then
		echo "쉘이 부여된 계정 중 90일 이상 로그인하지 않은 계정이 존재하지 않으므로 양호함"                                       					>> $RESULT_FILE 2>&1
		echo [10-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-10]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "쉘이 부여된 계정 중 90일 이상 로그인하지 않은 계정이 존재하므로 취약함"                                              					>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		cat tmp_10_2.txt                                                                                                           	>> $RESULT_FILE 2>&1
		echo [10-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-10]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_10_1.txt
rm -rf tmp_10_2.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-11]관리자 그룹에 최소한의 계정 포함
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-11]관리자 그룹에 최소한의 계정 포함                                                                                        			>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [11-START]                                                                                                                    	>> $RESULT_FILE 2>&1
grep "^root" /etc/group | awk -F ":" '{print $4}' | sed s/,/\\n/g | grep -v "^root$" | wc -w > tmp_11.txt
if [ `cat tmp_11.txt` -eq 0 ]
	then
		echo "관리자 그룹에 root 이외의 계정이 존재하지 않으므로 양호함"                                                           				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		grep "^root" /etc/group                                                                                                    	>> $RESULT_FILE 2>&1
		echo [11-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-11]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "관리자 그룹에 root 이외의 계정이 존재함"                                                                             			>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		grep "^root" /etc/group                                                                                                    	>> $RESULT_FILE 2>&1
		echo [11-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-11]Result : MANUAL                                                                                                 	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_11.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
 

echo [U-12]계정이 존재하지 않는 GID 금지
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-12]계정이 존재하지 않는 GID 금지                                                                                           		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [12-START]                                                                                                                    	>> $RESULT_FILE 2>&1
awk -F : '$4 == null {print $0}' /etc/group | awk -F : '$3 >= 500 {print $0}' > tmp_group.txt
awk -F : '{print $4}' /etc/passwd > tmp_passwd.txt
for TGID in `cat tmp_passwd.txt`
	do
		grep -v ":$TGID:" tmp_group.txt > tmp_deh.txt
		cat tmp_deh.txt > tmp_group.txt
done
if [ `cat tmp_group.txt | wc -w` -eq 0 ]
	then
		echo "계정이 존재하지 않는 500 이상 GID가 존재하지 않으므로 양호함"                                                        				>> $RESULT_FILE 2>&1
		echo [12-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-12]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "계정이 존재하지 않는 500 이상 GID가 존재하므로 취약함"                                                               				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1 
		cat tmp_group.txt                                                                                                          	>> $RESULT_FILE 2>&1 
		echo [12-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-12]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_group.txt
rm -rf tmp_passwd.txt
rm -rf tmp_deh.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-13]동일한 UID 금지
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-13]동일한 UID 금지                                                                                                         	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [13-START]                                                                                                                    	>> $RESULT_FILE 2>&1
awk -F : '{print $3}' /etc/passwd > tmp_passwd.txt
if [ `cat tmp_passwd.txt | sort | uniq -d | wc -l` -eq 0 ]
	then
		echo "중복된 UID가 존재하지 않으므로 양호함"                                                                               			>> $RESULT_FILE 2>&1
		echo [13-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-13]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "중복된 UID가 존재하므로 취약함"                                                                                      		>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1 
		DUID=`cat tmp_passwd.txt | sort | uniq -d`
		grep "x:$DUID:" /etc/passwd                                                                                                	>> $RESULT_FILE 2>&1
		echo [13-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-13]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_passwd.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-14]사용자 shell 점검
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-14]사용자 shell 점검                                                                                                       	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [14-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `cat /etc/passwd | egrep "^daemon|^bin|^sys|^adm|^listen|^nobody|^nobody4|^noaccess|^diag|^listen|^operator|^games|^gopher" | grep -v "admin" |  awk -F: '{print $7}'| egrep -v 'false|nologin|null|halt|sync|shutdown' | wc -l` -eq 0 ]
	then
		echo "점검 대상 시스템 계정에 쉘이 부여되지 않으므로 양호함"                                                               				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		cat /etc/passwd | egrep "^daemon|^bin|^sys|^adm|^listen|^nobody|^nobody4|^noaccess|^diag|^listen|^operator|^games|^gopher" 	>> $RESULT_FILE 2>&1
		echo [14-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-14]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "점검 대상 시스템 계정에 쉘이 부여되므로 취약함"                                                                      				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		cat /etc/passwd | egrep "^daemon|^bin|^sys|^adm|^listen|^nobody|^nobody4|^noaccess|^diag|^listen|^operator|^games|^gopher" 	>> $RESULT_FILE 2>&1
		echo [14-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-14]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-15]Session Timeout 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-15]Session Timeout 설정                                                                                                    	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [15-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `echo $TMOUT | wc -w` -eq 0 ]
	then
		echo "세션 타임아웃이 설정되지 않았으므로 취약함"                                                                          				>> $RESULT_FILE 2>&1
		echo [15-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-15]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
	else
		if [ `echo $TMOUT` -gt 600 ]
			then
				echo "세션 타임아웃이 설정되어 있으나 정책에 맞지 않으므로 취약함"                                                					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				echo "TMOUT : `echo $TMOUT`"                                                                                       	>> $RESULT_FILE 2>&1
				echo [15-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-15]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
			else
				echo "세션 타임아웃이 기준에 맞게 설정되었으므로 양호함"                                                           				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				echo "TMOUT : `echo $TMOUT`"                                                                                       	>> $RESULT_FILE 2>&1
				echo [15-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-15]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
		fi
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-16]root 홈, 패스 디렉터리 권한 및 패스 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-16]root 홈, 패스 디렉터리 권한 및 패스 설정                                                                                			>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [16-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `echo $PATH | grep "\.:" | wc -l` -eq 0 ]
	then
		echo "PATH 환경변수에 '.'이 맨 앞 또는 중간에 위치하지 않으므로 양호함"                                                    				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo $PATH                                                                                                                 	>> $RESULT_FILE 2>&1
		echo [16-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-16]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "PATH 환경변수에 '.'이 맨 앞 또는 중간에 위치하므로 취약함"                                                           				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		echo $PATH                                                                                                                 	>> $RESULT_FILE 2>&1
		echo [16-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-16]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-17]파일 및 디렉터리 소유자 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-17]파일 및 디렉터리 소유자 설정                                                                                            		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [17-START]                                                                                                                    	>> $RESULT_FILE 2>&1
ls -lL /home | awk '{print $3}' | grep "^[0-9]" > tmp_17_1.txt
for i in `cat tmp_17_1.txt`; do ls -lLd /home/* | grep -w $i >> tmp_17_2.txt; done
if [ -f tmp_17_2.txt ]
	then
		echo "/home 디렉토리에 소유자가 존재하지 않는 파일이 존재하므로 취약함"                                                    					>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		cat tmp_17_2.txt                                                                                                           	>> $RESULT_FILE 2>&1
		echo [17-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-17]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1		
	else
		echo "/home 디렉토리에 소유자가 존재하지 않는 파일이 존재하지 않으므로 양호함"                                             					>> $RESULT_FILE 2>&1
		echo [17-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-17]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_17_1.txt
rm -rf tmp_17_2.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-18]/etc/passwd 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-18]/etc/passwd 파일 소유자 및 권한 설정                                                                                    		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [18-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `ls -alL /etc/passwd | grep "^...-.--.--" | awk '$3=="root"' | wc -l` -eq 1 ]
  then
	echo "/etc/passwd 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되었으므로 양호함"                                     	 				>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
	echo "[현황]"                                                                                                                  	>> $RESULT_FILE 2>&1
	ls -alL /etc/passwd                                                                                                            	>> $RESULT_FILE 2>&1
	echo [18-END]                                                                                                                  	>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
    echo [U-18]Result : GOOD                                                                                                       	>> $RESULT_FILE 2>&1
 else
	echo "/etc/passwd 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되지 않았으므로 취약함"                                 					>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
	echo "[현황]"                                                                                                                  	>> $RESULT_FILE 2>&1
	ls -alL /etc/passwd                                                                                                            	>> $RESULT_FILE 2>&1
	echo [18-END]                                                                                                                  	>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
    echo [U-18]Result : VULNERABLE                                                                                                 	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-19]/etc/shadow 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-19]/etc/shadow 파일 소유자 및 권한 설정                                                                                    		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [19-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `ls -alL /etc/shadow | grep "^....------" | awk '$3=="root"' | wc -l` -eq 1 ]
  then
	echo "/etc/shadow 파일의 소유자(root) 및 퍼미션(400/600)이 기준에 맞게 설정되었으므로 양호함"                                  					>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
	echo "[현황]"                                                                                                                  	>> $RESULT_FILE 2>&1
	ls -alL /etc/shadow                                                                                                            	>> $RESULT_FILE 2>&1
	echo [19-END]                                                                                                                  	>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
    echo [U-19]Result : GOOD                                                                                                       	>> $RESULT_FILE 2>&1
 else
	echo "/etc/shadow 파일의 소유자(root) 및 퍼미션(400/600)이 기준에 맞게 설정되지 않았으므로 취약함"                             					>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
	echo "[현황]"                                                                                                                  	>> $RESULT_FILE 2>&1
	ls -alL /etc/shadow                                                                                                            	>> $RESULT_FILE 2>&1
	echo [19-END]                                                                                                                  	>> $RESULT_FILE 2>&1
	echo                                                                                                                           	>> $RESULT_FILE 2>&1
    echo [U-19]Result : VULNERABLE                                                                                                 	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-20]/etc/hosts 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-20]/etc/hosts 파일 소유자 및 권한 설정                                                                                     		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [20-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/hosts ]
	then
		if [ `ls -alL /etc/hosts | grep "^...-------" | awk '$3=="root"' | wc -l` -eq 1 ]
			then
				echo "/etc/hosts 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되었으므로 양호함"                           					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                              		   	>> $RESULT_FILE 2>&1
				ls -alL /etc/hosts                                                                                                 	>> $RESULT_FILE 2>&1
				echo [20-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-20]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "/etc/hosts 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되지 않았으므로 취약함"                      					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/hosts                                                                                                 	>> $RESULT_FILE 2>&1
				echo [20-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-20]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
	else
		echo "/etc/hosts 파일을 찾을 수 없음"                                                                                      		>> $RESULT_FILE 2>&1
		echo [20-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-20]Result : N/A                                                                                                    	>> $RESULT_FILE 2>&1 
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo "[U-21]/etc/(x)inetd.conf 파일 소유자 및 권한 설정"
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo "[U-21]/etc/(x)inetd.conf 파일 소유자 및 권한 설정"                                                                           		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [21-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/xinetd.conf ]
	then
		if [ `ls -alL /etc/xinetd.conf | grep "^....------" | awk '$3=="root"' | wc -l` -eq 1 ]
			then
				echo "/etc/xinetd.conf 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되었으므로 양호함"                     					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/xinetd.conf                                                                                           	>> $RESULT_FILE 2>&1
				echo [21-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-21]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "/etc/xinetd.conf 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되지 않았으므로 취약함"                					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/xinetd.conf                                                                                           	>> $RESULT_FILE 2>&1
				echo [21-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-21]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
	else
		if [ -f /etc/inetd.conf ]
			then
				if [ `ls -alL /etc/inetd.conf | grep "^....------" | awk '$3=="root"' | wc -l` -eq 1 ]
					then
						echo "/etc/inetd.conf 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되었으므로 양호함"              					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						ls -alL /etc/inetd.conf                                                                                    	>> $RESULT_FILE 2>&1
						echo [21-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-21]Result : GOOD                                                                                   	>> $RESULT_FILE 2>&1
					else
						echo "/etc/inetd.conf 파일의 소유자(root) 및 퍼미션(600)이 기준에 맞게 설정되지 않았으므로 취약함"         					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						ls -alL /etc/inetd.conf                                                                                    	>> $RESULT_FILE 2>&1
						echo [21-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-21]Result : VULNERABLE                                                                             	>> $RESULT_FILE 2>&1
				fi				
			else
				echo "/etc/(x)inetd.conf 파일을 찾을 수 없으므로 양호함"                                                           			>> $RESULT_FILE 2>&1
				echo [21-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-21]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1 
		fi
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-22]/etc/syslog.conf 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-22]/etc/syslog.conf 파일 소유자 및 권한 설정                                                                               		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [22-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/syslog.conf ]
	then
		if [ `ls -alL /etc/syslog.conf | grep "^...-.--.--" | awk '$3=="root"' | wc -l` -eq 1 ]
			then
				echo "/etc/syslog.conf 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되었으므로 양호함"                     					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ls -alL /etc/syslog.conf                                                                                          	>> $RESULT_FILE 2>&1
				echo [22-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-22]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "/etc/syslog.conf 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되지 않았으므로 취약함"                					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/syslog.conf                                                                                           	>> $RESULT_FILE 2>&1
				echo [22-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-22]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
	else
		if [ -f /etc/rsyslog.conf ]
			then
				if [ `ls -alL /etc/rsyslog.conf | grep "^...-.--.--" | awk '$3=="root"' | wc -l` -eq 1 ]
					then
						echo "/etc/rsyslog.conf 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되었으므로 양호함"            					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						ls -alL /etc/rsyslog.conf                                                                                  	>> $RESULT_FILE 2>&1
						echo [22-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1	
						echo [U-22]Result : GOOD                                                                                   	>> $RESULT_FILE 2>&1
					else
						echo "/etc/rsyslog.conf 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되지 않았으므로 취약함"       					>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						ls -alL /etc/rsyslog.conf                                                                                  	>> $RESULT_FILE 2>&1
						echo [22-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-22]Result : VULNERABLE                                                                             	>> $RESULT_FILE 2>&1
				fi
			else
				echo "/etc/syslog.conf 파일을 찾을 수 없음"                                                                        		>> $RESULT_FILE 2>&1
				echo [22-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-22]Result : N/A                                                                                            	>> $RESULT_FILE 2>&1 
		fi
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-23]/etc/services 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-23]/etc/services 파일 소유자 및 권한 설정                                                                                  		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [23-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/services ]
	then
		if [ `ls -alL /etc/services | grep "^...-.--.--" | awk '$3=="root"' | wc -l` -eq 1 ]
			then
				echo "/etc/services 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되었으므로 양호함"                        					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/services                                                                                              	>> $RESULT_FILE 2>&1
				echo [23-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-23]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "/etc/services 파일의 소유자(root) 및 퍼미션(644)이 기준에 맞게 설정되지 않았으므로 취약함"                   					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -alL /etc/services                                                                                              	>> $RESULT_FILE 2>&1
				echo [23-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-23]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
	else
		echo "/etc/services 파일이 없음"                                                                                           	>> $RESULT_FILE 2>&1
		echo [23-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-23]Result : N/A                                                                                                    	>> $RESULT_FILE 2>&1 
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-24]SUID, SGID, Sticky bit 설정 파일 점검
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-24]SUID, SGID, Sticky bit 설정 파일 점검                                                                                   		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [24-START]                                                                                                                    	>> $RESULT_FILE 2>&1
FILES="/sbin/dump /usr/bin/lpq-lpd /usr/bin/newgrp /sbin/restore /usr/bin/lpr /usr/sbin/lpc /sbin/unix_chkpwd /usr/bin/lpr-lpd /usr/sbin/lpc-lpd /usr/bin/at /usr/bin/lprm /usr/sbin/traceroute /usr/bin/lpq /usr/bin/lprm-lpd"
for check_file in $FILES
	do
    if [ -f $check_file ]
		then
			if [ -g $check_file -o -u $check_file ]
				then
					echo `ls -alL $check_file` >> tmp_24.txt
				else
				:
			fi
		else
		:
    fi
done
if [ -f tmp_24.txt ]
	then
		echo "점검 파일 중 SUID, SGID가 설정된 파일이 존재하므로 취약함"                                                           				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		cat tmp_24.txt                                                                                                             	>> $RESULT_FILE 2>&1
		echo [24-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-24]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
	else
		echo "점검 파일 중 SUID, SGID가 설정된 파일이 존재하지 않으므로 양호함"                                                    				>> $RESULT_FILE 2>&1
		echo [24-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-24]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_24.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-25]사용자, 시스템 시작파일 및 환경파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-25]사용자, 시스템 시작파일 및 환경파일 소유자 및 권한 설정                                                                 				>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [25-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/profile ]
	then
		if [ `ls -alL /etc/profile | grep "^.....-..-." | awk '$3=="root"' | wc -l` -eq 1 ]
			then
				echo "/etc/profile 파일의 소유자(root) 및 퍼미션(g-w,o-w)이 기준에 맞게 설정되었으므로 양호함"                     					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -al /etc/profile                                                                                                	>> $RESULT_FILE 2>&1
				echo [25-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-25]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "/etc/profile 파일의 소유자(root) 및 퍼미션(g-w,o-w)이 기준에 맞게 설정되지 않았으므로 취약함"                					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -al /etc/profile                                                                                                	>> $RESULT_FILE 2>&1
				echo [25-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-25]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
	else
		echo "/etc/profile 파일이 없음"                                                                                            	>> $RESULT_FILE 2>&1
		echo [25-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-25]Result : N/A                                                                                                    	>> $RESULT_FILE 2>&1 
fi	
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-26]world writable 파일 점검
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-26]world writable 파일 점검                                                                                                  	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [26-START]                                                                                                                    	>> $RESULT_FILE 2>&1
find /etc -perm -2 -a -not -type l -ls > tmp_26.txt
if [ `cat tmp_26.txt | wc -l` -eq 0 ]
	then
		echo "/etc 디렉토리 하위에 Others에 쓰기 권한이 부여된 파일이 존재하지 않으므로 양호함"                                   			 		>> $RESULT_FILE 2>&1
		echo [26-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-26]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "/etc 디렉토리 하위에 Others에 쓰기 권한이 부여된 파일이 존재하므로 취약함"                                           					>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"																												>> $RESULT_FILE 2>&1
		cat tmp_26.txt                                                                                                             	>> $RESULT_FILE 2>&1
		echo [26-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-26]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_26.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
    

echo [U-27]/dev에 존재하지 않는 device 파일 점검
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-27]/dev에 존재하지 않는 device 파일 점검                                                                                  		   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [27-START]                                                                                                                    	>> $RESULT_FILE 2>&1
find /dev -type f -exec ls -lL {} \; | grep -Ev "MAKEDEV|\.mount|\.udev|/dev/shm" > tmp_27.txt
if [ `cat tmp_27.txt | wc -l` -eq 0 ]
	then
		echo "/dev 디렉토리에 major, minor nubmer를 가지지 않는 파일이 존재하지 않으므로 양호함"                                   				>> $RESULT_FILE 2>&1
		echo [27-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-27]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "/dev 디렉토리에 major, minor nubmer를 가지지 않는 파일이 존재하므로 취약함"                                          				>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"																												>> $RESULT_FILE 2>&1
		cat tmp_27.txt                                                                                                             	>> $RESULT_FILE 2>&1
		echo [27-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-27]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
rm -rf tmp_27.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-28]$HOME/.rhosts, hosts.equiv 사용 금지
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-28]$HOME/.rhosts, hosts.equiv 사용 금지                                                                                    	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [28-START]                                                                                                                    	>> $RESULT_FILE 2>&1
ls -lL /home/ | grep -v "+found" | sed -n '2,$p' | awk '{print $9}' > tmp_28_1.txt
for i in `cat tmp_28_1.txt`; do ls -al /home/$i/.rhosts; done 2>/dev/null > tmp_28_2.txt
if [ -f /etc/hosts.equiv ]; then ls -lL /etc/hosts.equiv >> tmp_28_2.txt; else true; fi 
if [ `cat tmp_28_2.txt | wc -l` -eq 0 ]
	then
		echo ".rhosts, hosts.equiv 파일이 존재하지 않으므로 양호함"                                                                			>> $RESULT_FILE 2>&1
		echo [28-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-28]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		if [ `cat tmp_28_2.txt | wc -l` -eq `cat tmp_28_2.txt | grep "^....------" | wc -l` ]
			then
				for i in `cat tmp_28_2.txt | awk '{print $9}'`; do cat $i; done >> tmp_28_3.txt
				if [ `cat tmp_28_3.txt | grep "\+" | wc -l` -eq 0 ] 
					then
						echo ".rhosts, hosts.equiv 파일의 퍼미션 및 설정이 기준에 맞게 적용되었으므로 양호함"                      				>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						for i in `cat tmp_28_2.txt | awk '{print $9}'`; do ls -lL $i                                               	>> $RESULT_FILE 2>&1 && cat $i          >> $RESULT_FILE 2>&1; done
						echo [28-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-28]Result : GOOD                                                                                   	>> $RESULT_FILE 2>&1
					else
						echo ".rhosts, hosts.equiv 파일의 설정이 기준에 맞지 않았으므로 취약함"                                    				>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						for i in `cat tmp_28_2.txt | awk '{print $9}'`; do ls -lL $i                                               	>> $RESULT_FILE 2>&1 && cat $i          >> $RESULT_FILE 2>&1; done
						echo [28-END]                                                                                              	>> $RESULT_FILE 2>&1
						echo                                                                                                       	>> $RESULT_FILE 2>&1
						echo [U-28]Result : VULNERABLE                                                                             	>> $RESULT_FILE 2>&1
				fi
			else
				echo ".rhosts, hosts.equiv 파일의 퍼미션이 기준에 맞지 않았으므로 취약함"                                          				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				for i in `cat tmp_28_2.txt | awk '{print $9}'`; do ls -lL $i                                                       	>> $RESULT_FILE 2>&1 && cat $i          >> $RESULT_FILE 2>&1; done
				echo [28-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-28]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_28_1.txt
rm -rf tmp_28_2.txt				
rm -rf tmp_28_3.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
 

echo [U-29]접속 IP 및 포트 제한
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-29]접속 IP 및 포트 제한                                                                                                    		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [29-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/hosts.deny ]
	then
		if [ `cat /etc/hosts.deny | grep -v "#" | grep -iE "(sshd|all) *: *all$" | wc -l` -eq 0 ]
			then
				echo "/etc/hosts.deny 파일에 Deny 설정이 존재하지 않으므로 취약함"                                                 			>> $RESULT_FILE 2>&1
				echo [29-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-29]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
			else
				echo "/etc/hosts.deny 파일에 Deny 설정이 적용되었으므로 양호함"                                                    			>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -lL /etc/hosts.deny                                                                                             	>> $RESULT_FILE 2>&1
				cat /etc/hosts.deny | grep -v "#" | grep -v "^$"                                                                   	>> $RESULT_FILE 2>&1
				ls -lL /etc/hosts.allow                                                                                            	>> $RESULT_FILE 2>&1
				cat /etc/hosts.allow | grep -v "#" | grep -v "^$"                                                                  	>> $RESULT_FILE 2>&1
				echo [29-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                              	>> $RESULT_FILE 2>&1
				echo [U-29]Result : GOOD                                                                                          	>> $RESULT_FILE 2>&1
		fi
	else
		echo "/etc/hosts.deny 파일이 존재하지 않음"                                                                                		>> $RESULT_FILE 2>&1
		echo [29-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-29]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1
 

echo [U-30]hosts.lpd 파일 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-30]hosts.lpd 파일 소유자 및 권한 설정                                                                                      		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [30-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ -f /etc/hosts.lpd ]
	then
		if [ `ls -lL /etc/hosts.lpd | grep "^........-." | awk '$3=="root"' | wc -l` -eq 0 ]
			then
				echo "/etc/hosts.lpd 파일의 소유자(root) 및 퍼미션(o-w)이 기준에 맞지 않으므로 취약함"                             				>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -lL /etc/hosts.lpd                                                                                              	>> $RESULT_FILE 2>&1
				echo [30-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-30]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
			else
				echo "/etc/hosts.lpd 파일의 소유자(root) 및 퍼미션(o-w)이 기준에 맞게 설정되어 있으므로 양호함"                    					>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				ls -lL /etc/hosts.lpd                                                                                              	>> $RESULT_FILE 2>&1
				echo [30-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-30]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
		fi
	else
		echo "/etc/hosts.lpd 파일이 존재하지 않음"                                                                                 		>> $RESULT_FILE 2>&1
		echo [30-END]                                                                                                             	>> $RESULT_FILE 2>&1
		echo                                                                                                                      	>> $RESULT_FILE 2>&1
		echo [U-30]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
fi	
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-31]NIS 서비스 비활성화
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-31]NIS 서비스 비활성화                                                                                                     		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [31-START]                                                                                                                    	>> $RESULT_FILE 2>&1
NISSERVICE="ypserv|ypbind|ypxfrd|rpc.yppasswdd|rpc.ypupdated"
if [ `ps -ef | egrep $NISSERVICE | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "NIS, NIS+ 서비스가 실행중이지 않으므로 양호함"                                                                       			>> $RESULT_FILE 2>&1
		echo [31-END]                                                                                                             	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-31]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		echo "NIS, NIS+ 서비스가 실행중이므로 취약함"                                                                              			>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                              	>> $RESULT_FILE 2>&1
		ps -ef | egrep $SERVICE | grep -v "grep"                                                                                   	>> $RESULT_FILE 2>&1
		echo [31-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-31]Result : VULNERABLE                                                                                             	>> $RESULT_FILE 2>&1
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-32]UMASK 설정 관리
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-32]UMASK 설정 관리																												>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [32-START]                                                                                                                    	>> $RESULT_FILE 2>&1
if [ `umask` -eq 0022 ]
	then
		echo "UMASK 값이 기준에 맞게 설정되었으므로 양호함"                                                                        		   	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1		
		echo "UMASK : `umask`"                                                                                                     	>> $RESULT_FILE 2>&1
		echo [32-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-32]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		if [ `umask` -eq 0027 ]
			then
				echo "UMASK 값이 기준에 맞게 설정되었으므로 양호함"                                                                		   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1		
				echo "UMASK : `umask`"                                                                                             	>> $RESULT_FILE 2>&1
				echo [32-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-32]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "UMASK 값이 기준에 맞게 설정되지 않았으므로 취약함"                                                           			   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1		
				echo "UMASK : `umask`"                                                                                             	>> $RESULT_FILE 2>&1
				echo [32-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-32]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
fi
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-33]홈디렉토리 소유자 및 권한 설정
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-33]홈디렉토리 소유자 및 권한 설정                                                                                          		   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [33-START]                                                                                                                    	>> $RESULT_FILE 2>&1
ls -lLd /home/* | grep "^d" > tmp_33_1.txt
cat tmp_33_1.txt | grep -v "^........w." > tmp_33_2.txt
if [ `cat tmp_33_1.txt | wc -l` -eq 0 ]
	then
		echo "사용자 홈디렉토리가 존재하지 않으므로 양호함"                                                                        			   	>> $RESULT_FILE 2>&1
		echo [33-END]                                                                                                              	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo [U-33]Result : GOOD                                                                                                   	>> $RESULT_FILE 2>&1
	else
		if [ `diff tmp_33_1.txt tmp_33_2.txt | wc -l` -eq 0 ]
			then
				echo "사용자 홈디렉토리의 퍼미션(o-w)이 기준에 맞게 설정되어 있으므로 양호함"                                      				   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_33_1.txt                                                                                                   	>> $RESULT_FILE 2>&1
				echo [33-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-33]Result : GOOD                                                                                           	>> $RESULT_FILE 2>&1
			else
				echo "사용자 홈디렉토리의 퍼미션(o-w)이 기준에 맞게 설정되지 않았으므로 취약함"                                    				   	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_33_1.txt | grep "^........w."                                                                             	>> $RESULT_FILE 2>&1
				echo [33-END]                                                                                                      	>> $RESULT_FILE 2>&1
				echo                                                                                                               	>> $RESULT_FILE 2>&1
				echo [U-33]Result : VULNERABLE                                                                                     	>> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_33_1.txt
rm -rf tmp_33_2.txt
echo                                                                                                                               	>> $RESULT_FILE 2>&1
echo                                                                                                                               	>> $RESULT_FILE 2>&1


echo [U-34]홈디렉토리로 지정한 디렉토리의 존재 관리
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [U-34]홈디렉토리로 지정한 디렉토리의 존재 관리                                                                                		   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                	>> $RESULT_FILE 2>&1
echo [34-START]                                                                                                                    	>> $RESULT_FILE 2>&1
cat /etc/passwd | awk -F: '$3>=500 {print $0}' > tmp_34_1.txt
cat tmp_34_1.txt | awk -F: '{print $6}' > tmp_34_2.txt
touch tmp_34_3.txt
for i in `cat tmp_34_2.txt`
	do
		if [ -d $i ]; then echo $i >> tmp_34_3.txt; else true; fi
done
if [ `diff tmp_34_2.txt tmp_34_3.txt | wc -l` -eq 0 ]
	then
		echo "홈디렉토리가 존재하지 않는 계정이 존재하지 않으므로 양호함"                                                           				>> $RESULT_FILE 2>&1
		echo [34-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-34]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "홈디렉토리가 존재하지 않는 계정이 존재하므로 취약함"                                                                  			   	>> $RESULT_FILE 2>&1
		echo                                                                                                                       	>> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1
		diff tmp_34_2.txt tmp_34_3.txt | grep "<" | awk '{print $2}' > tmp_34_4.txt
		for i in `cat tmp_34_4.txt`
			do
				cat /etc/passwd | grep $i | awk -F: '{print "계정  "$1"  의 홈디렉토리  "$6"  가 존재하지 않음"}'                   			>> $RESULT_FILE 2>&1
		done
		echo [34-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-34]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
rm -rf tmp_34_1.txt
rm -rf tmp_34_2.txt
rm -rf tmp_34_3.txt
rm -rf tmp_34_4.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-35]숨겨진 파일 및 디렉토리 검색 및 제거
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-35]숨겨진 파일 및 디렉토리 검색 및 제거                                                                                     			>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [35-START]                                                                                                                     >> $RESULT_FILE 2>&1
Var_35_1="font-unix|ICE-unix|ifstat|Test-unix|X11-unix|XIM-unix|esd-"
find /tmp/ | grep "/\." | grep -Ev $Var_35_1 > tmp_35_1.txt
if [ `cat tmp_35_1.txt | wc -l` -eq 0 ]
	then
		echo "/tmp 디렉토리에 숨김 속성 파일이 존재하지 않으므로 양호함"                                                            				>> $RESULT_FILE 2>&1
		echo [35-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-35]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "/tmp 디렉토리에 숨김 속성 파일이 존재함"                                                                              			>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1
		cat tmp_35_1.txt                                                                                                            >> $RESULT_FILE 2>&1
		echo [35-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-35]Result : MANUAL                                                                                                  >> $RESULT_FILE 2>&1
fi
rm -rf tmp_35_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-36]Finger 서비스 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-36]Finger 서비스 비활성화                                                                                                  		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [36-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep -i "finger" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "Finger 서비스가 실행중이지 않으므로 양호함"                                                                           			>> $RESULT_FILE 2>&1
		echo [36-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-36]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "Finger 서비스가 실행중이므로 취약함"                                                                                  		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1
		ps -ef | grep -i "finger" | grep -v "grep"                                                                                  >> $RESULT_FILE 2>&1
		echo [36-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-36]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-37]Anonymous FTP 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-37]Anonymous FTP 비활성화                                                                                                   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [37-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep -i "ftpd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "FTP 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [37-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-37]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		find /etc -name "vsftpd.conf" -exec cat {} \; > tmp_37_1.txt
		if [ `cat tmp_37_1.txt | wc -l` -eq 0 ]
			then
				if [ `cat /etc/passwd | egrep -w "ftp|anonymous" | wc -l` -eq 0 ]
					then
						echo "FTP 서비스가 실행중이며, ftp 또는 anonymous 계정이 존재하지 않으므로 양호함 "                         				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                               	>> $RESULT_FILE 2>&1
						netstat -anp | grep ":21 " | grep -i "LISTEN"                                                               >> $RESULT_FILE 2>&1
						echo [37-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-37]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "FTP 서비스가 실행중이며, ftp 또는 anonymous 계정이 존재하므로 취약함"                                 				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						netstat -anp | grep ":21 " | grep -i "LISTEN"                                                               >> $RESULT_FILE 2>&1
						cat /etc/passwd | egrep -w "ftp|anonymous"                                                                  >> $RESULT_FILE 2>&1
						echo [37-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-37]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
			else
				if [ `cat tmp_37_1.txt | grep "anonymous_enable" | grep -v "#" | grep -i -v "no$" | wc -l` -eq 0 ]
					then
						echo "FTP 서비스가 실행중이며, Anonymous 접속이 차단되었으므로 양호함"                                      				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                              	>> $RESULT_FILE 2>&1
						netstat -anp | grep ":21 " | grep -i "LISTEN"                                                               >> $RESULT_FILE 2>&1
						cat tmp_37_1.txt | grep "anonymous_enable"                                                                  >> $RESULT_FILE 2>&1
						echo [37-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-37]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "FTP 서비스가 실행중이며, Anonymous 접속이 허용되므로 취약함"                                          			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                               	>> $RESULT_FILE 2>&1
						netstat -anp | grep ":21 " | grep -i "LISTEN"                                                               >> $RESULT_FILE 2>&1
						cat tmp_37_1.txt | grep "anonymous_enable"                                                                  >> $RESULT_FILE 2>&1
						echo [37-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-37]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
		fi	
fi
rm -rf tmp_37_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-38]r 계열 서비스 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-38]r 계열 서비스 비활성화                                                                                                   		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [38-START]                                                                                                                     >> $RESULT_FILE 2>&1
SERVICE_INETD="rsh|rlogin|rexec"
chkconfig --list | egrep $SERVICE_INETD > tmp_38_1.txt
if [ `cat tmp_38_1.txt | wc -l` -eq 0 ]
	then
		echo "r 계열 서비스가 설치되어 있지 않으므로 양호함"                                                                        			>> $RESULT_FILE 2>&1
		echo [38-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-38]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `cat tmp_38_1.txt | egrep "3:on|:.on|3:활성" | wc -l` -eq 0 ]
			then
				echo "r 계열 서비스가 설치되어 있으나 실행중이지 않으므로 양호함"                                                   				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_38_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [38-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-38]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				echo "r 계열 서비스가 실행중이므로 취약함"                                                                          			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_38_1.txt | egrep "3:on|:.on|3:활성"                                                                         	>> $RESULT_FILE 2>&1
				echo [38-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-38]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_38_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-39]cron 파일 소유자 및 권한 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-39]cron 파일 소유자 및 권한 설정                                                                                            		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [39-START]                                                                                                                     >> $RESULT_FILE 2>&1
ls -l /etc/* | egrep "cron.deny|cron.allow" > tmp_39_1.txt
if [ `cat tmp_39_1.txt | wc -l` -eq 0 ]
	then
		echo "cron.deny, cron.allow 파일을 찾을 수 없음"                                                                            		>> $RESULT_FILE 2>&1
		echo [39-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-39]Result : N/A                                                                                                     >> $RESULT_FILE 2>&1
	else
		cat tmp_39_1.txt | grep "^.....-----" > tmp_39_2.txt
		if [ `diff tmp_39_1.txt tmp_39_2.txt | wc -l` -eq 0 ]
			then
				echo "cron 파일의 소유자(root) 및 퍼미션(640)이 기준에 맞게 적용되어 있으므로 양호함"                               				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_39_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [39-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-39]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				echo "cron 파일의 소유자(root) 및 퍼미션(640)이 기준에 맞게 적용되어 있지 않으므로 취약함"                          					>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_39_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [39-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-39]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
		fi
fi	
rm -rf tmp_39_1.txt
rm -rf tmp_39_2.txt	
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-40]DoS 공격에 취약한 서비스 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-40]DoS 공격에 취약한 서비스 비활성화                                                                                        		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [40-START]                                                                                                                     >> $RESULT_FILE 2>&1
SERVICE_INETD="echo|discard|daytime|chargen"
chkconfig --list | egrep $SERVICE_INETD > tmp_40_1.txt
if [ `cat tmp_40_1.txt | wc -l` -eq 0 ]
	then
		echo "DoS 공격에 취약한 서비스가 설치되어 있지 않으므로 양호함"                                                             				>> $RESULT_FILE 2>&1
		echo [40-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-40]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `cat tmp_40_1.txt | egrep "3:on|:.on|3:활성" | wc -l` -eq 0 ]
			then
				echo "DoS 공격에 취약한 서비스가 설치되어 있으나 실행중이지 않으므로 양호함"                                        					>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                      	>> $RESULT_FILE 2>&1
				cat tmp_40_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [40-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-40]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				echo "DoS 공격에 취약한 서비스가 실행중이므로 취약함"                                                               			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				cat tmp_40_1.txt | egrep "3:on|:.on|3:활성"                                                                        	>> $RESULT_FILE 2>&1
				echo [40-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-40]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_40_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-41]NFS 서비스 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-41]NFS 서비스 비활성화                                                                                                      	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [41-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep -i "nfsd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "NFS 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [41-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-41]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "NFS 서비스가 실행중이므로 취약함"                                                                                     		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1
		ps -ef | grep -i "nfsd" | grep -v "grep"                                                                                    >> $RESULT_FILE 2>&1
		echo [41-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-41]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-42]NFS 접근통제 
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-42]NFS 접근통제                                                                                                             	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [42-START]                                                                                                                     >> $RESULT_FILE 2>&1

if [ `ps -ef | grep -i "nfsd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "NFS 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [42-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-42]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ -f /etc/exports ]
			then
				if [ `cat /etc/exports | grep -i "everyone" | grep -v "^ *#" | wc -l` -eq 0 ]
					then
						echo "NFS 서비스가 실행중이나 everyone 공유가 존재하지 않으므로 양호함"                                     				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                               	>> $RESULT_FILE 2>&1
						ps -ef | grep -i "nfsd" | grep -v "grep"                                                                    >> $RESULT_FILE 2>&1
						cat /etc/exports                                                                                            >> $RESULT_FILE 2>&1 
						echo [42-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-42]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "NFS 서비스가 실행중이고 everyone 공유가 존재하므로 취약함"                                            			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                               	>> $RESULT_FILE 2>&1
						ps -ef | grep -i "nfsd" | grep -v "grep"                                                                    >> $RESULT_FILE 2>&1
						cat /etc/exports                                                                                            >> $RESULT_FILE 2>&1 
						echo [42-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-42]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
			else
				echo "NFS 서비스가 실행중이나 /etc/exports 파일을 찾을 수 없음"                                                     			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                       	>> $RESULT_FILE 2>&1
				ps -ef | grep -i "nfsd" | grep -v "grep"                                                                            >> $RESULT_FILE 2>&1
				echo [42-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-42]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
		fi
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-43]automountd 제거
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-43]automountd 제거                                                                                                           >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [43-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep -i "automountd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "automountd 서비스가 실행중이지 않으므로 양호함"                                                                       			>> $RESULT_FILE 2>&1
		echo [43-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-43]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "automountd 서비스가 실행중이므로 취약함"                                                                              		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                               	>> $RESULT_FILE 2>&1
		ps -ef | grep -i "automountd" | grep -v "grep"                                                                              >> $RESULT_FILE 2>&1
		echo [43-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-43]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-44]RPC 서비스 확인
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-44]RPC 서비스 확인                                                                                                          	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [44-START]                                                                                                                     >> $RESULT_FILE 2>&1
SERVICE_RPC="rpc.cmsd|rpc.ttdbserverd|sadmind|rusersd|walld|sprayd|rstatd|rpc.nisd|rpc.pcnfsd|rpc.statd|rpc.ypupdated|rpc.rquotad|kcms_server|cachefsd|rexd"
if [ `chkconfig --list | egrep "$SERVICE_RPC" | egrep "3:on|:.on|3:활성" | wc -l` -eq 0 ]
	then
		echo "RPC 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [44-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-44]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1		
	else
		echo "RPC 서비스가 실행중이므로 취약함"                                                                                     		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		chkconfig --list | egrep "$SERVICE_RPC"                                                                                     >> $RESULT_FILE 2>&1
		echo [44-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-44]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1	
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-45]NIS, NIS+ 점검
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-45]NIS, NIS+ 점검                                                                                                            >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [45-START]                                                                                                                     >> $RESULT_FILE 2>&1
SERVICE_NIS="ypserv|ypbind|ypxfrd|rpc.yppasswdd|rpc.ypupdated|rpc.nisd"
if [ `ps -ef | egrep $SERVICE_NIS | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "NIS 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [45-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-45]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "NIS 서비스가 실행중이므로 취약함"                                                                                     		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		ps -ef | egrep $SERVICE_NIS | grep -v "grep"                                                                                >> $RESULT_FILE 2>&1
		echo [45-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-45]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
 

echo [U-46]tftp, talk 서비스 비활성화
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-46]tftp, talk 서비스 비활성화                                                                                               	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [46-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `chkconfig --list | egrep "tftp|talk" | egrep "3:on|:.on|3:활성" | wc -l` -eq 0 ]
	then
		echo "tftp, talk 서비스가 실행중이지 않으므로 양호함"                                                                       			>> $RESULT_FILE 2>&1
		echo [46-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-46]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1		
	else
		echo "tftp, talk 서비스가 실행중이므로 취약함"                                                                              		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		chkconfig --list | egrep "tftp|talk"                                                                                        >> $RESULT_FILE 2>&1
		echo [46-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-46]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1	
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-47]Sendmail 버전 점검
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-47]Sendmail 버전 점검                                                                                                       	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [47-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep sendmail | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "Sendmail 서비스가 실행중이지 않으므로 양호함"                                                                         			>> $RESULT_FILE 2>&1
		echo [47-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-47]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `find /etc -name "sendmail.cf" | wc -l` -eq 0 ]
			then
				echo "Sendmail 서비스가 실행중이나 sendmail.cf 파일을 찾을 수 없음"                                                 			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ps -ef | grep sendmail | grep -v "grep"                                                                             >> $RESULT_FILE 2>&1
				echo [47-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-47]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				find /etc -name "sendmail.cf" -exec cat {} > tmp_47_1.txt \;			
				if [ `cat tmp_47_1.txt | grep -v '^ *#' | grep DZ | egrep "8.14" | wc -l` -eq 0 ]
					then 
						echo "취약한 버전의 Sendmail 서비스가 실행중이므로 취약함"                                                  			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						echo "Sendmail 버전 : `cat tmp_47_1.txt | grep -v '^ *#' | grep DZ`"                                         >> $RESULT_FILE 2>&1
						echo [47-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-47]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
					else
						echo "취약하지 않은 버전의 Sendmail 서비스가 실행중이므로 양호함"                                           				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						echo "Sendmail 버전 : `cat tmp_47_1.txt | grep -v '^ *#' | grep DZ`"                                         >> $RESULT_FILE 2>&1
						echo [47-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-47]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
				fi
		fi
fi
rm -rf tmp_47_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-48]스팸 메일 릴레이 제한
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-48]스팸 메일 릴레이 제한                                                                                                    		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [48-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep sendmail | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "Sendmail 서비스가 실행중이지 않으므로 양호함"                                                                         			>> $RESULT_FILE 2>&1
		echo [48-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-48]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `find /etc -name "sendmail.cf" | wc -l` -eq 0 ]
			then
				echo "Sendmail 서비스가 실행중이나 sendmail.cf 파일을 찾을 수 없음"                                                 			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ps -ef | grep sendmail | grep -v "grep"                                                                             >> $RESULT_FILE 2>&1
				echo [48-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-48]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				find /etc -name "sendmail.cf" -exec cat {} > tmp_48_1.txt \;
				if [ `cat tmp_48_1.txt | grep -v "^ *#" | grep "R$\*" | grep -i "Relaying denied" | wc -l ` -gt 0 ]
					then
						echo "스팸 메일 릴레이 제한 설정이 적용되었으므로 양호함"                                                   				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						cat tmp_48_1.txt | grep -v "^ *#" | grep "R$\*" | grep -i "Relaying denied"                                 >> $RESULT_FILE 2>&1
						echo [48-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-48]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "스팸 메일 릴레이 제한 설정이 적용되지 않았으므로 취약함"                                              				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						cat tmp_48_1.txt | grep "R$\*" | grep -i "Relaying denied"                                                  >> $RESULT_FILE 2>&1
						echo [48-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-48]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
		fi
fi
rm -rf tmp_48_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-49]일반사용자의 Sendmail 실행 방지
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-49]일반사용자의 Sendmail 실행 방지                                                                                          		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [49-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep sendmail | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "Sendmail 서비스가 실행중이지 않으므로 양호함"                                                                         			>> $RESULT_FILE 2>&1
		echo [49-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-49]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `find /etc -name "sendmail.cf" | wc -l` -eq 0 ]
			then
				echo "Sendmail 서비스가 실행중이나 sendmail.cf 파일을 찾을 수 없음"                                                 			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ps -ef | grep sendmail | grep -v "grep"                                                                             >> $RESULT_FILE 2>&1
				echo [49-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-49]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				find /etc -name "sendmail.cf" -exec cat {} > tmp_49_1.txt \;
				if [ `cat tmp_49_1.txt | grep -i "O PrivacyOptions" | grep -i "restrictqrun" | grep -v "#" | wc -l` -gt 0 ]
					then
						echo "일반사용자의 Sendmail 실행 방지 설정이 적용되었으므로 양호함"                                         				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						cat tmp_49_1.txt | grep -i "O PrivacyOptions" | grep -i "restrictqrun"                                      >> $RESULT_FILE 2>&1
						echo [49-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-49]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "일반사용자의 Sendmail 실행 방지 설정이 적용되지 않았으므로 취약함"                                    				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						ps -ef | grep sendmail | grep -v "grep"                                                                     >> $RESULT_FILE 2>&1
						cat tmp_49_1.txt | grep -i "O PrivacyOptions"                                                               >> $RESULT_FILE 2>&1
						echo [49-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-49]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
		fi
fi
rm -rf tmp_49_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-50]DNS 보안 버전 패치
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-50]DNS 보안 버전 패치                                                                                                       	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [50-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `netstat -anp | awk '{print $4}' | grep ":53$" | wc -l` -eq 0 ]
	then
		echo "DNS 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [50-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-50]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		named -v > /dev/null
		if [ $? -eq 0 ]
			then
				echo "DNS 서비스가 실행중이며 버전을 확인하여 결과 분석"                                                            			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				named -v                                                                                                            >> $RESULT_FILE 2>&1
				echo [50-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-50]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				if [ -f /usr/sbin/named ]
					then
						echo "DNS 서비스가 실행중임 버전을 확인하여 결과 분석"                                                      			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						/usr/sbin/named -v                                                                                          >> $RESULT_FILE 2>&1
						echo [50-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-50]Result : MANUAL                                                                                  >> $RESULT_FILE 2>&1
					else
						if [ -f /usr/sbin/named8 ]
							then
								echo "DNS 서비스가 실행중임 버전을 확인하여 결과 분석"                                              			>> $RESULT_FILE 2>&1
								echo                                                                                                >> $RESULT_FILE 2>&1
								echo "[현황]"                                                                                        >> $RESULT_FILE 2>&1
								/usr/sbin/named8 -v                                                                                 >> $RESULT_FILE 2>&1
								echo [50-END]                                                                                       >> $RESULT_FILE 2>&1
								echo                                                                                                >> $RESULT_FILE 2>&1
								echo [U-50]Result : MANUAL                                                                          >> $RESULT_FILE 2>&1
							else
								echo "DNS 서비스가 실행중이나 실행 데몬을 찾을 수 없음"                                             			>> $RESULT_FILE 2>&1
								echo [50-END]                                                                                       >> $RESULT_FILE 2>&1
								echo                                                                                                >> $RESULT_FILE 2>&1
								echo [U-50]Result : MANUAL                                                                          >> $RESULT_FILE 2>&1
						fi
				fi
		fi
fi		
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-51]DNS ZoneTransfer 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-51]DNS ZoneTransfer 설정                                                                                                     >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [51-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `netstat -anp | awk '{print $4}' | grep ":53$" | wc -l` -eq 0 ]
	then
		echo "DNS 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [51-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-51]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		cat /etc/named.conf /etc/named.rfc1912.zones /etc/named.boot > tmp_51_1.txt 2> /dev/null
		if [ `cat tmp_51_1.txt | wc -l` -eq 0 ]
			then
				echo "DNS 서비스가 실행중이나 설정파일을 찾을 수 없음"                                                              			>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				netstat -anp | grep ":53 "                                                                                          >> $RESULT_FILE 2>&1
				echo [51-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-51]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				if [ `cat tmp_51_1.txt | grep "allow-transfer" | grep -v "#" | wc -l` -eq 0 ]
					then
						echo "DNS 서비스가 실행중이며 DNS ZoneTransfer 설정이 적용되지 않았으므로 취약함"                           				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						netstat -anp | grep ":53 "                                                                                  >> $RESULT_FILE 2>&1						
						echo [51-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-51]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
					else
						echo "DNS 서비스가 실행중이며 DNS ZoneTransfer 설정이 적용되었으므로 양호함"                                				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						netstat -anp | grep ":53 "                                                                                  >> $RESULT_FILE 2>&1
						cat tmp_51_1.txt | grep "allow-transfer" | grep -v "#"                                                      >> $RESULT_FILE 2>&1
						echo [51-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-51]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
				fi
		fi
fi
rm -rf tmp_51_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


##################################################홈 디렉터리 경로 탐색##################################################

if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -ge 1 ]
echo
	then
		APROC1=`ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq`
		APROC=`echo $APROC1 | awk '{print $1}'`

		if [ `$APROC -V | grep -i "root" | wc -l` -ge 1 ]
			then
				AHOME=`$APROC -V | grep -i "root" | awk -F"\"" '{print $2}'`
				ACFILE=`$APROC -V | grep -i "server_config_file" | awk -F"\"" '{print $2}'`
			else
				AHOME=/apache_test	#디렉터리 확인 필요
				ACFILE=apache_test	#디렉터리 확인 필요
		fi

		if [ -f $AHOME/$ACFILE ]
			then
				HTTP_CONF_INP=$AHOME/$ACFILE
			else
				HTTP_CONF_INP=$ACFILE
		fi
fi


HTTP_ROOT=`grep -i "ServerRoot" $HTTP_CONF_INP | grep -v "#" | head -1 | awk -F\" '{print $2}'`
HTTP_DOC_ROOT=`grep -i "DocumentRoot" $HTTP_CONF_INP | grep -v "#" | head -1 | awk -F\" '{print $2}'`

if [ `grep -i "^Include" $HTTP_CONF_INP | grep -v "#" | wc -l` -eq 0 ]
	then
		cat $HTTP_CONF_INP > http_conf.txt
	else
		cat $HTTP_CONF_INP > http_conf.txt
		for a in `grep -i "^Include" $HTTP_CONF_INP | grep -v "#" | awk '{print $2}'`
			do 
				cat $HTTP_ROOT/$a >> http_conf.txt 
		done
fi

HTTP_CONF=./http_conf.txt

################################################홈 디렉터리 경로 탐색 종료################################################


echo [U-52]Apache 디렉토리 리스팅 제거
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-52]Apache 디렉토리 리스팅 제거                                                                                              		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [52-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -ge 1 ]
	then
		if [ `grep -w "Indexes" $HTTP_CONF_INP | grep -v "#" | wc -l` -eq 0 ]
			then
				echo "Indexes 옵션이 존재하지 않으므로 양호함"																				>> $RESULT_FILE 2>&1
				echo [52-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-52]Result : GOOD 																							>> $RESULT_FILE 2>&1
			else
				echo "Indexes 옵션이 존재하므로 취약함" 																					>> $RESULT_FILE 2>&1
				echo                                                                                                        		>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				grep -inw "Indexes" $HTTP_CONF_INP | grep -v "#" 																	>> $RESULT_FILE 2>&1
				echo [52-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-52]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [52-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-52]Result : N/A 																									>> $RESULT_FILE 2>&1
fi
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1


echo [U-53]Apache 웹 프로세스 권한 제한
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-53]Apache 웹 프로세스 권한 제한                                                                                             		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [53-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		egrep -in "^User" $HTTP_CONF 										 > tmp_53.txt
		egrep -in "^Group" $HTTP_CONF 										>> tmp_53.txt
		if [ `cat tmp_53.txt | grep -w "root" | wc -l` -eq 0 ]
			then
				echo "Apache 구동 계정이 root가 아닌 일반 계정이므로 양호함" 																	>> $RESULT_FILE 2>&1
				echo                                                                                                        		>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				cat tmp_53.txt 																										>> $RESULT_FILE 2>&1
				echo [53-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-53]Result : GOOD 																							>> $RESULT_FILE 2>&1
			else
				echo "Apache 데몬이 root 계정으로 구동되므로 취약함" 																		>> $RESULT_FILE 2>&1
				echo                                                                                                        		>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				cat tmp_53.txt 																										>> $RESULT_FILE 2>&1
				echo [53-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-53]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [53-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-53]Result : N/A 																									>> $RESULT_FILE 2>&1
fi
rm -rf tmp_53.txt
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1


echo [U-54]Apache 상위 디렉토리 접근 금지
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-54]Apache 상위 디렉토리 접근 금지                                                                                           		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [54-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		grep -win "AllowOverride" $HTTP_CONF | grep -v "#" > tmp_54.txt
		if [ `cat tmp_54.txt | wc -l` -eq 0 ]
			then
				echo "AllowOverride 설정이 존재하지 않으므로 취약함"																			>> $RESULT_FILE 2>&1
				echo [54-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-54]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
			else
				if [ `cat tmp_54.txt | grep -wi "None" | wc -l` -eq 0 ]
					then
						echo "AllowOverride None 설정이 존재하지 않으므로 양호함" 															>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]" 																								>> $RESULT_FILE 2>&1
						cat tmp_54.txt 																								>> $RESULT_FILE 2>&1
						echo [54-END] 																								>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-54]Result : GOOD 																					>> $RESULT_FILE 2>&1
					else
						echo "AllowOverride None 설정이 존재하므로 취약함" 																>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]" 																								>> $RESULT_FILE 2>&1
						cat tmp_54.txt 																								>> $RESULT_FILE 2>&1
						echo [54-END] 																								>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-54]Result : VULNERABLE 																				>> $RESULT_FILE 2>&1
				fi
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [54-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-54]Result : N/A 																									>> $RESULT_FILE 2>&1
fi
rm -rf tmp_54.txt
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1                                                                                                                       
																													   

echo [U-55]Apache 불필요한 파일 제거
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-55]Apache 불필요한 파일 제거                                                                                                		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [55-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		if [ `ls -ld $HTTP_ROOT/manual | wc -l` -eq 0 ]
			then
				if [ `ls -ld $HTTP_DOC_ROOT/manual | wc -l` -eq 0 ]
					then
						echo "불필요한 매뉴얼 파일이 존재하지 않으므로 양호함"																	>> $RESULT_FILE 2>&1
						echo [55-END] 																								>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-55]Result : GOOD 																					>> $RESULT_FILE 2>&1
					else
						echo "불필요한 매뉴얼 파일이 존재하므로 취약함"																		>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]" 																								>> $RESULT_FILE 2>&1
						ls -ld $HTTP_DOC_ROOT/manual 																				>> $RESULT_FILE 2>&1
						echo [55-END] 																								>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-55]Result : VULNERABLE 																				>> $RESULT_FILE 2>&1
				fi
			else
				echo "불필요한 manual 파일이 존재하므로 취약함" 																				>> $RESULT_FILE 2>&1
				echo                                                                                                      		 	>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				ls -ld $HTTP_ROOT/manual 																							>> $RESULT_FILE 2>&1
				echo [55-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-55]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [55-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-55]Result : N/A 																									>> $RESULT_FILE 2>&1
fi				
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1


echo [U-56]Apache 링크 사용금지
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-56]Apache 링크 사용금지                                                                                                     	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [56-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		if [ `grep -wi "FollowSymLinks" $HTTP_CONF_INP | grep -v "#" | wc -l` -eq 0 ]
			then
				echo "FollowSymLinks 옵션이 존재하지 않으므로 양호함" 																		>> $RESULT_FILE 2>&1
				echo [56-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-56]Result : GOOD 																							>> $RESULT_FILE 2>&1
			else
				echo "FollowSymLinks 옵션이 존재하므로 취약함" 																			>> $RESULT_FILE 2>&1
				echo                                                                                                      		 	>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				grep -inw "FollowSymLinks" $HTTP_CONF_INP | grep -v "#" 															>> $RESULT_FILE 2>&1
				echo [56-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-56]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [56-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-56]Result : N/A 																									>> $RESULT_FILE 2>&1
fi		
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1                                                                                                     
																									 

echo [U-57]Apache 파일 업로드 및 다운로드 제한
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-57]Apache 파일 업로드 및 다운로드 제한                                                                                      		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [57-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		if [ `grep -wi "LimitRequestBody" $HTTP_CONF | grep -v "#" | wc -l` -eq 0 ]
			then
				echo "LimitRequestBody 옵션이 존재하지 않으므로 취약함" 																		>> $RESULT_FILE 2>&1
				echo [57-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-57]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
			else
				echo "LimitRequestBody 옵션이 존재하므로 양호함" 																			>> $RESULT_FILE 2>&1
				echo                                                                                                      		 	>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				grep -inw "LimitRequestBody" $HTTP_CONF | grep -v "#" 																>> $RESULT_FILE 2>&1
				echo [57-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-57]Result : GOOD 																							>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [57-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-57]Result : N/A 																									>> $RESULT_FILE 2>&1
fi		
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1                                                                                                                         


echo [U-58]Apache 웹 서비스 영역의 분리
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-58]Apache 웹 서비스 영역의 분리                                                                                             		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [58-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		if [ `echo $HTTP_DOC_ROOT | egrep -w "/usr/local/apache/htdocs|/var/www/html" | wc -l` -eq 0 ]
			then
				echo "DocumentRoot로 기본경로를 사용하지 않으므로 양호함" 																	>> $RESULT_FILE 2>&1
				echo                                                                                                      		 	>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				echo $HTTP_DOC_ROOT 																								>> $RESULT_FILE 2>&1
				echo [58-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-58]Result : GOOD 																							>> $RESULT_FILE 2>&1
			else
				echo "DocumentRoot로 기본경로를 사용하므로 취약함" 																			>> $RESULT_FILE 2>&1
				echo                                                                                                      		 	>> $RESULT_FILE 2>&1
				echo "[현황]" 																										>> $RESULT_FILE 2>&1
				echo $HTTP_DOC_ROOT 																								>> $RESULT_FILE 2>&1
				echo [58-END] 																										>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-58]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [58-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-58]Result : N/A 																									>> $RESULT_FILE 2>&1
fi	
echo >> $RESULT_FILE 2>&1
echo >> $RESULT_FILE 2>&1


echo [U-59]ssh 원격접속 허용
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-59]ssh 원격접속 허용                                                                                                        	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [59-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "sshd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "SSH 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [59-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-59]Result : MANUAL                                                                                                  >> $RESULT_FILE 2>&1
	else
		echo "SSH 서비스가 실행중이므로 양호함"                                                                                     		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		ps -ef | grep "sshd" | grep -v "grep"                                                                                       >> $RESULT_FILE 2>&1
		echo [59-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-59]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
 

echo [U-60]ftp 서비스 확인
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-60]ftp 서비스 확인                                                                                                          	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [60-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "ftpd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "FTP 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [60-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-60]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "FTP 서비스가 실행중이므로 취약함"                                                                                     		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		ps -ef | grep "ftpd" | grep -v "grep"                                                                                       >> $RESULT_FILE 2>&1
		echo [60-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-60]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-61]ftp 계정 shell 제한
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-61]ftp 계정 shell 제한                                                                                                      	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [61-START]                                                                                                                     >> $RESULT_FILE 2>&1
cat /etc/passwd | grep -w "^ftp" > tmp_61_1.txt
if [ `cat tmp_61_1.txt | wc -l` -eq 0 ]
	then
		echo "/etc/passwd 파일에 ftp 계정이 존재하지 않으므로 양호함"                                                               			>> $RESULT_FILE 2>&1
		echo [61-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-61]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `cat tmp_61_1.txt | awk -F: '{print $7}' | egrep -v "false|nologin|null|halt|sync|shutdown" | wc -l` -eq 0 ]
			then
				echo "ftp 계정에 로그인 가능한 쉘이 부여되지 않았으므로 양호함"                                                     				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_61_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [61-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-61]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				echo "ftp 계정에 로그인 가능한 쉘이 부여되었으므로 취약함"                                                          				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_61_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [61-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-61]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_61_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-62]Ftpusers 파일 소유자 및 권한 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-62]Ftpusers 파일 소유자 및 권한 설정                                                                                        		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [62-START]                                                                                                                     >> $RESULT_FILE 2>&1
find /etc -name "ftpusers" -exec ls -lL {} \; > tmp_62_1.txt
if [ `cat tmp_62_1.txt | wc -l` -eq 0 ]
	then
		echo "ftpusers 파일을 찾을 수 없음"                                                                                         		>> $RESULT_FILE 2>&1
		echo [62-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-62]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `cat tmp_62_1.txt | grep "^.....-----" | awk '$3=="root"' | wc -l` -eq 0 ]
			then
				echo "ftpusers 파일의 소유자(root) 및 퍼미션이 기준에 맞게 설정되지 않았으므로 취약함"                              					>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_62_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [62-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-62]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
			else
				echo "ftpusers 파일의 소유자(root) 및 퍼미션이 기준에 맞게 설정되었으므로 양호함"                                   				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_62_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [62-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-62]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1				
		fi
fi
rm -rf tmp_62_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-63]Ftpusers 파일 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-63]Ftpusers 파일 설정                                                                                                       	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [63-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep -i "ftpd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "FTP 서비스가 실행중이지 않으므로 양호함"                                                                              			>> $RESULT_FILE 2>&1
		echo [63-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-63]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		find /etc -name "ftpusers" -exec ls -lL {} \; > tmp_63_1.txt
		if [ `cat tmp_63_1.txt | wc -l` -eq 0 ]
			then
				echo "ftpusers 파일을 찾을 수 없으므로 양호함"                                                                      		>> $RESULT_FILE 2>&1
				echo [63-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-63]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				find /etc -name "ftpusers" -exec cat {} \; > tmp_63_2.txt
				if [ `cat tmp_63_2.txt | grep "root" | grep -v "^ *#" | wc -l` -gt 0 ]
					then
						echo "FTP 서비스가 실행중이며, ftpusers 파일에 root가 존재하므로 양호함"                                    				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_63_1.txt                                                                                            >> $RESULT_FILE 2>&1
						cat tmp_63_2.txt                                                                                            >> $RESULT_FILE 2>&1
						echo [63-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-63]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "FTP 서비스가 실행중이며, ftpusers 파일에 root가 존재하지 않으므로 취약함"                             				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_63_1.txt                                                                                            >> $RESULT_FILE 2>&1
						cat tmp_63_2.txt                                                                                            >> $RESULT_FILE 2>&1
						echo [63-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-63]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
		fi	
fi		
rm -rf tmp_63_1.txt
rm -rf tmp_63_2.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-64]at 파일 소유자 및 권한 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-64]at 파일 소유자 및 권한 설정                                                                                              		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [64-START]                                                                                                                     >> $RESULT_FILE 2>&1
ls -l /etc/* | egrep "at.deny|at.allow" > tmp_64_1.txt
if [ `cat tmp_64_1.txt | wc -l` -eq 0 ]
	then
		echo "at.deny, at.allow 파일을 찾을 수 없으므로 양호함"                                                                     		>> $RESULT_FILE 2>&1
		echo [64-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-64]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		cat tmp_64_1.txt | grep "^.....-----" | awk '$3=="root"' > tmp_64_2.txt
		if [ `diff tmp_64_1.txt tmp_64_2.txt | wc -l` -eq 0 ]
			then
				echo "at 파일의 소유자(root) 및 퍼미션(640)이 기준에 맞게 적용되어 있으므로 양호함"                                 				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_64_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [64-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-64]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
			else
				echo "at 파일의 소유자(root) 및 퍼미션(640)이 기준에 맞게 적용되어 있지 않으므로 취약함"                            					>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				cat tmp_64_1.txt                                                                                                    >> $RESULT_FILE 2>&1
				echo [64-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-64]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
		fi
fi
rm -rf tmp_64_1.txt
rm -rf tmp_64_2.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-65]SNMP 서비스 구동 점검
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-65]SNMP 서비스 구동 점검                                                                                                    	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [65-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "snmpd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "SNMP 서비스가 실행중이지 않으므로 양호함"                                                                             			>> $RESULT_FILE 2>&1
		echo [65-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-65]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "SNMP 서비스가 실행중이므로 취약함"                                                                                    		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		ps -ef | grep "snmpd" | grep -v "grep"                                                                                      >> $RESULT_FILE 2>&1
		echo [65-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-65]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-66]SNMP 서비스 커뮤니티스트링의 복잡성 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-66]SNMP 서비스 커뮤니티스트링의 복잡성 설정                                                                                 			>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [66-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "snmpd" | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "SNMP 서비스가 실행중이지 않으므로 양호함"                                                                             			>> $RESULT_FILE 2>&1
		echo [66-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-66]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		find /etc -name "snmpd.conf" -exec cat {} \; > tmp_66_1.txt
		if [ `cat tmp_66_1.txt | wc -l` -gt 0 ]
			then
				if [ `cat tmp_66_1.txt | grep -i "com2sec" | grep "public" | grep -v "^ *#" | wc -l` -eq 0 ]
					then
						echo "SNMP Community String이 임의의 값으로 설정되었으므로 양호함"                                          			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_66_1.txt | grep -i "com2sec" | grep -v "^ *#"                                                       >> $RESULT_FILE 2>&1
						echo [66-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-66]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
					else
						echo "SNMP Community String이 기본값으로 설정되어있으므로 취약함"                                           			>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_66_1.txt | grep -i "com2sec" | grep -v "^ *#"                                                       >> $RESULT_FILE 2>&1
						echo [66-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-66]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
				fi
			else
				echo "SNMP 서비스가 실행중이나 설정파일을 찾을 수 없음"                                                             			>> $RESULT_FILE 2>&1
				echo [66-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-66]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
		fi						
fi
rm -rf tmp_66_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-67]로그온 시 경고 메시지 제공
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-67]로그온 시 경고 메시지 제공                                                                                               		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [67-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `cat /etc/motd | wc -l` -gt 0 ]
	then
		echo "/etc/motd 파일에 경고 메시지가 설정되어 있으므로 양호함"                                                              			>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		cat /etc/motd                                                                                                               >> $RESULT_FILE 2>&1
		echo [67-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-67]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "/etc/motd 파일에 경고 메시지가 설정되지 않으므로 취약함"                                                              			>> $RESULT_FILE 2>&1
		echo [67-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-67]Result : VULNERABLE                                                                                              >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-68]NFS 설정 파일 접근 권한 
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-68]NFS 설정 파일 접근 권한                                                                                                  		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [68-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ -f /etc/exports ]
	then
		if [ `ls -lL /etc/exports | grep "^.....--.--" | wc -l` -eq 0 ]
			then
				echo "/etc/exports 파일의 퍼미션(644)이 기준에 맞게 설정되지 않으므로 취약함"                                       				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ls -lL /etc/exports                                                                                                 >> $RESULT_FILE 2>&1
				echo [68-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-68]Result : VULNERABLE                                                                                      >> $RESULT_FILE 2>&1
			else
				echo "/etc/exports 파일의 퍼미션(644)이 기준에 맞게 설정되어 있으므로 양호함"                                       				>> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo "[현황]"                                                                                                        >> $RESULT_FILE 2>&1
				ls -lL /etc/exports                                                                                                 >> $RESULT_FILE 2>&1
				echo [68-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-68]Result : GOOD                                                                                            >> $RESULT_FILE 2>&1
		fi	
	else	
		echo "/etc/exports 파일을 찾을 수 없음"                                                                                     		>> $RESULT_FILE 2>&1
		echo [68-END]                                                                                                  	            >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-68]Result : N/A                                                                                                     >> $RESULT_FILE 2>&1
fi
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-69]expn, vrfy 명령어 제한
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-69]expn, vrfy 명령어 제한                                                                                                   	>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [69-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep sendmail | grep -v "grep" | wc -l` -eq 0 ]
	then
		echo "Sendmail 서비스가 실행중이지 않으므로 양호함"                                                                         			>> $RESULT_FILE 2>&1
		echo [69-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-69]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		if [ `find /etc -name "sendmail.cf" | wc -l` -eq 0 ]
			then
				echo "Sendmail 서비스가 실행중이나 sendmail.cf 파일을 찾을 수 없음"                                                 			>> $RESULT_FILE 2>&1
				echo [69-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-69]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
			else
				find /etc -name "sendmail.cf" -exec cat {} > tmp_69.txt \;			
				cat tmp_69.txt | grep -i "O PrivacyOptions" > tmp_69_1.txt
				if [ `cat tmp_69_1.txt | grep -v "^ *#" | grep "noexpn" | grep "novrfy" | wc -l` -eq 0 ]
					then
						echo "Sendmail 서비스가 실행중이며 sendmail.cf 파일에 noexpn, novrfy 옵션이 적용되지 않았으므로 취약함"     				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_69_1.txt                                                                                            >> $RESULT_FILE 2>&1
						echo [69-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-69]Result : VULNERABLE                                                                              >> $RESULT_FILE 2>&1
					else
						echo "Sendmail 서비스가 실행중이며 sendmail.cf 파일에 noexpn, novrfy 옵션이 적용되있으므로 양호함"          				>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]"                                                                                                >> $RESULT_FILE 2>&1
						cat tmp_69_1.txt                                                                                            >> $RESULT_FILE 2>&1
						echo [69-END]                                                                                               >> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [U-69]Result : GOOD                                                                                    >> $RESULT_FILE 2>&1
				fi
		fi
fi
rm -rf tmp_69.txt
rm -rf tmp_69_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-70]Apache 웹서비스 정보 숨김
echo "=======================================================================" 	                                                    >> $RESULT_FILE 2>&1
echo [U-70]Apache 웹서비스 정보 숨김                                                                                                		>> $RESULT_FILE 2>&1
echo "=======================================================================" 	                                                    >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [70-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ `ps -ef | grep "httpd" | grep -v "ns-httpd" | grep -v "grep" | awk '{print $8}' | grep "/" | grep -v "httpd.conf" | uniq | wc -l` -gt 0 ]
	then
		if [ `grep -wi "servertokens" $HTTP_CONF | grep -v "#" | wc -l` -eq 0 ]
			then
				echo "ServerTokens 옵션이 존재하지 않으므로 취약함" 																			>> $RESULT_FILE 2>&1
				echo [70-END] 																									 	>> $RESULT_FILE 2>&1
				echo 																												>> $RESULT_FILE 2>&1
				echo [U-70]Result : VULNERABLE 																						>> $RESULT_FILE 2>&1
			else
				if [ `grep -wi "servertokens" $HTTP_CONF | grep -v "#" | grep -wi "prod" | wc -l` -eq 0 ]
					then
						echo "ServerTokens 옵션이 Prod로 설정되지 않으므로 취약함"															>> $RESULT_FILE 2>&1
						echo [70-END] 																								>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo "[현황]" 																								>> $RESULT_FILE 2>&1
						grep -wi "servertokens" $HTTP_CONF | grep -v "#" 															>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-70]Result : VULNERABLE 																				>> $RESULT_FILE 2>&1
					else
						echo "ServerTokens 옵션이 Prod로 설정되어 있으므로 양호함"															>> $RESULT_FILE 2>&1
						echo                                                                                                        >> $RESULT_FILE 2>&1
						echo [70-END] 																								>> $RESULT_FILE 2>&1
						echo "[현황]" 																								>> $RESULT_FILE 2>&1
						grep -wi "servertokens" $HTTP_CONF | grep -v "#" 															>> $RESULT_FILE 2>&1
						echo 																										>> $RESULT_FILE 2>&1
						echo [U-70]Result : GOOD 																					>> $RESULT_FILE 2>&1
				fi

		fi
	else
		echo "Apache Service Disable" 																								>> $RESULT_FILE 2>&1
		echo [70-END] 																												>> $RESULT_FILE 2>&1
		echo 																														>> $RESULT_FILE 2>&1
		echo [U-70]Result : N/A 																									>> $RESULT_FILE 2>&1
fi	
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1


echo [U-71]최신 보안패치 및 벤더 권고사항 적용
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-71]최신 보안패치 및 벤더 권고사항 적용                                                                                      			>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
# echo [71-START]                                                                                                                   >> $RESULT_FILE 2>&1
# echo "인터뷰 점검 항목"                                                                                                          		>> $RESULT_FILE 2>&1
# echo [71-END]                                                                                                                     >> $RESULT_FILE 2>&1
# echo                                                                                                                              >> $RESULT_FILE 2>&1
# echo [U-71]Result : MANUAL                                                                                                        >> $RESULT_FILE 2>&1
echo [71-START]                                                                                                                     >> $RESULT_FILE 2>&1
echo "아래 현황을 기반으로 수동분석"                                                                                                		>> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "[현황]"                                                                                                                        >> $RESULT_FILE 2>&1
echo "1) OpenSSL Version"                                                                                                           >> $RESULT_FILE 2>&1
rpm -q openssl                                                                                                                      >> $RESULT_FILE 2>&1
rpm -q openssl --changelog | head -2                                                                                                >> $RESULT_FILE 2>&1
echo "2) Bash Shell Version"                                                                                                        >> $RESULT_FILE 2>&1
rpm -q bash                                                                                                                         >> $RESULT_FILE 2>&1
rpm -q bash --changelog | head -2                                                                                                   >> $RESULT_FILE 2>&1
echo [71-END]                                                                                                                       >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [U-71]Result : MANUAL                                                                                                          >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo [U-72]로그의 정기적 검토 및 보고
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-72]로그의 정기적 검토 및 보고                                                                                               		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [72-START]                                                                                                                     >> $RESULT_FILE 2>&1
echo "인터뷰 점검 항목"                                                                                                             	>> $RESULT_FILE 2>&1
echo [72-END]                                                                                                                       >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo [U-72]Result : MANUAL                                                                                                          >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1


echo [U-73]정책에 따른 시스템 로깅 설정
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [U-73]정책에 따른 시스템 로깅 설정                                                                                             		>> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo [73-START]                                                                                                                     >> $RESULT_FILE 2>&1
if [ -f /etc/syslog.conf ]
	then
		cat /etc/syslog.conf | grep -v "#" | awk '$0 != null {print $0}' > tmp_73_1.txt
	else
		if [ -f /etc/rsyslog.conf ]
			then
				cat /etc/rsyslog.conf | grep -v "#" | awk '$0 != null {print $0}' > tmp_73_1.txt
			else
				echo "(r)syslog.conf 파일을 찾을 수 없음"                                                                           		>> $RESULT_FILE 2>&1
				echo [73-END]                                                                                                       >> $RESULT_FILE 2>&1
				echo                                                                                                                >> $RESULT_FILE 2>&1
				echo [U-73]Result : MANUAL                                                                                          >> $RESULT_FILE 2>&1
		fi
fi
if [ `cat tmp_73_1.txt | egrep -w "cron.\*|authpriv.\*|\*.info" | wc -l` -eq 3 ]
	then
		echo "(r)syslog.conf 설정이 기준에 맞게 설정되어있으므로 양호함 "                                                           			>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		cat tmp_73_1.txt                                                                                                            >> $RESULT_FILE 2>&1
		echo [73-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-73]Result : GOOD                                                                                                    >> $RESULT_FILE 2>&1
	else
		echo "아래 현황을 기반으로 수동분석 "                                                                                       		>> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo "[현황]"                                                                                                                >> $RESULT_FILE 2>&1
		cat tmp_73_1.txt                                                                                                            >> $RESULT_FILE 2>&1
		echo [73-END]                                                                                                               >> $RESULT_FILE 2>&1
		echo                                                                                                                        >> $RESULT_FILE 2>&1
		echo [U-73]Result : MANUAL                                                                                                  >> $RESULT_FILE 2>&1
fi
rm -rf tmp_73_1.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "======================== CHECK END ========================="                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo ""                                                                                                                             >> $RESULT_FILE 2>&1
echo ""                                                                                                                             >> $RESULT_FILE 2>&1

echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Version ]"                                                                                                                  >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
uname -a                                                                                                                            >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
cat /etc/redhat-release                                                                                                             >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Interface ]"                                                                                                                >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
ifconfig -a                                                                                                                         >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Socket ]"                                                                                                                   >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
netstat -ntpl                                                                                                                       >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Daemon ]"                                                                                                                   >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "1) ps -ef"                                                                                                                    >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
ps -ef                                                                                                                              >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "2) chkconfig --list"                                                                                                          >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
chkconfig --list                                                                                                                    >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Iptables ]"                                                                                                                 >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
iptables -L                                                                                                                         >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ TCP Wrapper ]"                                                                                                              >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "1) /etc/hosts.deny"                                                                                                           >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
cat /etc/hosts.deny                                                                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "2) /etc/hosts.allow"                                                                                                          >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
cat /etc/hosts.allow                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ NTP ]"                                                                                                                      >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "1) NTP 데몬 상태"                                                                                                            	>> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
ntpq -p                                                                                                                             >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo "2) NTP 서버와 시간 차이"                                                                                                      	>> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
rdate -p 203.248.240.140                                                                                                            >> $RESULT_FILE 2>&1
rdate -p 203.248.240.103                                                                                                            >> $RESULT_FILE 2>&1
date                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Last password change ]"                                                                                                     >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
cat /etc/shadow | awk -F: '$2!="*" {print $0}' | awk -F: '$2!="!!" {print $1}' > tmp_deh.txt
for var in `cat tmp_deh.txt`; do echo "- $var" && chage -l $var | grep -i "last"; done                                              >> $RESULT_FILE 2>&1
rm -rf tmp_deh.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Password Hashing Algorithm ]"                                                                                               >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
authconfig --test | grep hashing                                                                                                    >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
 

echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Last Access Log ]"                                                                                                          >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo root > tmp_death.txt
cat /etc/passwd | awk -F: '$3>=500 {print $1}' | grep -v nfsnobody >> tmp_death.txt
for var in `cat tmp_death.txt`; do lastlog | grep -w $var; done                                                                     >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1


echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo "[ Account Access IP ]"                                                                                                        >> $RESULT_FILE 2>&1
echo "============================================================"                                                                 >> $RESULT_FILE 2>&1
echo                                                                                                                                >> $RESULT_FILE 2>&1
for var in `cat tmp_death.txt`; do last | grep -w $var; done | grep "pts" | awk '{print $1,"->",$3}' | sort | uniq                  >> $RESULT_FILE 2>&1
rm -rf tmp_death.txt
echo                                                                                                                                >> $RESULT_FILE 2>&1
echo                

echo "============================================================" 																>> $RESULT_FILE 2>&1
echo "[HTTP_CONF]"  																												>> $RESULT_FILE 2>&1
echo "============================================================" 																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
echo "HTTP_CONF" 																													>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
cat http_conf.txt 																													>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
echo 																																>> $RESULT_FILE 2>&1
rm -rf http_conf.txt

clear

echo ""				 																				 >a.txt 2>&1
echo -e "\033[1m"================  Linux Server Security Check Status  ================"\033[m"		>>a.txt 2>&1	
echo ""       																						>>a.txt 2>&1                                                          
echo -n "▷ GOOD : "       >>a.txt && cat $RESULT_FILE | grep -o -w "GOOD"        | wc -w 			>>a.txt 2>&1
echo -n "▷ VULNERABLE : " >>a.txt && cat $RESULT_FILE | grep -o -w "VULNERABLE"  | wc -w 			>>a.txt 2>&1																																																			
echo -n "▷ N/A : "        >>a.txt && cat $RESULT_FILE | grep -o -w "N/A"         | wc -w 			>>a.txt 2>&1
echo -n "▷ MANUAL : "     >>a.txt && cat $RESULT_FILE | grep -o -w "MANUAL"      | wc -w   		>>a.txt 2>&1                                                                                               		  
echo ""																								>>a.txt 2>&1

cat a.txt
cat $RESULT_FILE     																				 >b.txt 2>&1
rm -rf $RESULT_FILE
cat a.txt   																														 >$RESULT_FILE 2>&1
cat b.txt  																															>>$RESULT_FILE 2>&1
rm -rf a.txt
rm -rf b.txt


iconv -c -f utf-8 -t euc-kr $RESULT_FILE > $RESULT_FILE-euc-kr.txt
sed 's/$'"/`echo \\\r`/" $RESULT_FILE-euc-kr.txt > $RESULT_FILE
rm $RESULT_FILE-euc-kr.txt


count_start=`cat $RESULT_FILE | grep -i "start]" | wc -l`
count_end=`cat $RESULT_FILE | grep -i "end]" | wc -l`
count_result=`cat $RESULT_FILE | grep -i "]result" | wc -l`

if [ $count_start -eq 73 -a $count_end -eq 73 -a $count_result -eq 73 ]
	then
		echo ""
		echo -e "\033[1m"==================================================================="\033[m"
		echo ""
		echo -e "\033[1m"　　　　　　　　　　　Security Check Finished.　　　　　　　　　　 "\033[m"
		echo ""
		echo -e "\033[1m"==================================================================="\033[m"
		echo ""
	else
		echo ""
		echo -e "\033[1m"==================================================================="\033[m" 
		echo ""
		echo -e "\031[1m"                            Re-try.                                "\033[m"
		echo ""
		echo -e "\033[1m"==================================================================="\033[m"
		echo ""
fi

