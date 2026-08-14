import re
from typing import List, Dict, Any, Union, Optional
from .base_filter import BaseFilter, filter_result




def _parse_wmic_blocks(text: str):
    """
    wmic pagefile ... /value 는 인스턴스가 여러 개면 블록 단위로 반복됨:
      AllocatedBaseSize=...
      CurrentUsage=...
      PeakUsage=...
      <blank>
      AllocatedBaseSize=...
      ...

    반환: list of dict
    """
    raw = _normalize_raw(text)
    lines = _split_lines(raw)
    blocks = []
    cur = {}
    for ln in lines + [""]:
        if not ln.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            cur[k.strip()] = v.strip()
    return blocks


def _normalize_raw(stdout_data: Union[str, List[str]]) -> str:
    if stdout_data is None:
        return ""
    if isinstance(stdout_data, (list, tuple)):
        stdout_data = "\n".join(str(x) for x in stdout_data)
    return str(stdout_data).replace("\r", "").strip("\n")


def _split_lines(raw: str) -> List[str]:
    raw = re.sub(r"\n\s*\n+", "\n", (raw or "").strip())
    return raw.splitlines() if raw else []


def _scan_lines(lines, bad_res, ignore_res):
    hits = []
    for ln in lines:
        if not ln.strip():
            continue
        if any(r.search(ln) for r in ignore_res):
            continue
        if any(r.search(ln) for r in bad_res):
            hits.append(ln)
    return hits



def _parse_percent(val: str) -> Optional[float]:
    """
    '12.3%' / '12.3' / '12,3%' -> float(12.3)
    %가 없는 값도 퍼센트로 간주 가능(출력이 % 없이 나오는 케이스 대비)
    """
    if not val:
        return None
    s = val.strip()
    s = s.replace(",", ".")
    s = s.replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


def _is_pid(val: str) -> bool:
    return bool(val) and val.strip().isdigit()


def _compile_patterns(pats):
    return [re.compile(p, re.IGNORECASE) for p in (pats or [])]



# (재사용) 보류 판단 함수
def _is_command_unavailable(text: str) -> bool:
    if not text:
        return True
    pat = re.compile(
        r"(not found|cannot execute|permission denied|access is denied|No such file|not recognized|typeperf.*error|invalid counter|specified object was not found|path.*not found)",
        re.IGNORECASE,
    )
    return bool(pat.search(text))


def _parse_typeperf_csv(text: str) -> Dict[str, List[float]]:
    """
    typeperf 출력(CSV)을 파싱해서 counter -> [values] 로 반환
    typeperf 예시:
      "(PDH-CSV 4.0)","\\HOST\\Processor(_Total)\\% User Time","\\HOST\\Processor(_Total)\\% Privileged Time",...
      "09/30/2025 10:10:01.123","12.345","3.210","84.445","0.100"
      ...
    """
    raw = _normalize_raw(text)
    lines = _split_lines(raw)
    if not lines:
        return {}

    # 헤더 라인 찾기: "(PDH-CSV" 포함
    header_idx = None
    for i, ln in enumerate(lines):
        if "PDH-CSV" in ln.upper():
            header_idx = i
            break
    if header_idx is None:
        return {}

    header = lines[header_idx]
    # CSV split: 간단히 "," 기준으로 자르되 따옴표 제거
    cols = [c.strip().strip('"') for c in header.split(",")]
    # cols[0]은 (PDH-CSV 4.0)
    counters = cols[1:]

    data_map = {c: [] for c in counters}

    for ln in lines[header_idx + 1 :]:
        # 데이터 라인: "date","v1","v2",...
        if not ln.strip().startswith('"'):
            continue
        parts = [p.strip().strip('"') for p in ln.split(",")]
        if len(parts) < 2:
            continue

        values = parts[1:]
        for j, c in enumerate(counters):
            if j >= len(values):
                continue
            v = values[j].replace(",", ".").strip()
            try:
                data_map[c].append(float(v))
            except Exception:
                # 숫자 파싱 실패는 무시(부분 데이터)
                pass

    return data_map


def _find_counter_key(data_map: Dict[str, List[float]], needle: str) -> Optional[str]:
    """
    counter 경로에서 특정 키워드(% User Time 등)를 포함하는 counter를 찾음(대소문자 무시)
    """
    n = needle.lower()
    for k in data_map.keys():
        if n in k.lower():
            return k
    return None


