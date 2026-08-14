from .base_parser import BaseParser
import re

class AristaParser(BaseParser):
    def parse_os_info(self):
        result = {
            "os_name": "",
            "os_version": "",
            "kernel": "",
            "os_type": "",
            "uptime": ""
        }

        full_text = "\n".join(self.lines)

        # -------------------------------------------------
        # 1. 모델명 → os_name
        # -------------------------------------------------
        m = re.search(r'Arista\s+(\S+)', full_text)
        if m:
            result["os_name"] = m.group(1)
        else:
            result["os_name"] = "Arista"

        # os_type은 그대로 유지
        result["os_type"] = "Arista"

        # -------------------------------------------------
        # 2. Version
        # -------------------------------------------------
        version = ""
        m = re.search(r'Software image version:\s+([^\s]+)', full_text)
        if m:
            version = m.group(1)

        version = version.strip()
        result["os_version"] = version
        result["kernel"] = version

        # -------------------------------------------------
        # 3. Uptime
        # -------------------------------------------------
        uptime = ""
        m = re.search(r'Uptime:\s+(.+)', full_text)
        if m:
            uptime = m.group(1)

        result["uptime"] = uptime.strip()

        return result