from .base_parser import BaseParser
import re
import csv
from io import StringIO

class WindowsParser(BaseParser):

    def _clean(self, lines):
        if isinstance(lines, str):
            lines = lines.replace('\r', '').split('\n')

        return [l.strip() for l in lines if l.strip() and "setlocale" not in l.lower()]

    def parse_os_info(self):
        result = dict.fromkeys(["os_name", "os_type", "os_version", "kernel"], "")

        for line in self.lines:
            parts = line.split("|")
            if len(parts) == 4:
                keys = list(result.keys())
                for i in range(4):
                    result[keys[i]] = parts[i].strip()
                break  # 첫 줄만 쓰고 종료
        return result

    def parse_df_lines(self):
        result = []

        if not self.lines or len(self.lines) < 2:
            return result

        reader = csv.DictReader(StringIO("\n".join(self.lines)))

        for row in reader:
            try:
                size = int(row["Size"])
                free = int(row["SizeRemaining"])
                used = size - free
                label = row["FileSystemLabel"].strip()
                fs_type = row["FileSystem"].strip()

                filesystem = f"{label}({fs_type})" if label else fs_type

                result.append({
                    "filesystem": filesystem,
                    "size": f"{size // (1024 * 1024)}M",
                    "used": f"{used // (1024 * 1024)}M",
                    "avail": f"{free // (1024 * 1024)}M",
                    "mounted": row["DriveLetter"] or "-"
                })
            except (KeyError, ValueError):
                continue

        return {"disk_list": result}
    

    def parse_disk_size(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
            value = None
        return {"disk_size": value}
    

    def parse_uptime(self):
        if not self.lines:
            return {"uptime": ""}

        return {"uptime": self.lines[0].strip()}
    

    def parse_cpu(self):
        try:
            value_line = next((line for line in self.lines if line.strip().isdigit()), None)
            value = float(value_line) if value_line else None
        except Exception:
            value = None
        return {"cpu": value}


    def parse_cpu_cores(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
            value = None
        return {"cpu_cores": value}


    def parse_memory(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
            value = None
        return {"memory": value}       


    def parse_memory_size(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
            value = None
        return {"memory_size": value}
    
    
    def parse_user_list(self):
        if not self.lines:
            return {"user_list": []}

        users = [line.strip() for line in self.lines if line.strip()]
        return {"user_list": users}


    def parse_service_list(self):

        result = []

        for line in self.lines:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                result.append({
                    "name": parts[0],
                    "status": parts[1],
                    "source": parts[2],
                    "state": parts[3]
                })

        return {"service_list": result}
        

    def parse_package_list(self):
        fallback = False
        result = []
        for line in self.lines:
            parts = [p.strip() for p in line.strip().split('|')]
            if fallback:
                if len(parts) >= 2:
                    result.append({
                        "name": parts[0],
                        "version": parts[1],
                        "release": parts[2] if len(parts) > 2 else "unknown",
                        "source": None
                    })
            else:
                if len(parts) == 4:
                    result.append({
                        "name": parts[0],
                        "version": parts[1],
                        "release": parts[2],
                        "source": parts[3] or None
                    })
        return {"package_list": result}
