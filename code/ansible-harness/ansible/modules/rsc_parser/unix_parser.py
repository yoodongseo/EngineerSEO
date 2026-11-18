from .base_parser import BaseParser
import re

class UnixParser(BaseParser):

    def parse_os_info(self):
        expected_keys = ["os_name", "os_version", "kernel", "os_type"]
        result = {k: "" for k in expected_keys}
        
        for line in self.lines:
            if "=" not in line:
                continue 
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
            if k in result:
                result[k] = v

        return result
    

    def parse_df_lines(self):
        lines = self.lines

        result = []

        # os_type 판단(aix의 경우 헤더가 다르기 때문에 분기)
        header = next((line for line in lines if 'Filesystem' in line), '')
        if 'Iused' in header:
            os_type = 'aix'
        else:
            os_type = 'common'
        
        def strip_unit(value):
            return ''.join(filter(str.isdigit, value))

        if os_type == 'aix':
            for line in lines[1:]:
                parts = re.split(r'\s+', line.strip())
                if len(parts) < 7:
                    continue
                    
                try:
                    filesystem = parts[0]
                    total = int(parts[1]) if parts[1].isdigit() else 0
                    free = int(parts[2]) if parts[2].isdigit() else 0
                    used = total - free
                    mounted = parts[-1]

                    size = f"{total // 1024}M"
                    used = f"{used // 1024}M"
                    avail = f"{free // 1024}M"

                except Exception:
                    size = used = avail = "0M"
                    mounted = "?"

                result.append({
                    'filesystem': filesystem,
                    'size': size,
                    'used': used,
                    'avail': avail,
                    'mounted': mounted
                })

        else: # common UNIX
            for line in lines[1:]:
                parts = line.split()
                if len(parts) < 6:
                    continue

                try:
                    filesystem = parts[0]
                    total = int(strip_unit(parts[1]))
                    used = int(strip_unit(parts[2]))
                    free = int(strip_unit(parts[3]))
                    mounted = parts[-1]

                    size = f"{total // 1024}M"
                    used_str = f"{used // 1024}M"
                    avail = f"{free // 1024}M"
                except (ValueError, IndexError):
                    size = used_str = avail = "0M"
                    mounted = "?"

                result.append({
                    "filesystem": filesystem,
                    "size": size,
                    "used": used_str,
                    "avail": avail,
                    "mounted": mounted
                })

        return {"disk_list": result}
    

    def parse_disk_size(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
            value = None
        return {"disk_size": value}
    

    def parse_uptime(self):
        """
        Extracts and trims the 'up ...' uptime string from uptime output.
        Returns:
          String like 'up 3 days, 4:13'
        """
        if not self.lines:
            return ""

        line = self.lines[0]
        match = re.search(r'^.*?up\s+[^,]+,', line)
        if not match:
            return ""

        return {"uptime": match.group(0).rstrip(",").strip()}
    

    def parse_cpu(self):
        try:
            # 첫 줄에서 float 파싱 → 예: ["48.5"] → 48.5
            value = float(self.lines[0])
        except (ValueError, IndexError):
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
        return {"user_list":self.lines}


    def parse_service_list(self):
        try:
            parsed = self.extract_json_lines()
        except Exception:
            parsed = []

        return {"service_list": parsed}
    

    def parse_package_list(self):
        """
        예시:
          {"name": "bash", "version": "4.4.20", "release": "2.el8", "epoch": null, "arch": "x86_64", "source": "rpm"}
        """
        # print("[DEBUG] Lines to parse:")
        # for i in self.lines:
        #     print(i)
        try:
            package_list = self.extract_json_lines()
        except Exception:
            return {"package_list": []}

        # dpkg인 경우 후처리
        if package_list and package_list[0].get("source") == "dpkg":
            package_list = self._dpkg_parse_version(package_list)

        return {"package_list": package_list}
    

    def _dpkg_parse_version(self, package_list):
        parsed = []
        for pkg in package_list:
            if not isinstance(pkg, dict):
                continue

            version = pkg.get("version", "")
            epoch = pkg.get("epoch", None)
            release = pkg.get("release", "-")

            if ":" in version:
                epoch, version = version.split(":", 1)
            if "-" in version:
                version, release = version.rsplit("-", 1)

            new_pkg = pkg.copy()
            new_pkg.update({
                "epoch": epoch,
                "version": version,
                "release": release
            })
            parsed.append(new_pkg)
        return parsed
