from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.base_parser import BaseParser
from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.linux_parser import LinuxParser
from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.unix_parser import UnixParser
from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.windows_parser import WindowsParser
from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.cisco_parser import CiscoParser
from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.arista_parser import AristaParser
# from ansible_collections.fap.custom.plugins.module_utils.rsc_parser.citrix_parser import CitrixParser

# ─────────────────────────────────────────────
# 로케일 경고 제거 함수
# ─────────────────────────────────────────────

def base_clean(lines):
    return BaseParser(lines)._clean(lines)


# ─────────────────────────────────────────────
# parser 매칭
# ─────────────────────────────────────────────

# def parse_result(lines, os_type, key):
#     parsers = {
#         'linux': LinuxParser,
#         'sunos': UnixParser,
#         'hpux': UnixParser,
#         'aix': UnixParser,
#         'windows': WindowsParser
        
#     }

#     parser_cls = parsers.get(os_type.lower())
#     if not parser_cls:
#         return {}

#     parser = parser_cls(lines)

#     method_name = f"parse_{key}"
#     if hasattr(parser, method_name):
#         return getattr(parser, method_name)()
#     else:
#         return parser.fallback() # 해당 필터 없을 때(BaseParer에 정의)


def parse_combined_result(raw_dict, os_type):
    parsers = {
        'linux': LinuxParser,
        'sunos': UnixParser,
        'hpux': UnixParser,
        'aix': UnixParser,
        'windows': WindowsParser,
        'cisco': CiscoParser,
        'arista': AristaParser,
        'citrix': CitrixParser,
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

def parse_sectioned_output(lines, os_type=None):
    if os_type in ["cisco", "arista", "citrix"]:
        return {
            "os_info": lines
        }
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
            # 'parse_result' : parse_result,
            'parse_combined_result' : parse_combined_result,
            'parse_sectioned_output' : parse_sectioned_output
        }