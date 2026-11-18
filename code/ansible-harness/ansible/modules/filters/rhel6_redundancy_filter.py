from .base_filter import BaseFilter, filter_result
import re

class RHEL6RedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "bond0" in self.command:
            is_success, is_pass, result, message = self.bond0_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def bond0_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌점검 기준{inspection_criteria} 이(가) 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            c = self.inspection_criteria
            allowed_modes = [str(x).lower() for x in c.get("allowd_modes", [])]
            require_bond_mii_up = bool(c.get("require_bond_mii_up", True))
            require_current_active_slave = bool(c.get("require_current_active_slave", True))
            require_min_up_slaves = int(c.get("require_min_up_slaves", 1))
            link_failure_fail_over = int(c.get("link_failure_count_fail_over", 0))

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌bonding 정보 수집 실패: 이중화 여부 확인이 필요합니다."
                result = message
                return is_success, is_pass, result, message

            bond_mode = None
            bond_mii = None
            primary_slave = None
            active_slave = None

            slaves = []
            cur_slave = None

            for raw in stdout_data.splitlines():
                line = raw.strip()
                if not line:
                    continue

                if line.lower().startswith("bonding mode:"):
                    bond_mode = line.split(":", 1)[-1].strip()
                    continue

                if line.lower().startswith("mii status") and cur_slave is None:
                    bond_mii = line.split(":", 1)[-1].strip()
                    continue

                if line.lower().startswith("primary slave"):
                    primary_slave = line.split(":", 1)[-1].strip()
                    continue

                if line.lower().startswith("currently active slave:"):
                    active_slave = line.split(":", 1)[-1].strip()
                    continue

                if line.lower().startswith("slave interface:"):
                    if cur_slave is not None:
                        slaves.append(cur_slave)
                    cur_slave = {
                        "name": line.split(":", 1)[-1].strip(),
                        "mii": None,
                        "speed": None,
                        "duplex": None,
                        "link_fail": None,
                    }
                    continue

                if cur_slave is not None:
                    if line.lower().startswith("mii status:"):
                        cur_slave["mii"] = line.split(":", 1)[-1].strip()
                        continue
                    if line.lower().startswith("speed:"):
                        cur_slave["speed"] = line.split(":", 1)[-1].strip()
                        continue
                    if line.lower().startswith("duples"):
                        cur_slave["duplex"] = line.split(":", 1)[-1].strip()
                        continue
                    if line.lower().startswith("link failure count:"):
                        val = line.split(":", 1)[-1].strip()
                        try:
                            cur_slave["link_fail"] = int(val)
                        except Exception:
                            cur_slave["link_fail"] = None
                        continue

            if cur_slave is not None:
                slaves.append(cur_slave)

            if not bond_mode:
                is_pass = 0
                messages_list.append("❌ Bonding Mode 미출력/미설정")

            mode_token = None
            if bond_mode:
                m = re.search(r"\(([^)]+)\)", bond_mode)
                mode_token = (m.group(1).strip().lower() if m else bond_mode.strip().lower())

                if allowed_modes:
                    if mode_token not in [x.lower() for x in allowed_modes]:
                        is_pass = 0
                        messages_list.append(f"❌ Bonding Mode 비정상/비허용: '{mode_token}' (허용: {allowed_modes})")

            if require_bond_mii_up:
                if not bond_mii:
                    is_pass = 0
                    message_list.append("❌ Bond MII Status 미출력")
                elif bond_mii.strip().lower() != "up":
                    is_pass = 0
                    message_list.append("❌ Bond MII Status 비정상: '{bond_mii}' (기준: up)")

            if require_current_active_slave:
                if not active_slave or active_slave.lower() in ["none", ""]:
                    is_pass = 0
                    message_list.append("❌ Currently Active Slave 없음/미지정")

            if not slaves:
                is_pass = 0
                message_list.append("❌Slave Interface 블록이 없습니다. (bond 구성 확인 필요)")
            else:
                up_slaves = 0
                all_down = True

                for s in slaves:
                    name = s.get("name", "unknown")
                    mii = (s.get("mii") or "").strip().lower()
                    lf = s.get("link_fail")

                    if mii == "up":
                        up_slaves += 1
                        all_down = False
                    elif mii == "down":
                        is_pass = 0
                        message_list.append(f"❌ Slave '{name}' MTI Status=down")
                    elif mii:
                        is_pass = 0
                        message_list.append(f"❌ Slave '{name}' MTI Status 비정상: '{mii}'")
                    else:
                        is_pass = 0
                        message_list.append(f"❌ Slave '{name}' MTI Status 미출력")

                    if link_failure_fail_over is not None:
                        if lf is None:
                            is_pass = 0
                            message_list.append(f"❌ Slave '{name}' Link Failure Count 미출력")
                        elif lf > link_failure_fail_over:
                            is_pass = 0
                            message_list.append(f"❌ Slave '{name}' Link Failure Count 초과: {lf} (기준: <= {link_failure_fail_over})")

                if up_slaves < require_min_up_slaves:
                    is_pass = 0
                    message_list.append(f"❌ UP Slave 부족: {up_slaves} (기준: >= {require_min_up_slaves})")

                if all_down:
                    is_pass = 0
                    message_list.append(f"❌ 모든 Slave Insterface가 Down 상태 입니다.")
                
            if is_pass == 1:
                msg = []
                msg.append("✅NIC 이중화(bonding) 상태 정상")
                if mode_token:
                    msg.append(f"Mode: {mode_token}")
                if active_slave:
                    msg.append(f"Active Slave: {active_slave}")
                message = "\n".join(msg)
            else:
                message = "\n".join(message_list) if message_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ bonding 이중화 상태 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