# 입력:
# typeperf "\Processor(_Total)\% User Time" "\Processor(_Total)\% Privileged Time" "\Processor(_Total)\% Idle Time" "\Processor(_Total)\% Interrupt Time" -sc 3 -si 1
#
# 출력(예시):
# "(PDH-CSV 4.0)","\\HOST\\Processor(_Total)\\% User Time","\\HOST\\Processor(_Total)\\% Privileged Time","\\HOST\\Processor(_Total)\\% Idle Time","\\HOST\\Processor(_Total)\\% Interrupt Time"
# "09/30/2025 10:10:01.123","12.34","3.21","84.45","0.10"
# "09/30/2025 10:10:02.123","13.10","3.00","83.50","0.20"
# "09/30/2025 10:10:03.123","11.90","2.80","85.10","0.10"
#
# ============================================================
# Windows_①-1 CPU 사용률 점검 (mpstat 대체)
# ============================================================
class winMpstatEquivalentCpuFilter(BaseFilter):
    """
    점검 목적:
      Linux mpstat의 핵심 지표를 Windows에서 대체 점검
      - usr + sys (User + Privileged) 합
      - idle (Idle Time)
      - irq+soft 대체 (Interrupt Time)
      - iowait: Windows에서 1:1 대응 불가(별도 Disk I/O 지표로 점검 권고)

    명령어(통상적/권장):
      typeperf "\Processor(_Total)\% User Time" "\Processor(_Total)\% Privileged Time" "\Processor(_Total)\% Idle Time" "\Processor(_Total)\% Interrupt Time" -sc 3 -si 1

    판정 기준(기본값, params/interface로 조정 가능):
      - (User% + Privileged%) <= MAX_USER_SYS_PCT  이면 양호 (기본 80)
      - Idle% >= MIN_IDLE_PCT 이면 양호 (기본 20)
      - Interrupt% <= MAX_IRQ_PCT 이면 양호 (기본 5)
      - 실패/권한/카운터 없음/파싱 실패 => 보류(is_pass=-1)

    버전/환경 주의:
      - typeperf는 대부분 Windows(Server 포함)에 기본 탑재
      - OS 언어가 한글인 경우 카운터 경로가 달라질 수 있음(그 경우 보류로 떨어짐)
    """

    DEFAULT_MAX_USER_SYS_PCT = 80.0
    DEFAULT_MIN_IDLE_PCT = 20.0
    DEFAULT_MAX_IRQ_PCT = 5.0

    def __init__(self, params):
        super().__init__(params)

        interface = params.get("interface") or {}
        # 네가 쓰던 yml 스타일과 호환되게
        self.max_user_sys = float(interface.get("max_user_sys_pct", self.DEFAULT_MAX_USER_SYS_PCT))
        self.min_idle = float(interface.get("min_idle_pct", self.DEFAULT_MIN_IDLE_PCT))
        self.max_irq = float(interface.get("max_irq_pct", self.DEFAULT_MAX_IRQ_PCT))

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        # 보류: 출력 없음
        if not raw.strip():
            result["is_pass"] = 0
            result["summary"] = (
                "❌ 명령 결과 없음\n"
                "typeperf 출력이 비어있어 점검할 수 없습니다."
            )
            return result

        # 보류: 실행 불가/카운터 오류
        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가 또는 카운터 오류\n"
                "typeperf 실행 불가/권한 문제/카운터 경로 오류로 점검할 수 없습니다.\n"
                "참고: OS 언어(한글/영문)에 따라 카운터 경로가 달라질 수 있습니다."
            )
            return result

        data_map = _parse_typeperf_csv(raw)
        if not data_map:
            result["is_pass"] = 0
            result["message"] = ( 
                "❌ 파싱 실패\n"
                "typeperf CSV 헤더/데이터를 파싱하지 못했습니다."
            )
            return result

        k_user = _find_counter_key(data_map, "% User Time")
        k_priv = _find_counter_key(data_map, "% Privileged Time")
        k_idle = _find_counter_key(data_map, "% Idle Time")
        k_intr = _find_counter_key(data_map, "% Interrupt Time")

        # 필수 키 최소 3개(User/Priv/Idle)는 있어야 판단 가능
        if not (k_user and k_priv and k_idle):
            result["is_pass"] = 0
            result["summary"] = (
                "❌ 필수 카운터 없음\n"
                "필요한 카운터(% User/Privileged/Idle)를 찾지 못했습니다.\n"
                "OS 언어가 한글이면 카운터 경로가 다를 수 있습니다."
            )
            return result

        user_vals = data_map.get(k_user, [])
        priv_vals = data_map.get(k_priv, [])
        idle_vals = data_map.get(k_idle, [])
        intr_vals = data_map.get(k_intr, []) if k_intr else []

        if not user_vals or not priv_vals or not idle_vals:
            result["is_pass"] = 0
            result["message"] = "보류: 샘플 값 부족\ntypeperf 샘플 값을 충분히 수집하지 못했습니다."
            return result

        # 평균값 사용(샘플 3회 평균)
        avg_user = round(sum(user_vals) / len(user_vals), 2)
        avg_priv = round(sum(priv_vals) / len(priv_vals), 2)
        avg_idle = round(sum(idle_vals) / len(idle_vals), 2)
        avg_intr = round(sum(intr_vals) / len(intr_vals), 2) if intr_vals else None

        user_sys = round(avg_user + avg_priv, 2)

        # 판정
        bad_reasons = []
        if user_sys > self.max_user_sys:
            bad_reasons.append(f"User+Priv={user_sys}% > {self.max_user_sys}%")
        if avg_idle < self.min_idle:
            bad_reasons.append(f"Idle={avg_idle}% < {self.min_idle}%")
        if avg_intr is not None and avg_intr > self.max_irq:
            bad_reasons.append(f"Interrupt={avg_intr}% > {self.max_irq}%")

        result["is_pass"] = 0 if bad_reasons else 1

        header = "❌ CPU 지표 임계치 초과" if bad_reasons else "✅ CPU 지표 정상"
        detail = []
 #        detail = [
 #            "\n",
 #            "[요약(평균)]",
 #            f"- %User(Time)      = {avg_user}%",
 #            f"- %Priv(Time)      = {avg_priv}%",
 #            f"- %User+%Priv       = {user_sys}% (기준 <= {self.max_user_sys}%)",
 #            f"- %Idle(Time)      = {avg_idle}% (기준 >= {self.min_idle}%)",
 #        ]
        if avg_intr is not None:
            detail.append(f"- %Interrupt(Time) = {avg_intr}% (기준 <= {self.max_irq}%)")
        else:
            detail.append("- %Interrupt(Time) = (미수집/파싱불가)")

        # detail.append("")
        # detail.append("[참고]")
        # detail.append("- Linux mpstat의 %iowait은 Windows에서 1:1 매핑이 어려워 Disk I/O 항목에서 별도 점검을 권고합니다.")

        if bad_reasons:
            detail.append("")
            detail.append("[불량 사유]")
            detail.extend(f"- {r}" for r in bad_reasons)

        result["message"] = "\n".join([header, *detail])
        return result


def _parse_wmic_pagefile_value(text: str) -> List[Dict[str, Any]]:
    """
    wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value
    여러 pagefile이 있으면 블록 단위로 반복됨.

    반환: [{"Name": "...", "AllocatedBaseSize": int, "CurrentUsage": int, "PeakUsage": int}, ...]
    """
    raw = _normalize_raw(text)
    lines = _split_lines(raw)

    blocks = []
    cur = {}
    for ln in lines + [""]:
        if not ln.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            cur[k.strip()] = v.strip()

    out = []
    for b in blocks:
        def _to_int(x):
            try:
                return int(str(x).strip())
            except Exception:
                return None

        out.append({
            "name": b.get("Name"),
            "allocated_mb": _to_int(b.get("AllocatedBaseSize")),
            "used_mb": _to_int(b.get("CurrentUsage")),
            "peak_mb": _to_int(b.get("PeakUsage")),
            "raw": b,
        })
    return out



def _parse_wmic_kv(text: str):
    """
    WMIC /value 출력 파싱:
      Key=Value
      Key=Value
    """
    raw = _normalize_raw(text)
    out = {}
    for ln in _split_lines(raw):
        if "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        out[k] = v
    return out


def _to_int(s: str):
    try:
        return int(str(s).strip())
    except Exception:
        return None


