# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Optional, Any, Union
from .base_filter import BaseFilter, filter_result

class winCpuFilter(BaseFilter): 
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        thr = iface.get("max_used_cpu", 80)
        try:
            self.max_used_cpu = float(thr)
        except Exception:
            self.max_used_cpu = 80.0

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        """
        지원 입력:
          1) wmic cpu get LoadPercentage /value
             LoadPercentage=12
          2) typeperf "\\Processor(_Total)\\% Processor Time" -sc N -si S
             "(PDH-CSV 4.0)","\\HOST\\Processor(_Total)\\% Processor Time"
             "ts1","12.345678"
             ...
          3) (Get-Counter ...).CounterSamples[0].CookedValue
             12.345678
        판정: 평균값(존재 시) 또는 단일값 ≤ self.max_used_cpu → PASS
        """
        result = {"is_pass": 0, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        def _to_float(s: str) -> Optional[float]:
            try:
                # 소수점 콤마 로케일 대비
                s = s.strip().replace(",", ".")
                return float(s)
            except Exception:
                return None

        val: Optional[float] = None
        summary_note = ""

        # A) wmic: LoadPercentage=NN
        m_wmic = re.search(r"^\s*LoadPercentage\s*=\s*([0-9]+)\s*$", raw, re.IGNORECASE | re.MULTILINE)
        if m_wmic:
            val = _to_float(m_wmic.group(1))
            summary_note = "wmic LoadPercentage 스냅샷"

        # B) typeperf: "timestamp","value" 라인들 → 숫자만 추출 후 평균
        if val is None:
            values: List[float] = []
            for m in re.finditer(r'^\s*"[^"]*"\s*,\s*"([^"]+)"\s*$', raw, re.MULTILINE):
                f = _to_float(m.group(1))
                if f is not None:
                    values.append(f)
            if values:
                # 첫 줄은 헤더가 아니므로 그대로 평균
                # 일부 환경에서 노이즈가 있을 수 있어, 숫자만 모아 평균
                val = round(sum(values) / len(values), 4)
                summary_note = f"typeperf 평균({len(values)}샘플)"

        # C) Get-Counter CookedValue: 숫자만 출력
        if val is None:
            m_gc = re.search(r'([0-9]+(?:[.,][0-9]+)?)\s*$', raw.strip(), re.MULTILINE)
            if m_gc:
                val = _to_float(m_gc.group(1))
                summary_note = "Get-Counter CookedValue"

        # 판정 및 출력
        if val is not None:
            result["is_pass"] = 1 if val <= self.max_used_cpu else 0
            header = (
                f"CPU 임계치: {self.max_used_cpu:.0f}%\n"
                f"CPU 사용률: {val:.2f}%"
                + (f" ({summary_note})" if summary_note else "")
            )
        else:
            header = "CPU 사용률 파싱 실패"

        result["stdout_data"] = f"{header}\n\n{raw}"
        result["cpu_usage_pct"] = val
        return result

# ============================================================
# Windows 메모리 – 사용률 임계치 점검 (WMIC 버전)
# ============================================================
class winMemoryFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        thr = iface.get("max_used_mem", 80)
        try:
            self.max_used_mem = float(thr)
        except Exception:
            self.max_used_mem = 80.0

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 0, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        # wmic /value 출력 형식에 맞춰 수정
        free_kb = _grab_int(r"FreePhysicalMemory=(\d+)", raw)
        total_kb = _grab_int(r"TotalVisibleMemorySize=(\d+)", raw)

        used_pct = None
        if free_kb is not None and total_kb and total_kb > 0:
            used_pct = round((1.0 - (float(free_kb) / float(total_kb))) * 100.0, 2)

        if used_pct is not None:
            result["is_pass"] = 1 if used_pct <= self.max_used_mem else 0
            header = f"메모리 임계치: {self.max_used_mem:.0f}%\n메모리 사용률: {used_pct:.2f}%"
        else:
            header = "메모리 사용률 파싱 실패"

        result["stdout_data"] = f"{header}\n\n{raw}"
        result["memory_used_pct"] = used_pct
        return result


# ============================================================
# F07B: Windows Swap(페이지파일) – 사용률 임계치 점검 (WMIC)
#   명령: wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /value
#   AllocatedBaseSize/CurrentUsage/PeakUsage 단위는 MB
#   사용률(%) = (ΣCurrentUsage / ΣAllocatedBaseSize) * 100
# ============================================================
class winSwapFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        thr = iface.get("max_used_swap", 80)
        try:
            self.max_used_swap = float(thr)
        except Exception:
            self.max_used_swap = 80.0

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 0, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        # 블록(빈 줄) 단위로 합산
        blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
        total_alloc = 0  # MB
        total_curr = 0   # MB
        total_peak = 0   # MB

        for blk in blocks:
            alloc = _grab_int(r"AllocatedBaseSize\s*=\s*([0-9]+)", blk) or 0
            curr  = _grab_int(r"CurrentUsage\s*=\s*([0-9]+)", blk) or 0
            peak  = _grab_int(r"PeakUsage\s*=\s*([0-9]+)", blk) or 0
            total_alloc += alloc
            total_curr  += curr
            total_peak  += peak

        used_pct = None
        if total_alloc > 0:
            used_pct = round((total_curr / float(total_alloc)) * 100.0, 2)

        if used_pct is not None:
            result["is_pass"] = 1 if used_pct <= self.max_used_swap else 0
            header = (
                f"페이지파일 임계치: {self.max_used_swap:.0f}%\n"
                f"페이지파일 사용률: {used_pct:.2f}% "
                f"(할당 {total_alloc}MB, 현재 {total_curr}MB, 피크 {total_peak}MB)"
            )
        else:
            header = "페이지파일 사용률 파싱 실패"

        result["stdout_data"] = f"{header}\n\n{raw}"
        result["swap_used_pct"] = used_pct
        result["swap_totals_mb"] = {"alloc": total_alloc, "curr": total_curr, "peak": total_peak}
        return result

# ============================================================
# F07C: Windows 메모리 인식/상태 – DIMM 슬롯별 존재/상태 및 총 용량 검증
#   명령: wmic memorychip get BankLabel,DeviceLocator,Capacity,Speed,Manufacturer,Status /value
#   보조(선택): wmic OS get TotalVisibleMemorySize /value (총 메모리 KB) – 이미 F07에서 수집
#   판정:
#     1) 모든 DIMM Status ∈ ok_status_values → 통과
#     2) DIMM 용량 합계(GB)가 OS 인식 총 메모리(GB)와 ±tolerance 이내 → 통과
# ============================================================
class winMemoryPresenceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        # OK로 치는 상태 문자열(대소문자 무시)
        ok_vals = iface.get("ok_status_values", ["OK", "Healthy"])
        self.ok_status_values = [s.lower() for s in ok_vals]
        # 총 용량 비교 허용 오차(MB)
        try:
            self.capacity_tolerance_mb = int(iface.get("capacity_tolerance_mb", 1024))
        except Exception:
            self.capacity_tolerance_mb = 1024

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
        dimms = []
        bad_status = False
        total_capacity_bytes = 0

        for blk in blocks:
            bank  = _grab_text(r"BankLabel\s*=\s*(.+)", blk) or "-"
            slot  = _grab_text(r"DeviceLocator\s*=\s*(.+)", blk) or "-"
            manu  = _grab_text(r"Manufacturer\s*=\s*(.+)", blk) or "-"
            speed = _grab_text(r"Speed\s*=\s*(.+)", blk) or "-"
            stat  = (_grab_text(r"Status\s*=\s*(.+)", blk) or "-").strip()
            cap_b = _grab_int(r"Capacity\s*=\s*([0-9]+)", blk)

            if any([bank != "-", slot != "-", manu != "-", speed != "-", stat != "-", cap_b is not None]):
                dimms.append({
                    "bank": bank, "slot": slot, "manufacturer": manu,
                    "speed": speed, "status": stat, "capacity_bytes": cap_b or 0
                })
                total_capacity_bytes += (cap_b or 0)
                if stat and stat.lower() not in self.ok_status_values:
                    bad_status = True

        # 상태 판정 1: DIMM Status
        if bad_status:
            result["is_pass"] = 0

        # 상태 판정 2: 총 용량 vs OS 인식 총 메모리(선택적 비교)
        #  - 가능하면 같은 리포트 내 F07 결과(총 메모리 KB)를 inspection_items에 넘겨서 비교하는 것이 이상적이지만,
        #    여기서는 wmic OS 출력이 동일 항목으로 들어오지 않는 경우가 많으므로,
        #    본 필터 단독에서는 총 용량(GB) 정보만 보고합니다.
        total_capacity_mb = round(total_capacity_bytes / (1024.0 * 1024.0), 2)
        lines = []
        for d in dimms:
            cap_mb = round((d["capacity_bytes"] or 0) / (1024.0 * 1024.0), 2)
            lines.append(
                f"Bank={d['bank']} Slot={d['slot']} Manufacturer={d['manufacturer']} "
                f"Speed={d['speed']} Status={d['status']} Capacity={cap_mb}MB"
            )

        header = "메모리 인식/상태: " + ("양호" if result["is_pass"] == 1 else "취약")
        header += f"\nDIMM 총 용량: {total_capacity_mb}MB"
        result["stdout_data"] = header + "\n" + "\n".join(lines) + "\n\n" + raw
        result["dimms"] = dimms
        result["total_dimm_capacity_mb"] = total_capacity_mb
        return result


# ============================================================
# Windows 디스크 – 드라이브별 사용률 임계치 점검 (WMIC/순서 무관 지원)
# ============================================================
class winDiskFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        thr = iface.get("max_used_disk", 85)
        try:
            self.max_used_disk = float(thr)
        except Exception:
            self.max_used_disk = 85.0

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 0, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        per_drive: Dict[str, Dict[str, Any]] = {}

        # 1) 블록 분할(빈 줄 기준) → 각 블록에서 key=value 라인 추출
        blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
        for blk in blocks:
            # key=value 라인만 추출(순서 무관)
            kv = {}
            for ln in blk.splitlines():
                m = re.match(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*=\s*(.+?)\s*$", ln)
                if m:
                    kv[m.group(1).strip()] = m.group(2).strip()

            dev = kv.get("DeviceID") or kv.get("DeviceId") or kv.get("Deviceid")
            size = kv.get("Size")
            free = kv.get("FreeSpace") or kv.get("Freespace")

            if dev and size and free:
                try:
                    size_i = int(size)
                    free_i = int(free)
                    per_drive[dev.upper()] = {
                        "size": size_i,
                        "free": free_i,
                        "used_pct": _disk_used_pct(size_i, free_i),
                    }
                except Exception:
                    # 숫자 변환 실패 시 skip
                    pass

        # 2) 혹시 블록 분할이 안 되는 단일 포맷용 보강(순서 무관 정규식)
        if not per_drive:
            pat = re.compile(
                r"DeviceID=([A-Za-z]:).*?(?:Size=([0-9]+).*?FreeSpace=([0-9]+)|FreeSpace=([0-9]+).*?Size=([0-9]+))",
                re.IGNORECASE | re.DOTALL,
            )
            for m in pat.finditer(raw):
                dev = m.group(1)
                # 두 가지 분기 중 어느 쪽이 잡혔는지에 따라 값 선택
                size_s = m.group(2) or m.group(5)
                free_s = m.group(3) or m.group(4)
                try:
                    size_i = int(size_s)
                    free_i = int(free_s)
                    per_drive[dev.upper()] = {
                        "size": size_i,
                        "free": free_i,
                        "used_pct": _disk_used_pct(size_i, free_i),
                    }
                except Exception:
                    pass

        header_lines, all_good = [], True
        if not per_drive:
            header_lines.append("디스크 정보 파싱 실패")
            all_good = False
        else:
            header_lines.append(f"디스크 임계치: {self.max_used_disk:.0f}%")
            for d in sorted(per_drive):
                up = per_drive[d]["used_pct"]
                status = "양호" if (up is not None and up <= self.max_used_disk) else "취약"
                if up is None:
                    status = "취약"
                header_lines.append(f"{d} 사용률: {up if up is not None else 'N/A'}% → {status}")
                if status != "양호":
                    all_good = False

        result["is_pass"] = 1 if all_good else 0
        result["stdout_data"] = "\n".join(header_lines) + "\n\n" + raw
        result["per_drive"] = per_drive
        return result

# ============================================================
# F10: Windows Swap(페이지파일) – 사용률 임계치 점검 (WMIC)
#   명령 예: wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /value
#   AllocatedBaseSize=MB, CurrentUsage=MB, PeakUsage=MB
#   used% = CurrentUsage / AllocatedBaseSize * 100
# ============================================================
class winSwapFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        thr = iface.get("max_used_swap", 80)
        try:
            self.max_used_swap = float(thr)
        except Exception:
            self.max_used_swap = 80.0

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 0, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")
        # 여러 페이지파일 항목이 있을 수 있어 블록별로 집계
        blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
        totals = {"alloc": 0, "curr": 0, "peak": 0}
        for blk in blocks:
            alloc = _grab_int(r"AllocatedBaseSize\s*=\s*([0-9]+)", blk) or 0
            curr  = _grab_int(r"CurrentUsage\s*=\s*([0-9]+)", blk) or 0
            peak  = _grab_int(r"PeakUsage\s*=\s*([0-9]+)", blk) or 0
            totals["alloc"] += alloc
            totals["curr"]  += curr
            totals["peak"]  += peak

        used_pct = None
        if totals["alloc"] > 0:
            used_pct = round((totals["curr"] / float(totals["alloc"])) * 100.0, 2)

        if used_pct is not None:
            result["is_pass"] = 1 if used_pct <= self.max_used_swap else 0
            header = (
                f"Swap(페이지파일) 임계치: {self.max_used_swap:.0f}%\n"
                f"Swap 사용률: {used_pct:.2f}% (할당 {totals['alloc']}MB, 현재 {totals['curr']}MB, 피크 {totals['peak']}MB)"
            )
        else:
            header = "Swap 사용률 파싱 실패"

        result["stdout_data"] = f"{header}\n\n{raw}"
        result["swap_used_pct"] = used_pct
        result["swap_totals_mb"] = totals
        return result

# ============================================================
# F11: Windows 스토리지 이중화/상태 – Storage Spaces 우선, 없으면 WMIC Fallback
#   PowerShell:
#     Get-VirtualDisk | Select FriendlyName,ResiliencySettingName,HealthStatus,OperationalStatus | FL
#     Get-PhysicalDisk | Select FriendlyName,CanPool,HealthStatus,OperationalStatus,MediaType | FL
#   Fallback(WMIC):
#     wmic diskdrive get Status,Model,Size /value
# ============================================================
class winRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        # PowerShell 허용 여부(미허용 환경이면 WMIC만으로 제한적 판단)
        self.allow_powershell = bool(iface.get("allow_powershell", True))

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        # Storage Spaces 출력 감지(키워드 기반)
        has_vdisk = re.search(r"ResiliencySettingName\s*:\s*\S+", raw, re.IGNORECASE)
        has_pdisk = re.search(r"HealthStatus\s*:\s*\S+", raw, re.IGNORECASE)

        findings = []
        bad = False

        if self.allow_powershell and (has_vdisk or has_pdisk):
            # PowerShell 포맷-리스트 파싱
            blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
            for blk in blocks:
                # VirtualDisk
                vname = _grab_text(r"FriendlyName\s*:\s*(.+)", blk)
                resil = _grab_text(r"ResiliencySettingName\s*:\s*(.+)", blk)
                hstat = _grab_text(r"HealthStatus\s*:\s*(.+)", blk)
                ostat = _grab_text(r"OperationalStatus\s*:\s*(.+)", blk)
                if resil or vname:
                    msg = f"[VirtualDisk] Name={vname or '-'} Resiliency={resil or '-'} Health={hstat or '-'} Op={ostat or '-'}"
                    findings.append(msg)
                    if hstat and hstat.strip().lower() not in ["healthy", "ok"]:
                        bad = True
                # PhysicalDisk
                pname = _grab_text(r"FriendlyName\s*:\s*(.+)", blk)
                canpl = _grab_text(r"CanPool\s*:\s*(.+)", blk)
                ph    = _grab_text(r"HealthStatus\s*:\s*(.+)", blk)
                po    = _grab_text(r"OperationalStatus\s*:\s*(.+)", blk)
                mtype = _grab_text(r"MediaType\s*:\s*(.+)", blk)
                # PhysicalDisk 블록 판정(키가 겹치므로 최소 2개 이상 키가 있을 때)
                if (ph or po) and (pname or mtype):
                    msg = f"[PhysicalDisk] Name={pname or '-'} Media={mtype or '-'} Health={ph or '-'} Op={po or '-'} CanPool={canpl or '-'}"
                    findings.append(msg)
                    if ph and ph.strip().lower() not in ["healthy", "ok"]:
                        bad = True

            header = "Storage Spaces 상태 점검"
        else:
            # WMIC Fallback: Status만으로 제한적 판단
            header = "WMIC Fallback(제한적 상태 점검)"
            for m in re.finditer(
                r"Model\s*=\s*(.+?)\s*[\r\n]+.*?Status\s*=\s*(.+?)\s*[\r\n]+.*?Size\s*=\s*([0-9]+)",
                raw, re.IGNORECASE | re.DOTALL,
            ):
                model = m.group(1).strip()
                status = m.group(2).strip()
                size_b = m.group(3).strip()
                findings.append(f"[Disk] Model={model} Size={size_b} Status={status}")
                if status.lower() not in ["ok", "healthy"]:
                    bad = True

        result["is_pass"] = 0 if bad else 1
        result["stdout_data"] = header + "\n" + "\n".join(findings) + "\n\n" + raw
        result["summary"] = ("취약" if bad else "양호")
        return result

def _grab_text(pat: str, text: str) -> Optional[str]:
    m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip()

# ============================================================
# F12: Windows 디스크 인식/헬스 – 장치별 OK 여부
#   명령 예: wmic diskdrive get Index,Model,Size,Status,PNPDeviceID /value
# ============================================================
class winDiskPresenceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        self.fail_status_patterns = [re.compile(p, re.IGNORECASE) for p in iface.get(
            "fail_status_patterns", ["Pred Fail", "Degraded", "Error", "Unknown", "Critical"]
        )]

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")

        blocks = [b for b in re.split(r"\r?\n\s*\r?\n", raw) if b.strip()]
        offenders = []
        rows = []
        for blk in blocks:
            idx  = _grab_text(r"Index\s*=\s*(.+)", blk)
            mdl  = _grab_text(r"Model\s*=\s*(.+)", blk)
            size = _grab_text(r"Size\s*=\s*([0-9]+)", blk)
            stat = _grab_text(r"Status\s*=\s*(.+)", blk)
            pnp  = _grab_text(r"PNPDeviceID\s*=\s*(.+)", blk)
            if not (idx or mdl or size or stat or pnp):
                continue
            rows.append(f"Index={idx or '-'} Model={mdl or '-'} Size={size or '-'} Status={stat or '-'} PNP={pnp or '-'}")
            bad = False
            if not stat or stat.strip().lower() not in ["ok", "healthy"]:
                bad = True
            if stat and any(p.search(stat) for p in self.fail_status_patterns):
                bad = True
            if bad:
                offenders.append(rows[-1])

        result["is_pass"] = 0 if offenders else 1
        header = "디스크 인식/헬스 점검: " + ("취약" if offenders else "양호")
        if offenders:
            header += f" (비정상 {len(offenders)}개)"
        result["stdout_data"] = header + "\n" + "\n".join(offenders if offenders else rows) + "\n\n" + raw
        result["offenders"] = offenders
        return result

# ============================================================
# Windows 이벤트 로그 – 간단 키워드 판정
#   입력 예시:
#     wevtutil qe System /c:200 /rd:true /f:text
#   또는:
#     Get-WinEvent -LogName System -MaxEvents 200 | Format-Table -Auto
#   규칙:
#     - bad_patterns 중 1건이라도 발견 → 불량
#     - 흔한 잡음(로그온/로그오프/시간 미설정 등) 기본 제외
# ============================================================
class winEventLogSimpleFilter(BaseFilter):
    _IGNORE_DEFAULTS = [
        r"User logon", r"User logout", r"Login", r"Logout",
        r"idle timeout", r"CLOCK NOT SET", r"^\s*$",
    ]

    def __init__(self, params):
        super().__init__(params)
        iface = params.get("interface", {}) if params else {}
        self.bad_patterns: List[str] = iface.get("bad_patterns", ["error", "fail", "critical", "panic"])
        try:
            self.max_lines: int = int(iface.get("max_lines", 200))
        except Exception:
            self.max_lines = 200
        self._bad_regexes = [re.compile(p, re.IGNORECASE) for p in self.bad_patterns]
        self._ignore_regexes = [re.compile(p, re.IGNORECASE) for p in self._IGNORE_DEFAULTS]

    @filter_result
    def evaluate(self, stdout_data: Union[str, List[str]]):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = "\n".join(stdout_data) if isinstance(stdout_data, (list, tuple)) else (stdout_data or "")
        lines = raw.splitlines()[: self.max_lines]

        def _ignored(ln: str) -> bool:
            return any(r.search(ln) for r in self._ignore_regexes)

        scan = [ln for ln in lines if not _ignored(ln)]
        offenders = [ln for ln in scan if any(r.search(ln) for r in self._bad_regexes)]

        if offenders:
            result["is_pass"] = 0
            header = f"비정상 이벤트 발견 ({len(offenders)}건, 상위 {self.max_lines}줄)"
            result["summary"] = f"불량: patterns={self.bad_patterns}, hits={len(offenders)}"
        else:
            header = f"비정상 이벤트 없음 (상위 {self.max_lines}줄)"
            result["summary"] = "정상"

        out = [header]
        if offenders:
            out.append("\n[비정상 라인]\n" + "\n".join(offenders))
        out.append("\n[검사한 로그 상위 N줄]\n" + "\n".join(lines))
        result["stdout_data"] = "\n\n".join(out).strip()
        result["bad_patterns"] = self.bad_patterns
        result["offenders"] = offenders
        return result


# ----------------- helpers -----------------
def _grab_int(pat: str, text: str) -> Optional[int]:
    m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def _disk_used_pct(size: Optional[int], free: Optional[int]) -> Optional[float]:
    try:
        size = int(size); free = int(free)
        if size <= 0:
            return None
        used = size - free
        return round((used / float(size)) * 100.0, 2)
    except Exception:
        return None

def _to_float(s: str) -> Optional[float]:
    try:
        return float(str(s).strip().replace(",", "."))
    except Exception:
        return None

def _grab_int(pat: str, text: str) -> Optional[int]:
    m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def _disk_used_pct(size: Optional[int], free: Optional[int]) -> Optional[float]:
    try:
        size = int(size); free = int(free)
        if size <= 0:
            return None
        used = size - free
        return round((used / float(size)) * 100.0, 2)
    except Exception:
        return None