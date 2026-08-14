import sys
sys.path.insert(0, '/fap/ansible/projects/custom_modules/ansible_collections/fap/custom/plugins/modules/')
#sys.path.insert(0, '/fap/ansible/')  # rsc_parser 상위 디렉토리
from rsc_parser.base_parser import BaseParser
from rsc_parser.linux_parser import LinuxParser
from rsc_parser.unix_parser import UnixParser
from rsc_parser.windows_parser import WindowsParser

# ─────────────────────────────────────────────
# 로케일 경고 제거 함수
# ─────────────────────────────────────────────

def base_clean(lines):
    return BaseParser(lines)._clean(lines)


# ─────────────────────────────────────────────
# parser 매칭
# ─────────────────────────────────────────────

def parse_result(lines, os_type, key):
    parsers = {
        'linux': LinuxParser,
        'sunos': UnixParser,
        'hpux': UnixParser,
        'aix': UnixParser,
        'windows': WindowsParser
        
    }

    parser_cls = parsers.get(os_type.lower())
    if not parser_cls:
        return {}

    parser = parser_cls(lines)

    method_name = f"parse_{key}"
    if hasattr(parser, method_name):
        return getattr(parser, method_name)()
    else:
        return parser.fallback() # 해당 필터 없을 때(BaseParer에 정의)

def parse_combined_result(raw_dict, os_type):
    parsers = {
        'linux': LinuxParser,
        'sunos': UnixParser,
        'hpux': UnixParser,
        'aix': UnixParser,
        'windows': WindowsParser
    }

    parser_cls = parsers.get(os_type.lower())
    if not parser_cls:
        return {}

    result = {}
    for key, lines in raw_dict.items():
        try:
            parser = parser_cls(lines)
            method_name = f"parse_{key}"
            if hasattr(parser, method_name):
                result.update(getattr(parser, method_name)())
            else:
                result.update(parser.fallback())
        except Exception:
            continue
    return result


# ─────────────────────────────────────────────
#  통합 결과 분리
# ─────────────────────────────────────────────

def parse_sectioned_output(lines):
    result = {}
    current_key = None
    buffer = []

    for line in lines:
        if line.startswith("==="):
            if current_key:
                result[current_key] = buffer[:]
            current_key = line.strip("=").strip()
            buffer = []
        elif current_key:
            buffer.append(line.strip())

    if current_key:
        result[current_key] = buffer

    return result


# ─────────────────────────────────────────────
# 필터 등록부
# ─────────────────────────────────────────────

class FilterModule(object):
    def filters(self):
        return {
            'base_clean': base_clean,
            'parse_result' : parse_result,
            'parse_combined_result' : parse_combined_result,
            'parse_sectioned_output' : parse_sectioned_output
        }
    