# 입력: wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value
#
# 출력(예시):
# FreePhysicalMemory=1234567
# TotalVisibleMemorySize=16777216
#
# 단위:
# - 위 값들은 KB 단위
#
# ============================================================
# Windows free -h 대체: 물리 메모리 사용/여유 점검
# ============================================================
class winFreeMemoryFilter(BaseFilter):
    """
    점검 목적:
      Linux free -h의 total/used/free/available 개념을 Windows에서 대체 점검

    명령어(가장 통상적):
      wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value

    판정 기준(기본값, interface로 조정):
      - (사용률) used_pct <= MAX_USED_MEM_PCT  (기본 80%)
      - (여유율) free_pct >= MIN_FREE_MEM_PCT  (기본 20%)
      - 명령 실행 불가/파싱 실패 => 보류(is_pass=-1)

    주의:
      - Linux available과 1:1 대응 불가 → FreePhysicalMemory를 보수적 가용치로 사용
      - WMIC는 일부 최신 Windows에서 제거/비권장일 수 있음(그 경우 보류)
    """

    DEFAULT_MAX_USED_MEM_PCT = 80.0
    DEFAULT_MIN_FREE_MEM_PCT = 20.0

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}
        self.max_used_pct = float(interface.get("max_used_mem", self.DEFAULT_MAX_USED_MEM_PCT))
        self.min_free_pct = float(interface.get("min_free_mem_pct", self.DEFAULT_MIN_FREE_MEM_PCT))

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "WMIC OS 출력이 비어있어 점검할 수 없습니다."
            )
            return result

        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "WMIC 실행 불가/권한/환경 문제로 점검할 수 없습니다.\n"
                "일부 최신 Windows에서는 WMIC가 제거/비권장일 수 있습니다."
            )
            return result

        kv = _parse_wmic_kv(raw)
        free_kb = _to_int(kv.get("FreePhysicalMemory"))
        total_kb = _to_int(kv.get("TotalVisibleMemorySize"))

        if free_kb is None or total_kb is None or total_kb <= 0:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 파싱 실패\n"
                "FreePhysicalMemory/TotalVisibleMemorySize 파싱에 실패했습니다."
            )
            return result

        used_kb = total_kb - free_kb
        used_pct = round((used_kb / total_kb) * 100.0, 2)
        free_pct = round((free_kb / total_kb) * 100.0, 2)

        bad = []
        if used_pct > self.max_used_pct:
            bad.append(f"메모리 사용률 {used_pct}% > {self.max_used_pct}%")
        if free_pct < self.min_free_pct:
            bad.append(f"가용 메모리 비율 {free_pct}% < {self.min_free_pct}%")

        result["is_pass"] = 0 if bad else 1

        header = "❌ 메모리 임계치 초과" if bad else "✅ 메모리 상태 양호"
 #        details = [ '\n',
 #            "[계산 결과]",
 #            f"- Total = {round(total_kb/1024/1024, 2)} GB",
 #            f"- Used  = {round(used_kb/1024/1024, 2)} GB ({used_pct}%)",
 #            f"- Free  = {round(free_kb/1024/1024, 2)} GB ({free_pct}%)",
 #            "",
 #            "[기준]",
 #            f"- Used% <= {self.max_used_pct}%",
 #            f"- Free% >= {self.min_free_pct}%",
 #        ]
        details = []
        if bad:
            details = [ 
                f"- Total = {round(total_kb/1024/1024, 2)} GB",
                f"- Used  = {round(used_kb/1024/1024, 2)} GB ({used_pct}%)",
                f"- Free  = {round(free_kb/1024/1024, 2)} GB ({free_pct}%)",
                "[기준]",
                f"- Used% <= {self.max_used_pct}%",
                f"- Free% >= {self.min_free_pct}%",
            ]

        result["message"] = "\n".join([header, *details])
        return result



# 입력: wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /value
#
# 출력(예시, 단위 MB):
# AllocatedBaseSize=4096
# CurrentUsage=512
# PeakUsage=1024
#
# ============================================================
# Windows free -h 대체: swap(페이지파일) 사용률 점검
# ============================================================
class winFreeSwapFilter(BaseFilter):
    """
    점검 목적:
      Linux free -h의 swap 사용률(%) 개념을 Windows 페이지파일로 대체 점검

    명령어(가장 통상적):
      wmic pagefile get AllocatedBaseSize,CurrentUsage,PeakUsage /value

    판정 기준(기본값):
      - swap_used_pct >= 50% 이면 불량 (Linux 기준 반영)
      - 파싱 실패/명령 불가 => 보류(is_pass=-1)

    주의:
      - AllocatedBaseSize/CurrentUsage 단위는 MB
      - 페이지파일이 여러 개면 합산해서 계산
      - 일부 최신 Windows에서는 WMIC 미지원 가능(보류)
    """

    DEFAULT_MAX_USED_SWAP_PCT = 50.0

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}
        # yml에서 max_used_swap을 쓰고 있으니 호환
        self.max_used_swap = float(interface.get("max_used_swap", self.DEFAULT_MAX_USED_SWAP_PCT))

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "WMIC pagefile 출력이 비어있어 점검할 수 없습니다."
            )
            return result

        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "WMIC 실행 불가/환경 문제로 점검할 수 없습니다.\n"
            )
            return result

        blocks = _parse_wmic_blocks(raw)
        if not blocks:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 파싱 실패\n"
                "pagefile 항목을 파싱하지 못했습니다."
            )
            return result

        total_alloc_mb = 0
        total_used_mb = 0

        for b in blocks:
            a = _to_int(b.get("AllocatedBaseSize"))
            u = _to_int(b.get("CurrentUsage"))
            if a is not None:
                total_alloc_mb += a
            if u is not None:
                total_used_mb += u

        if total_alloc_mb <= 0:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 값 부족\n"
                "AllocatedBaseSize 값을 확인할 수 없습니다."
            )
            return result

        used_pct = round((total_used_mb / total_alloc_mb) * 100.0, 2)
        ok = used_pct < self.max_used_swap
        result["is_pass"] = 1 if ok else 0

        header = "✅ 페이지파일 사용률 양호" if ok else "❌ 페이지파일 사용률 과다"
        details = []
        if not ok:
            details = [
                "[계산 결과]",
                f"- Total Allocated = {total_alloc_mb} MB",
                f"- Current Usage   = {total_used_mb} MB",
                f"- Used%           = {used_pct}% (기준 < {self.max_used_swap}%)",
            ]
        result["message"] = "\n".join([header, *details])
        return result





def _parse_wmic_pagefile_value(text: str) -> List[Dict[str, Any]]:
    """
    wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value
    여러 pagefile이 있으면 블록 단위로 반복됨.

    반환: [{"Name": "...", "AllocatedBaseSize": int, "CurrentUsage": int, "PeakUsage": int}, ...]
    """
    raw = _normalize_raw(text)
    lines = _split_lines(raw)

    blocks = []
    cur = {}
    for ln in lines + [""]:
        if not ln.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            cur[k.strip()] = v.strip()

    out = []
    for b in blocks:
        def _to_int(x):
            try:
                return int(str(x).strip())
            except Exception:
                return None

        out.append({
            "name": b.get("Name"),
            "allocated_mb": _to_int(b.get("AllocatedBaseSize")),
            "used_mb": _to_int(b.get("CurrentUsage")),
            "peak_mb": _to_int(b.get("PeakUsage")),
            "raw": b,
        })
    return out


