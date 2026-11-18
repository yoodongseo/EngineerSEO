from .base_parser import BaseParser
import re

class CiscoParser(BaseParser):
    def _is_invalid_output(self):
        text = "\n".join(self.lines).lower()
        invalid_markers = (
            "% invalid input",
            "% incomplete command",
            "% ambiguous command",
            "unknown command",
            "authorization failed",
            "command authorization failed",
        )
        return any(marker in text for marker in invalid_markers)

    def _size_to_mb(self, value, unit="", default_unit="K"):
        try:
            number = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

        unit = (unit or default_unit or "").strip().lower()
        if unit.endswith("bytes"):
            unit = unit[:-5]
        if unit.endswith("byte"):
            unit = unit[:-4]
        if unit.endswith("b") and unit != "b":
            unit = unit[:-1]

        multipliers = {
            "": 1 / 1024,
            "k": 1 / 1024,
            "m": 1,
            "g": 1024,
            "t": 1024 * 1024,
            "b": 1 / (1024 * 1024),
        }
        value_mb = number * multipliers.get(unit, 1 / 1024)
        return int(value_mb) if value_mb.is_integer() else round(value_mb, 2)

    def _format_mb(self, value):
        if value is None:
            return "0M"
        return f"{int(value) if float(value).is_integer() else round(value, 2)}M"

    def _parse_memory_size(self, lines):
        # IOS-XE often exposes this as a dedicated total memory line.
        for line in lines:
            m = re.search(r'([\d,]+)\s*([KMGTP]?)\s+bytes\s+of\s+physical\s+memory\b', line, re.I)
            if m:
                return self._size_to_mb(m.group(1), m.group(2), default_unit="B")

        # NX-OS commonly prints "Memory: 16402536 kB".
        for line in lines:
            m = re.search(r'\bMemory:\s*([\d,]+)\s*([KMGTP]?B?)\b', line, re.I)
            if m:
                return self._size_to_mb(m.group(1), m.group(2))

        # IOS/IOS-XE model lines commonly split processor and I/O memory.
        for line in lines:
            m = re.search(r'\bwith\s+([\d,]+)\s*K/([\d,]+)\s*K\s+bytes\s+of\s+memory\b', line, re.I)
            if m:
                total_kb = float(m.group(1).replace(",", "")) + float(m.group(2).replace(",", ""))
                return self._size_to_mb(total_kb, "K")

        # NX-OS model lines commonly use "with 32801472 kB of memory".
        for line in lines:
            m = re.search(r'\bwith\s+([\d,]+)\s*([KMGTP]?B?)\s+of\s+memory\b', line, re.I)
            if m:
                return self._size_to_mb(m.group(1), m.group(2))

        for line in lines:
            m = re.search(r'\bwith\s+([\d,]+)\s*([KMGTP]?)\s+bytes\s+of\s+memory\b', line, re.I)
            if m:
                return self._size_to_mb(m.group(1), m.group(2), default_unit="B")

        return None

    def _memory_from_lines(self, lines):
        total_bytes = 0
        used_bytes = 0

        for line in lines:
            m = re.search(
                r'\b(?:Processor|I/O|Driver|Transient|System)\s+Pool\s+Total:\s*([\d,]+)\s+Used:\s*([\d,]+)\s+Free:\s*([\d,]+)',
                line,
                re.I,
            )
            if m:
                total_bytes += int(m.group(1).replace(",", ""))
                used_bytes += int(m.group(2).replace(",", ""))
                continue

            m = re.search(
                r'^\s*(?:Processor|I/O|Driver|Transient|System)\s+\S+\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\b',
                line,
                re.I,
            )
            if m:
                total_bytes += int(m.group(1).replace(",", ""))
                used_bytes += int(m.group(2).replace(",", ""))

        if total_bytes:
            return {
                "memory": round((used_bytes / total_bytes) * 100, 2),
            }

        return {}

    def _system_resources_from_lines(self, lines):
        result = {}
        full_text = "\n".join(lines)

        m = re.search(r'CPU states\s*:\s*(.+)', full_text, re.I)
        if m:
            cpu_line = m.group(1)
            idle = re.search(r'([\d.]+)%\s*idle', cpu_line, re.I)
            if idle:
                result["cpu"] = round(100 - float(idle.group(1)), 2)
            else:
                parts = [float(v) for v in re.findall(r'([\d.]+)%', cpu_line)]
                if parts:
                    result["cpu"] = round(sum(parts), 2)

        m = re.search(
            r'Memory usage:\s*([\d,]+)\s*([KMGTP]?B?)\s+total,\s*([\d,]+)\s*([KMGTP]?B?)\s+used',
            full_text,
            re.I,
        )
        if m:
            total_mb = self._size_to_mb(m.group(1), m.group(2))
            used_mb = self._size_to_mb(m.group(3), m.group(4))
            if total_mb:
                result["memory_size"] = total_mb
                result["memory"] = round((used_mb / total_mb) * 100, 2)

        return result

    def _parse_disk_size(self, lines):
        disk_sizes = []

        for line in lines:
            stripped = line.strip()

            # NX-OS/ACI format: "bootflash: 115805708 kB"
            m = re.search(r'^(?:bootflash|flash|slot0|sup-bootflash|usbflash\d*):\s*([\d,]+)\s*([KMGTP]?B?)\b', stripped, re.I)
            if m:
                size_mb = self._size_to_mb(m.group(1), m.group(2))
                if size_mb:
                    disk_sizes.append(size_mb)
                continue

            # IOS/IOS-XE format: "11264000K bytes of Flash at flash:."
            m = re.search(r'^([\d,]+)\s*([KMGTP]?)\s+bytes\s+of\s+(.+)$', stripped, re.I)
            if not m:
                continue

            description = m.group(3).lower()
            storage_keywords = ("flash", "compactflash", "bootflash", "usb flash")
            if any(keyword in description for keyword in storage_keywords):
                size_mb = self._size_to_mb(m.group(1), m.group(2), default_unit="B")
                if size_mb:
                    disk_sizes.append(size_mb)

        if not disk_sizes:
            return None

        total_mb = sum(disk_sizes)
        return int(total_mb) if float(total_mb).is_integer() else round(total_mb, 2)

    def parse_df_lines(self):
        if self._is_invalid_output():
            return {"disk_list": []}

        disk_list = []
        disk_size = 0
        storage_keywords = ("flash", "bootflash", "sup-bootflash", "slot", "usbflash", "compactflash", "disk")

        for line in self.lines:
            stripped = line.strip()
            if not stripped or "Size(b)" in stripped or "File Systems" in stripped:
                continue

            m = re.search(
                r'^\*?\s*([\d,]+)\s+([\d,]+)\s+(\S+)\s+(\S+)\s+(.+)$',
                stripped,
                re.I,
            )
            if not m:
                continue

            size_b = int(m.group(1).replace(",", ""))
            free_b = int(m.group(2).replace(",", ""))
            fs_type = m.group(3)
            prefixes = m.group(5).strip()
            prefix_name = prefixes.split()[0] if prefixes else fs_type

            if not any(keyword in prefixes.lower() or keyword in fs_type.lower() for keyword in storage_keywords):
                continue

            size_mb = self._size_to_mb(size_b, "B")
            avail_mb = self._size_to_mb(free_b, "B")
            used_mb = self._size_to_mb(size_b - free_b, "B")
            disk_size += size_mb or 0

            disk_list.append({
                "filesystem": prefix_name.rstrip(":"),
                "size": self._format_mb(size_mb),
                "used": self._format_mb(used_mb),
                "avail": self._format_mb(avail_mb),
                "mounted": prefixes,
            })

        result = {"disk_list": disk_list}
        if disk_list:
            result["disk_size"] = int(disk_size) if float(disk_size).is_integer() else round(disk_size, 2)
        return result

    def parse_cpu(self):
        if self._is_invalid_output():
            return {}

        full_text = "\n".join(self.lines)
        m = re.search(r'CPU utilization for five seconds:\s*([\d.]+)%', full_text, re.I)
        if m:
            return {"cpu": float(m.group(1))}

        result = self._system_resources_from_lines(self.lines)
        return {"cpu": result["cpu"]} if "cpu" in result else {}

    def parse_memory(self):
        if self._is_invalid_output():
            return {}

        result = self._memory_from_lines(self.lines)
        if result:
            return result

        return self._system_resources_from_lines(self.lines)

    def parse_system_resources(self):
        if self._is_invalid_output():
            return {}
        return self._system_resources_from_lines(self.lines)

    def parse_user_list(self):
        if self._is_invalid_output():
            return {"user_list": []}

        users = []
        seen = set()
        for line in self.lines:
            m = re.search(r'^\s*username\s+(\S+)\b', line, re.I)
            if not m:
                continue
            username = m.group(1).strip()
            if username not in seen:
                seen.add(username)
                users.append(username)

        return {"user_list": users}

    def parse_service_list(self):
        if self._is_invalid_output():
            return {"service_list": []}

        services = []
        seen = set()

        def add_service(name, line, state="enabled", status="enabled"):
            key = (name, state)
            if key in seen:
                return
            seen.add(key)
            services.append({
                "name": name,
                "status": status,
                "source": "running-config",
                "state": state,
            })

        for line in self.lines:
            stripped = line.strip()
            lower = stripped.lower()
            if not stripped:
                continue

            disabled = lower.startswith("no ")
            normalized = lower[3:] if disabled else lower
            state = "disabled" if disabled else "enabled"

            if normalized.startswith("ip http secure-server"):
                add_service("https", stripped, state)
            elif normalized.startswith("ip http server"):
                add_service("http", stripped, state)
            elif normalized.startswith("ip ssh") or normalized.startswith("feature ssh"):
                add_service("ssh", stripped, state)
            elif normalized.startswith("snmp-server"):
                add_service("snmp", stripped, state)
            elif normalized.startswith("ntp server"):
                add_service("ntp", stripped, state)
            elif normalized.startswith("logging host"):
                add_service("syslog", stripped, state)
            elif normalized.startswith("aaa new-model"):
                add_service("aaa", stripped, state)
            elif normalized.startswith("transport input"):
                protocols = stripped.split()[2:]
                for protocol in protocols:
                    add_service(protocol, stripped, state)

        return {"service_list": services}

    def parse_os_info(self):
        result = {
            "os_name": "",
            "os_version": "",
            "kernel": "",
            "os_type": "",
            "uptime": "",
            "memory_size": None,
            "disk_size": None
        }

        full_text = "\n".join(self.lines)

        # -------------------------------------------------
        # 1. 모델명 → os_name
        # -------------------------------------------------
        model = ""

        lines = full_text.splitlines()

        # Hardware 블록 (NXOS / ACI)
        for i, line in enumerate(lines):
            if line.strip().lower() == "hardware":
                if i + 1 < len(lines):
                    model = lines[i + 1].strip()
                break

        # fallback (IOS-XE Router)
        if not model:
            for line in lines:
                if line.strip().lower().startswith("cisco ") and "processor" in line.lower():
                    model = line.strip()
                    break
                
        if model:
            model = model.split(" processor")[0]
            model = model.split(" with ")[0]

        result["os_name"] = model if model else "cisco"

        # -------------------------------------------------
        # 2. OS 타입
        # -------------------------------------------------
        if "controller" in full_text and "Pod" in full_text:
            result["os_name"] = "ACI-APIC"
            result["os_type"] = "ACI-APIC"

        elif "Cisco Nexus Operating System" in full_text:
            # result["os_name"] = "NX-OS"
            result["os_type"] = "NX-OS"

        elif "Cisco IOS XE Software" in full_text:
            # result["os_name"] = "IOS-XE"
            result["os_type"] = "IOS-XE"

        elif "Cisco IOS Software" in full_text:
            # result["os_name"] = "IOS"
            result["os_type"] = "IOS"

        else:
            # result["os_name"] = "cisco"
            result["os_type"] = "cisco"

        # -------------------------------------------------
        # 3. Version (우선순위 중요)
        # -------------------------------------------------
        version = ""

        # 1. NX-OS standalone
        m = re.search(r'NXOS:\s+version\s+([^\s]+)', full_text)
        if m:
            version = m.group(1)

        # 2. ACI (leaf + spine) → system version
        if not version:
            m = re.search(r'\bsystem:\s+version\s+([^\s]+)', full_text)
            if m:
                version = m.group(1)

        # 3. IOS-XE
        if not version:
            m = re.search(r'Cisco IOS XE Software,\s+Version\s+([^\s,]+)', full_text)
            if m:
                version = m.group(1)

        # 4. APIC
        if not version:
            m = re.search(r'controller\s+\d+\s+\d+\s+\S+\s+([^\s]+)', full_text)
            if m:
                version = m.group(1)

        # 5. fallback (IOS)
        if not version:
            m = re.search(r'Version\s+([^\s,]+)', full_text)
            if m:
                version = m.group(1)

        version = version.strip()
        result["os_version"] = version
        result["kernel"] = version

        # -------------------------------------------------
        # 4. Uptime
        # -------------------------------------------------
        uptime = ""

        # NX-OS / ACI (leaf + spine)
        m = re.search(r'Kernel uptime is (.+)', full_text)
        if m:
            uptime = m.group(1)

        # IOS / IOS-XE
        if not uptime:
            m = re.search(r'uptime is (.+)', full_text)
            if m:
                uptime = m.group(1)

        result["uptime"] = uptime.strip()
        result["memory_size"] = self._parse_memory_size(lines)
        result["disk_size"] = self._parse_disk_size(lines)

        return result
