#!/usr/bin/python
# -*- coding: utf-8 -*-

from .base_filter import BaseFilter, filter_result

class ChronydFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        
        if "systemctl status chronyd" in self.command:
            is_success, is_pass, result, message = self.check_chronyd_systemctl(stdout_data)
        elif "ps -ef | grep chronyd" in self.command:
            is_success, is_pass, result, message = self.check_chronyd_ps(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': "서비스 실행 여부",
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def check_chronyd_systemctl(self, stdout_data):
        try:
            is_pass = 0
            # 'Active: active (running)'과 'chronyd' 프로세스 둘 다 확인
            is_active_running = "Active: active (running)" in stdout_data
            is_process_present = "chronyd" in stdout_data

            if is_active_running and is_process_present:
                is_pass = 1
                message = "chronyd 서비스가 정상적으로 실행 중입니다."
            elif not is_active_running:
                message = "chronyd 서비스가 실행 중이 아닙니다."
            else: # is_active_running is true but is_process_present is false (edge case)
                message = "chronyd 서비스는 active 상태이지만, 프로세스를 찾을 수 없습니다."
            
            result = message + "\n\n" + stdout_data

        except Exception as e:
            is_pass = 0
            message = f"chronyd 상태 평가 실패: {str(e)}"
            result = message
        
        return 1, is_pass, result, message

    def check_chronyd_ps(self, stdout_data):
        try:
            is_pass = 0
            # 'grep' in the line is to exclude the grep process itself from the result
            if "chronyd" in stdout_data and "grep" not in stdout_data:
                is_pass = 1
                message = "chronyd 프로세스가 실행 중입니다."
            else:
                message = "chronyd 프로세스가 실행 중이 아닙니다."

            result = message + "\n\n" + stdout_data

        except Exception as e:
            is_pass = 0
            message = f"chronyd 프로세스 확인 실패: {str(e)}"
            result = message

        return 1, is_pass, result, message