# 입력: wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value
#
# 출력(예시):
# Name=C:\\pagefile.sys
# AllocatedBaseSize=4096
# CurrentUsage=512
# PeakUsage=1024
#
# ============================================================
# Windows_②-3 Paging Space(swapon -s) 대체 점검
# ============================================================
class winPagingSpaceFilter(BaseFilter):
    """
    점검 목적:
      Linux swapon -s (스왑 목록/크기/사용량) 을 Windows 페이지파일로 대체 점검

    명령어(가장 통상적):
      wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value

    판정 기준(기본):
      - pagefile 사용률(합산) >= 50% 이면 불량
      - pagefile 정보 파싱 실패/명령 실행 불가 => 보류(is_pass=-1)
      - pagefile이 0MB 또는 미존재로 판단되는 경우 => 보류(is_pass=-1) 권장
        (정책적으로 pagefile disabled 환경이 있을 수 있어 단정 불량을 피함)

    주의:
      - Size/Used 단위는 MB
      - Priority는 Windows에서 swapon처럼 노출되지 않음(미지원)
      - WMIC는 일부 최신 Windows에서 제거/비권장일 수 있음(그 경우 보류)
    """

    DEFAULT_MAX_USED_SWAP_PCT = 50.0

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}
        # 기존 yml 스타일과 맞추기
        self.max_used_swap = float(interface.get("max_used_swap", self.DEFAULT_MAX_USED_SWAP_PCT))

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        if not raw.strip():
            result["is_pass"] = -1
            result["summary"] = "보류: 명령 결과 없음"
            result["stdout_data"] = "보류: pagefile 출력이 비어있어 점검할 수 없습니다."
            return result

        if _is_command_unavailable(raw):
            result["is_pass"] = -1
            result["summary"] = "보류: 명령 실행 불가"
            result["stdout_data"] = (
                "보류: WMIC 실행 불가/권한/환경 문제로 점검할 수 없습니다.\n"
                "참고: 일부 최신 Windows에서는 WMIC가 제거/비권장일 수 있습니다.\n\n"
                "[원문]\n" + raw
            )
            return result

        items = _parse_wmic_pagefile_value(raw)
        if not items:
            result["is_pass"] = -1
            result["summary"] = "보류: 파싱 실패"
            result["stdout_data"] = "보류: pagefile 정보를 파싱하지 못했습니다.\n\n[원문]\n" + raw
            return result

        total_alloc = 0
        total_used = 0
        rows = []

        for it in items:
            name = it.get("name") or "(unknown)"
            alloc = it.get("allocated_mb")
            used = it.get("used_mb")
            peak = it.get("peak_mb")

            if alloc is not None:
                total_alloc += alloc
            if used is not None:
                total_used += used

            if alloc and alloc > 0 and used is not None:
                pct = round((used / alloc) * 100.0, 2)
            else:
                pct = None

            rows.append((name, alloc, used, peak, pct))

        # pagefile이 실제로 없는/0인 케이스는 환경 정책에 따라 달라서 보류 처리
        if total_alloc <= 0:
            result["is_pass"] = -1
            result["summary"] = "보류: 페이지파일 미설정/0MB"
            result["stdout_data"] = (
                "보류: AllocatedBaseSize 합계가 0MB로 확인되어 Paging Space를 평가할 수 없습니다.\n"
                "정책적으로 pagefile이 비활성화된 서버일 수 있으니 확인이 필요합니다.\n\n"
                "[원문]\n" + raw
            )
            return result

        used_pct = round((total_used / total_alloc) * 100.0, 2)
        ok = used_pct < self.max_used_swap
        result["is_pass"] = 1 if ok else 0

        header = "정상: Paging Space(페이지파일) 사용률 양호" if ok else "비정상: Paging Space(페이지파일) 사용률 과다"
        summary = [
            "[합산 요약]",
            f"- Total Allocated = {total_alloc} MB",
            f"- Total Used      = {total_used} MB",
            f"- Used%           = {used_pct}% (기준 < {self.max_used_swap}%)",
            "",
            "[상세(Pagefile)]",
        ]

        for (name, alloc, used, peak, pct) in rows:
            summary.append(
                f"- {name} | Size={alloc}MB, Used={used}MB, Peak={peak}MB, Used%={pct if pct is not None else 'N/A'}"
            )

        summary.append("")
        summary.append("[원문]")
        summary.append(raw)

        result["stdout_data"] = "\n".join([header, *summary])
        return result




def _parse_wmic_blocks_value(text: str) -> List[Dict[str, str]]:
    """
    wmic LogicalDisk ... /value 출력은 드라이브별로 블록 반복:
      DeviceID=C:
      FreeSpace=...
      Size=...
      <blank>
      DeviceID=D:
      ...
    """
    raw = _normalize_raw(text)
    lines = _split_lines(raw)

    blocks = []
    cur = {}
    for ln in lines + [""]:
        if not ln.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            cur[k.strip()] = v.strip()
    return blocks


def _to_int(s: str) -> Optional[int]:
    try:
        return int(str(s).strip())
    except Exception:
        return None


def _bytes_to_gb(b: int) -> float:
    return round(b / (1024 ** 3), 2)


# 입력: wmic LogicalDisk where "DriveType=3" get DeviceID,Size,FreeSpace /value
#
# 출력(예시, 단위 bytes):
# DeviceID=C:
# FreeSpace=1234567890
# Size=250000000000
#
# ============================================================
# Windows_③-1 파일시스템 사용량(df -h) 대체 점검
# ============================================================
class winFilesystemUsageFilter(BaseFilter):
    """
    점검 목적:
      Linux df -h 파일시스템 사용량 점검을 Windows 로컬 디스크(DriveType=3) 기준으로 대체

    명령어(가장 통상적):
      wmic LogicalDisk where "DriveType=3" get DeviceID,Size,FreeSpace /value

    판정 기준(기본, interface로 조정):
      - Use% >= 80% 이면 불량
      - Avail% (Free%) < 20% 이면 불량
      - 명령 실행 불가/파싱 실패 => 보류(is_pass=-1)

    주의:
      - Windows는 "Mounted on"을 리눅스처럼 경로로 제공하지 않고 드라이브(예: C:) 단위로 제공됨.
      - WMIC는 일부 최신 Windows에서 제거/비권장일 수 있음(그 경우 보류)
    """

    DEFAULT_MAX_USED_PCT = 80.0     # Use% 80% 이상 불량
    DEFAULT_MIN_FREE_PCT = 20.0     # Free% 20% 미만 불량

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}
        self.max_used_pct = float(interface.get("max_used_disk", self.DEFAULT_MAX_USED_PCT))
        self.min_free_pct = float(interface.get("min_free_disk_pct", self.DEFAULT_MIN_FREE_PCT))

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "LogicalDisk 출력이 비어있어 점검할 수 없습니다."
            )
            return result

        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "WMIC 실행 불가/권한/환경 문제로 점검할 수 없습니다."
            )
            return result

        blocks = _parse_wmic_blocks_value(raw)
        if not blocks:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 파싱 실패\n"
                "드라이브 정보를 파싱하지 못했습니다."
            )
            return result

        drives = []
        for b in blocks:
            dev = b.get("DeviceID")
            size = _to_int(b.get("Size"))
            free = _to_int(b.get("FreeSpace"))
            if not dev or size is None or free is None or size <= 0:
                continue

            used = size - free
            used_pct = round((used / size) * 100.0, 2)
            free_pct = round((free / size) * 100.0, 2)

            drives.append({
                "dev": dev,
                "size": size,
                "free": free,
                "used": used,
                "used_pct": used_pct,
                "free_pct": free_pct,
            })

        if not drives:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 유효 드라이브 없음"
                "파싱 가능한 로컬 디스크(DriveType=3) 정보가 없습니다."
            )
            return result

        offenders = []
        for d in drives:
            if d["used_pct"] >= self.max_used_pct or d["free_pct"] < self.min_free_pct:
                offenders.append(d)

        result["is_pass"] = 0 if offenders else 1

        header = "❌ 디스크 사용률/가용공간 임계치 초과" if offenders else "✅ 디스크 사용량 양호"
        lines = [header]
        
        if offenders:
            #lines = ["[불량 드라이브]"]
            for d in offenders:
                lines.append(
                    f"- {d['dev']} (Used%={d['used_pct']}%, Free%={d['free_pct']}%)"
                )



        lines += [
            "[기준]",
            f"- Use% >= {self.max_used_pct}% 이면 불량",
            f"- Free%(Avail) < {self.min_free_pct}% 이면 불량",
        ]

 #        for d in drives:
 #            lines.append(
 #                f"- {d['dev']} | Size={_bytes_to_gb(d['size'])}GB, "
 #                f"Free={_bytes_to_gb(d['free'])}GB({d['free_pct']}%), "
 #                f"Used={_bytes_to_gb(d['used'])}GB({d['used_pct']}%)"
 #            )

#        lines += ["", "[원문]", raw]
        result["message"] = "\n".join(lines)
        return result


# 입력: wmic pagefile get Name,AllocatedBaseSize,CurrentUsage,PeakUsage /value
#
# 출력(예시, MB):
# Name=C:\\pagefile.sys
# AllocatedBaseSize=4096
# CurrentUsage=512
# PeakUsage=1024
#
# ============================================================
# ③-2 Disk Swap 사용률 (Windows Pagefile 기반) 점검
# ============================================================
class winDiskSwapUsageFilter(BaseFilter):
    """
    점검 목적:
      Linux swapon -s 의 swap Size/Used 확인을 Windows Pagefile로 대체 점검

    판정 기준(기본):
      - (합산) pagefile 사용률(Used/Size) >= 50% 이면 불량
      - 명령 실행 불가/파싱 실패/출력 없음 => 보류 처리
      - pagefile Size 합계가 0MB 이면(미설정/정책) 보류 처리

    비고:
      - Priority는 Windows에서 swapon -s 처럼 제공되지 않음
      - WMIC는 일부 최신 Windows에서 미제공/비활성일 수 있음
    """

    DEFAULT_MAX_USED_SWAP_PCT = 50.0

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}
        self.max_used_swap = float(interface.get("max_used_swap", self.DEFAULT_MAX_USED_SWAP_PCT))

    def _parse_wmic_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        wmic ... /value 형태: 항목 블록이 빈줄로 구분됨
        """
        raw = _normalize_raw(text)
        lines = _split_lines(raw)

        blocks = []
        cur = {}
        for ln in lines + [""]:
            if not ln.strip():
                if cur:
                    blocks.append(cur)
                    cur = {}
                continue
            if "=" in ln:
                k, v = ln.split("=", 1)
                cur[k.strip()] = v.strip()
        return blocks

    def _to_int(self, s: Optional[str]) -> Optional[int]:
        try:
            return int(str(s).strip())
        except Exception:
            return None

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}
        raw = _normalize_raw(stdout_data)

        # 보류 1) 출력 없음
        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "출력이 비어있어 점검할 수 없습니다."
            )
            return result

        # 보류 2) 실행 불가/명령 미존재 등 (재사용 함수)
        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "명령 실행 불가/환경 문제로 점검할 수 없습니다.\n"
            )
            return result

        blocks = self._parse_wmic_blocks(raw)
        if not blocks:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 파싱 실패\n"
                "pagefile 정보를 파싱하지 못했습니다."
            )
            return result

        items = []
        total_alloc = 0
        total_used = 0

        for b in blocks:
            name = b.get("Name") or "(unknown)"
            alloc = self._to_int(b.get("AllocatedBaseSize"))  # MB
            used = self._to_int(b.get("CurrentUsage"))        # MB
            peak = self._to_int(b.get("PeakUsage"))           # MB

            # 일부 환경은 값이 비거나 누락될 수 있음
            if alloc is None and used is None and peak is None:
                continue

            if alloc is not None:
                total_alloc += alloc
            if used is not None:
                total_used += used

            pct = None
            free_mb = None
            if alloc is not None and alloc > 0 and used is not None:
                pct = round((used / alloc) * 100.0, 2)
                free_mb = alloc - used

            items.append({
                "name": name,
                "alloc_mb": alloc,
                "used_mb": used,
                "peak_mb": peak,
                "used_pct": pct,
                "free_mb": free_mb,
            })

        # pagefile이 사실상 없거나 0MB면 판단 유보
        if total_alloc <= 0:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 페이지파일 미설정/0MB\n"
                "AllocatedBaseSize 합계가 0MB로 확인되어 Swap 사용률을 평가할 수 없습니다."
            )
            return result

        total_pct = round((total_used / total_alloc) * 100.0, 2)
        total_free = total_alloc - total_used

        ok = total_pct < self.max_used_swap
        result["is_pass"] = 1 if ok else 0

        header = "✅ Disk Swap(Pagefile) 사용률 양호" if ok else "❌ Disk Swap(Pagefile) 사용률 과다"
        rep = [header]
        if not ok:
           for it in items:
                rep.append(
                f"- {it['name']} | Size={it['alloc_mb']}MB, Used={it['used_mb']}MB, "
                f"Free={it['free_mb']}MB, Used%={it['used_pct']}%, Peak={it['peak_mb']}MB"
                )    
                rep += [
                    "[판정 기준]",
                    f"- 합산 Used% >= {self.max_used_swap}% 이면 불량",
                ]
    

#        rep += ["", "[원문]", raw]
        result["message"] = "\n".join(rep)
        return result


import re
from .base_filter import BaseFilter, filter_result

# ============================================================
# (재사용 전제)
# - _is_command_unavailable(text: str) -> bool
# - _normalize_raw(stdout_data) -> str
# - _split_lines(raw: str) -> List[str]
# - _compile_patterns(pats) -> List[Pattern]
# - _scan_lines(lines, bad_res, ignore_res) -> List[str]
# ============================================================


class _winEventLogGrepBaseFilter(BaseFilter):
    """
    Windows wevtutil 출력(text)에서 패턴 매칭으로 이상 징후를 찾는 공통 베이스
    """
    TITLE = "Windows 이벤트 로그"
    BAD_PATTERNS = []
    IGNORE_PATTERNS = []
    MAX_LINES = 2500  # 이벤트 몇 개만 보더라도 라인이 길어질 수 있어 넉넉히

    def __init__(self, params):
        super().__init__(params)

        interface = params.get("interface") or {}
        bad = interface.get("bad_patterns") or self.BAD_PATTERNS
        ign = interface.get("ignore_patterns") or self.IGNORE_PATTERNS

        self.bad_res = _compile_patterns(bad)
        self.ignore_res = _compile_patterns(ign)

        try:
            self.max_lines = int(interface.get("max_lines", self.MAX_LINES))
        except Exception:
            self.max_lines = self.MAX_LINES

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}

        raw = _normalize_raw(stdout_data)

        # 보류 1) 출력 없음
        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "출력이 비어있어 점검할 수 없습니다."
            )
            return result

        # 보류 2) 실행 불가/권한/채널 없음 등
        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "명령 실행 불가/권한/채널 미존재 등의 사유로 점검할 수 없습니다.\n"
            )
            return result

        # 패턴 미설정이면 보류
        if not self.bad_res:
            result["is_pass"] = 0
            result["message"] = (
                "❌ 패턴 미설정\n"
                "bad_patterns가 비어있어 점검할 수 없습니다."
            )
            return result

        lines = _split_lines(raw)
        scan = lines[-self.max_lines :] if len(lines) > self.max_lines else lines

        hits = _scan_lines(scan, self.bad_res, self.ignore_res)
        
        body = ""

        if hits:
            result["is_pass"] = 0
            header = f"❌: {self.TITLE} 이상 징후 감지 ({len(hits)}건)"
            body = ( 
                "[판정]\n"
                "- bad_patterns 매칭 시 불량"
                + "\n".join(hits[:200])
            )
        else:
            header = f"✅ {self.TITLE} 이상 징후 없음"

        result["message"] = "\n".join([
            header,
            body
        ])
        return result


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.1 시스템 로그 점검 (dmesg 대체)
# ============================================================
class winLogSystemAnomalyFilter(_winEventLogGrepBaseFilter):
    TITLE = "시스템 로그"
    BAD_PATTERNS = [
        # 레벨(로케일 대응: Level/레벨, Error/오류, Warning/경고)
        r"^\s*(Level|레벨)\s*:\s*(Error|오류|Warning|경고)\b",

        # 커널/하드웨어
        r"\bhardware\s+error\b",
        r"\bmachine\s+check\b|\bmachine\s+check\s+exception\b|\bMCE\b",

        # 디스크/파일시스템
        r"\bi/o\s+error\b",
        r"\bcorrupt\b",
        r"\bntfs\b.*\b(error|corrupt)\b",
        r"\bdisk\b.*\b(error|failed|failure)\b",

        # 메모리
        r"\bout\s+of\s+memory\b",
        r"\bmemory\s+leak\b",

        # 드라이버/모듈
        r"\bdriver\b.*\bfailed\b",
        r"\bmodule\b.*\bfailed\b",

        # 네트워크
        r"\bnetwork\b.*\b(error|failed|failure|timeout)\b",
        r"\btimeout\b.*\b(connection|request|device)\b",
        r"\bconnection\b.*\b(reset|failed|lost|timed\s*out)\b",

        # 서비스/데몬
        r"\bservice\b.*\b(failed|failure|terminated|stopped)\b",
        r"\bdaemon\b.*\bfailed\b",

        # 보안
        r"\bsecurity\b.*\b(error|failed|unauthorized)\b",
        r"\bunauthorized\b",
        r"\baccess\s+denied\b",
    ]


# 입력: wevtutil qe System /c:200 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.2 커널 패닉(Windows: BugCheck/Unexpected reboot) 점검
# ============================================================
class winLogKernelPanicFilter(_winEventLogGrepBaseFilter):
    TITLE = "커널 패닉/비정상 재부팅"
    BAD_PATTERNS = [
        # Bugcheck/Stop 계열
        r"\bBugCheck\b",
        r"\bThe\s+computer\s+has\s+rebooted\s+from\s+a\s+bugcheck\b",
        r"\bSTOP\b|\bStop\s+code\b|\bBlue\s+Screen\b",

        # 대표 이벤트 ID (표기 라인에 Event ID: 가 나오는 케이스)
        r"^\s*Event\s+ID\s*:\s*(41|1001)\b",

        # Kernel-Power(41) 등
        r"\bKernel-Power\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.3 CPU 로그 (ECC/Uncorrectable/Offline 유사) 점검
# ============================================================
class winLogCpuEccErrorFilter(_winEventLogGrepBaseFilter):
    TITLE = "CPU(ECC/WHEA) 로그"
    BAD_PATTERNS = [
        r"\bWHEA-Logger\b",
        r"\bMachine\s+Check\b|\bMachine\s+Check\s+Exception\b|\bMCE\b",
        r"\buncorrectable\b",
        r"\bprocessor\b.*\berror\b|\bCPU\b.*\berror\b",
        r"\bprocessor\b.*\b(disabled|offline)\b|\b(disabled|offline)\b.*\bprocessor\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.4 MEMORY 로그 (single/multi/uncorrectable ECC) 점검
# ============================================================
class winLogMemoryEccErrorFilter(_winEventLogGrepBaseFilter):
    TITLE = "메모리(ECC) 로그"
    BAD_PATTERNS = [
        r"\bMemoryDiagnostics-Results\b",
        r"\bWHEA-Logger\b",
        r"\bECC\b",
        r"\bsingle[-\s]?bit\b",
        r"\bmulti[-\s]?bit\b",
        r"\buncorrectable\b",
        r"\bmemory\b.*\b(error|fault|fail|failed)\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.5 FAN 로그 점검
# ============================================================
class winLogFanFailFilter(_winEventLogGrepBaseFilter):
    TITLE = "FAN 로그"
    BAD_PATTERNS = [
        r"\bfan\b.*\b(fail|failed|failure)\b",
        r"\bfan\b.*\bspeed\b.*\blow\b",
        r"\bover[-\s]?temp(?:erature)?\b",
        r"\boverheat\b",
        r"\bthermal\b.*\b(error|fail|failed)\b",
    ]
    IGNORE_PATTERNS = [
        r"\boperating\s+normally\b",
        r"\bnormal\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.6 POWER(PSU) 로그 점검
# ============================================================
class winLogPowerPsuFailFilter(_winEventLogGrepBaseFilter):
    TITLE = "전원(PSU) 로그"
    BAD_PATTERNS = [
        r"\bpsu\b.*\b(fail|failed|failure)\b",
        r"\bpower\s+supply\b.*\b(fail|failed|failure)\b",
        r"\bpower\b.*\b(fail|failed|failure)\b",
        r"\bKernel-Power\b",  # 전원 이슈/비정상 종료에 자주 등장
    ]
    IGNORE_PATTERNS = [
        r"\boperating\s+normally\b",
        r"\bnormal\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.7 HBA 로그 점검 (StorPort/FC/HBA)
# ============================================================
class winLogHbaAnomalyFilter(_winEventLogGrepBaseFilter):
    TITLE = "HBA/스토리지 경로 로그"
    BAD_PATTERNS = [
        r"\bhba\b",
        r"\b(fibre|fiber)\s+channel\b",
        r"\bstorport\b.*\b(error|reset|failed|timeout)\b",
        r"\bport\b.*\b(offline|failed|error)\b|\b(offline|failed|error)\b.*\bport\b",
        r"\bloop\b",
    ]
    IGNORE_PATTERNS = [
        r"\bport\b.*\bonline\b|\bonline\b.*\bport\b",
        r"\bcompleted\s+successfully\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.8 NIC 로그 점검 (Link Down/Failover 등)
# ============================================================
class winLogNicAnomalyFilter(_winEventLogGrepBaseFilter):
    TITLE = "NIC/네트워크 로그"
    BAD_PATTERNS = [
        r"\blink\s+(?:is\s+)?down\b",
        r"\bmedia\s+disconnected\b",
        r"\bNDIS\b.*\b(disconnect|disconnected|reset|failed|error)\b",
        r"\btcpip\b.*\b(error|failed|reset)\b",
        r"\bfailover\b",
        r"\bteaming\b.*\b(degrad|fail|failed|error)\b",
    ]
    IGNORE_PATTERNS = [
        r"\blink\s+(?:is\s+)?up\b",
        r"\bstatus\s+up\b",
    ]


# 입력: wevtutil qe System /c:500 /rd:true /f:text
# 출력: System 이벤트 로그 텍스트(최근 N개)
# ============================================================
# ⑤.9 I/O 에러 로그 점검 (Timeout/I/O error/Transport/Media)
# ============================================================
class winLogIoErrorFilter(_winEventLogGrepBaseFilter):
    TITLE = "I/O 에러 로그"
    BAD_PATTERNS = [
        r"\bi/o\b.*\berror\b",
        r"\btimeout\b",
        r"\btransport\b.*\bfailed\b",
        r"\bmedia\b.*\berror\b",
        r"\breset\s+to\s+device\b",
        r"\bhas\s+a\s+bad\s+block\b",
        r"\bDisk\b.*\b(error|failed|failure)\b",
        r"\bNTFS\b.*\b(error|corrupt)\b",
        r"\bstorport\b.*\b(error|reset|timeout|failed)\b",
    ]


# 입력: wevtutil qe Microsoft-Windows-FailoverClustering/Operational /c:300 /rd:true /f:text
# 출력: Failover Clustering 운영 로그 텍스트(최근 N개)
# ============================================================
# ⑤.10 클러스터 로그 점검 (Windows Failover Clustering)
# ============================================================
class winLogClusterStatusChangeFilter(_winEventLogGrepBaseFilter):
    TITLE = "클러스터(상태변경) 로그"
    BAD_PATTERNS = [
        r"\bcluster\b.*\berror\b",
        r"\bresource\b.*\bstatus\b",
        r"\bstatus\s+change\b",
        r"\bnode\b.*\b(offline|down|unknown)\b",
        r"\bresource\b.*\b(offline|unknown)\b|\b(offline|unknown)\b.*\bresource\b",
    ]
    IGNORE_PATTERNS = [
        r"\bresource\b.*\bonline\b|\bonline\b.*\bresource\b",
        r"\bnode\b.*\bonline\b|\bonline\b.*\bnode\b",
    ]



# 입력: cmd /c "echo ===NETSH=== & netsh interface show interface & echo ===WMIC=== & wmic nic where (PhysicalAdapter=True) get Name,NetEnabled,Speed /format:list"
#
# 출력(예):
# ===NETSH===
# Admin State    State          Type             Interface Name
# -------------------------------------------------------------------------
# Enabled        Connected      Dedicated        Ethernet
# Enabled        Disconnected   Dedicated        Ethernet 2
# Enabled        Connected      Loopback         Loopback Pseudo-Interface 1
# ===WMIC===
# Name=Intel(R) Ethernet Connection
# NetEnabled=TRUE
# Speed=1000000000
#
# ============================================================
# ⑦-1 NW 링크 상태/연결속도 점검 (Windows)
# ============================================================
class winNicLinkStateSpeedFilter(BaseFilter):
    """
    점검 목적:
      NIC별 링크 상태(Up/Down/Unknown) 및 속도(Speed) 확인

    명령어(권장):
      cmd /c "echo ===NETSH=== & netsh interface show interface & echo ===WMIC=== & wmic nic where (PhysicalAdapter=True) get Name,NetEnabled,Speed /format:list"

    판정:
      - (netsh 기준) Dedicated NIC가 Connected가 아니면 불량
      - Connected인데 속도(Speed)가 0/미확인이면 불량
      - 명령 실행 불가/권한/출력 없음이면 보류(is_pass=-1)
    """

    # netsh 출력에서 제외할 인터페이스(가상/터널/루프백 등) 기본 패턴
    IGNORE_IFNAME_PATTERNS = [
        r"loopback",
        r"teredo",
        r"isatap",
        r"tunnel",
        r"pseudo",
        r"virtual",
        r"vmware",
        r"hyper-v",
        r"bluetooth",
    ]

    def __init__(self, params):
        super().__init__(params)
        interface = params.get("interface") or {}

        # 최소 속도(Mbps) 옵션 (미설정 시 체크 안 함)
        self.min_speed_mbps = interface.get("min_speed_mbps")
        try:
            self.min_speed_mbps = float(self.min_speed_mbps) if self.min_speed_mbps is not None else None
        except Exception:
            self.min_speed_mbps = None

        pats = interface.get("ignore_ifname_patterns") or self.IGNORE_IFNAME_PATTERNS
        self._ignore_if_res = [re.compile(p, re.IGNORECASE) for p in pats]

    def _is_ignored_if(self, name: str) -> bool:
        if not name:
            return True
        return any(r.search(name) for r in self._ignore_if_res)

    def _bps_to_mbps(self, bps_val):
        try:
            bps = float(str(bps_val).strip())
            if bps <= 0:
                return None
            return round(bps / 1_000_000.0, 1)
        except Exception:
            return None

    def _parse_netsh(self, lines):
        """
        netsh interface show interface 테이블 파싱
        return: list[{name, admin, state, type}]
        """
        items = []
        header_idx = None
        for i, ln in enumerate(lines):
            if re.search(r"\bAdmin\s+State\b", ln) and re.search(r"\bInterface\s+Name\b", ln):
                header_idx = i
                break
        if header_idx is None:
            return items

        # 헤더 다음 구분선 이후부터 데이터
        data = lines[header_idx + 1 :]
        # 구분선(----) 이후부터 시작하는 경우가 많음
        for j, ln in enumerate(data):
            if re.match(r"^\s*-{3,}\s*$", ln):
                data = data[j + 1 :]
                break

        for ln in data:
            if not ln.strip():
                continue
            # 열이 고정폭이라 공백 다수로 split (3개까지만)
            parts = re.split(r"\s{2,}", ln.strip(), maxsplit=3)
            # 기대: Admin State / State / Type / Interface Name
            if len(parts) < 4:
                continue
            admin, state, itype, name = parts[0], parts[1], parts[2], parts[3]
            items.append({"admin": admin, "state": state, "type": itype, "name": name, "raw": ln})
        return items

    def _parse_wmic_blocks(self, lines):
        """
        wmic /format:list 블록 파싱
        return: dict[name_lower -> {Name, NetEnabled, Speed}]
        """
        blocks = []
        cur = {}
        for ln in lines:
            s = ln.strip()
            if not s:
                if cur:
                    blocks.append(cur)
                    cur = {}
                continue
            if "=" in s:
                k, v = s.split("=", 1)
                cur[k.strip()] = v.strip()
        if cur:
            blocks.append(cur)

        out = {}
        for b in blocks:
            name = (b.get("Name") or "").strip()
            if not name:
                continue
            out[name.lower()] = {
                "Name": name,
                "NetEnabled": (b.get("NetEnabled") or "").strip(),
                "Speed": (b.get("Speed") or "").strip(),
            }
        return out

    @filter_result
    def evaluate(self, stdout_data):
        result = {"is_pass": 1, "inspection_criteria": self.inspection_criteria}

        raw = _normalize_raw(stdout_data)

        # 보류: 출력 없음
        if not raw.strip():
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 결과 없음\n"
                "출력이 비어있어 점검할 수 없습니다."
            )
            return result

        # 보류: 실행 불가/권한/미지원
        if _is_command_unavailable(raw):
            result["is_pass"] = 0
            result["message"] = (
                "❌ 명령 실행 불가\n"
                "명령 실행 불가/권한/미지원 등의 사유로 점검할 수 없습니다."
            )
            return result

        lines = _split_lines(raw)

        # 섹션 분리(마커가 없을 수도 있어 전체 lines로도 동작)
        netsh_lines = []
        wmic_lines = []
        mode = "ALL"
        for ln in lines:
            if "===NETSH===" in ln:
                mode = "NETSH"
                continue
            if "===WMIC===" in ln:
                mode = "WMIC"
                continue
            if mode == "NETSH":
                netsh_lines.append(ln)
            elif mode == "WMIC":
                wmic_lines.append(ln)
            else:
                # 마커가 없으면 둘 다 후보로 둠
                netsh_lines.append(ln)
                wmic_lines.append(ln)

        net_items = self._parse_netsh(netsh_lines)
        wmic_map = self._parse_wmic_blocks(wmic_lines)
        
        sp_mbps = None
        bad = False 
        name = None
        offenders = []
        goods = []
        reasons = []
        bads = []
        for key,value in wmic_map.items():
          name = value.get('Name', None)
          sp_mbps = self._bps_to_mbps(value.get('Speed', None))
         # UP인데 속도 미확인/0이면 불량
          if sp_mbps is None:
              bad = True
              reasons.append(f"Physical Driver{name} SPEED=미확인/0")
          # 최소 속도 기준 옵션(설정 시)
          if self.min_speed_mbps is not None and sp_mbps is not None:
              if sp_mbps < self.min_speed_mbps:
                  bad = True
                  reasons.append(f" SPEED({sp_mbps}Mbps)가 기준 스피드({self.min_speed_mbps})Mbps보다 낮습니다.(불량)")
          if bad == False and self.min_speed_mbps != None:
            reasons.append(f"속도 SPEED({sp_mbps}Mbps)가 기준 스피드({self.min_speed_mbps})Mbps보다 높습니다.(양호)")          
          if bad:
              bads.append((name, reasons)) 
          else:
              goods.append((name,reasons))

         

        # netsh 기반 판정(가장 신뢰)
        checked = []
        
        for it in net_items:
            name = it["name"]
            if self._is_ignored_if(name):
                continue

            # Dedicated NIC만 우선(“Dedicated”가 아니면 체크 제외)
            # (원하면 interface 옵션으로 확장 가능)
            if str(it.get("type", "")).lower() != "dedicated":
                continue

            st = str(it.get("state", "")).strip().lower()
            # Windows 상태 -> Up/Down/Unknown 매핑
            if st == "connected":
                updown = "UP"
            elif st == "disconnected":
                updown = "DOWN"
            else:
                updown = "UNKNOWN"

            # # 속도 매칭(이름이 완벽히 일치하진 않을 수 있어 포함매칭 fallback)
            # sp_mbps = None
            # netenabled = None

            # # key = name.lower()
            # # if key in wmic_map:
            # netenabled = wmic_map[key].get("NetEnabled")
            # sp_mbps = self._bps_to_mbps(wmic_map[key].get("Speed"))
            # else:
            #     # fallback: wmic Name에 netsh Interface Name이 포함되는지
            #     for k, v in wmic_map.items():
            #         if key and key in k:
            #             netenabled = v.get("NetEnabled")
            #             sp_mbps = self._bps_to_mbps(v.get("Speed"))
            #             break

            checked.append({
                "name": name,
                "state": it.get("state"),
                "mapped": updown,
                # "speed_mbps": sp_mbps,
                # "netenabled": netenabled,
                "raw": it.get("raw"),
            })

            bad = False
            reasons = []

            if updown != "UP":
                bad = True
                reasons.append(f"Interface {name} STATE={updown}")

            # UP인데 속도 미확인/0이면 불량
            # if updown == "UP" and sp_mbps is None:
            #     bad = True
            #     reasons.append("SPEED=미확인/0")

            # 최소 속도 기준 옵션(설정 시)
            # if updown == "UP" and self.min_speed_mbps is not None and sp_mbps is not None:
            #     if sp_mbps < self.min_speed_mbps:
            #         bad = True
            #         reasons.append(f"SPEED<{self.min_speed_mbps}Mbps")

            if bad:
                offenders.append((name, reasons))

        # netsh 파싱 자체가 안 되면 보류(명령 출력은 있으나 형식 불명)
        if not checked:
            result["is_pass"] = 0
            result["summary"] = (
                "❌ NIC 정보 파싱 불가\n"
                "netsh/wmic 출력에서 NIC 상태 정보를 파싱하지 못했습니다.\n"
            )
            return result

        if offenders:
            header = f"❌ NIC 링크/속도 이상 감지 ({len(offenders)}개)"
        else:
            header = f"✅ NIC 링크/속도 이상 없음 ({len(checked)}개)"

        # 리포트 구성
        lines_out = [header, "", "[확인 결과]"]
        for c in checked:
            # sp = f"{c['speed_mbps']}Mbps" if c["speed_mbps"] is not None else "N/A"
            lines_out.append(f"- {c['name']}: {c['mapped']} (raw={c['state']})")

        if offenders or bads:
            result["is_pass"] = 0
            try: 
              lines_out += ["", "[이상 status]"]
              for name, reasons in offenders:
                  lines_out.append(f"- {name}: " + ", ".join(reasons))
            except:
              pass
            try:
              for name, reasons in bads:
                  lines_out.append(f"- {name}: " + ", ".join(reasons))
            except:
              pass

        #lines_out += ["", "[원문]", raw]
        result["message"] = "\n".join(lines_out)
        return result
