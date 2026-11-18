import re


def normalize_os(value):
    return str(value or "").strip().lower().replace("_", "").replace("-", "")


def result(is_pass, criteria_text, detail_lines):
    return {
        "is_success": 1,
        "is_pass": 1 if is_pass else 0,
        "check_target": criteria_text,
        "criteria_items": [criteria_text],
        "judgement_text": "기준 이내" if is_pass else "기준 초과",
        "detail_lines": detail_lines or ["점검 대상 이상 항목 미검출"],
    }


def split_marker_sections(raw):
    sections = {}
    current = "default"
    sections[current] = []
    for line in (raw or "").splitlines():
        stripped = line.strip()
        marker = re.match(r"^=+\s*([A-Z0-9_ -]+)\s*=+$", stripped)
        if marker:
            current = marker.group(1).strip().upper().replace(" ", "_")
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def parse_passwd(raw):
    accounts = {}
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        parts = stripped.split(":")
        if len(parts) < 7:
            continue
        accounts[parts[0]] = {
            "name": parts[0],
            "uid": safe_int(parts[2]),
            "gid": parts[3],
            "comment": parts[4],
            "home": parts[5],
            "shell": parts[6],
        }
    return accounts


def parse_shadow(raw):
    shadow = {}
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        parts = stripped.split(":")
        if len(parts) < 2:
            continue
        shadow[parts[0]] = {
            "name": parts[0],
            "password": parts[1],
            "max_days": safe_int(parts[4]) if len(parts) > 4 else None,
        }
    return shadow


def account_locked(account, shadow):
    shell = str((account or {}).get("shell") or "").strip().lower()
    if shell in ("/sbin/nologin", "/usr/sbin/nologin", "/bin/false", "/usr/bin/false", "nologin", "false"):
        return True
    password = str((shadow or {}).get((account or {}).get("name"), {}).get("password") or "")
    return password.startswith(("!", "*")) or password in ("", "!!")


def normalize_whitespace(text):
    if not text:
        return ""
    # Replace multiple spaces/tabs with a single space
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_listening_ports(raw):
    ports = []
    for line in (raw or "").splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        # Older versions of ss/netstat might not include the word 'LISTEN'
        # If it's a tcp or udp line, we treat it as a candidate since the command used -l
        if not any(token in lowered for token in ("tcp", "udp", "listen")):
            continue
        proto_match = re.match(r"^(tcp|udp)\w*", lowered)
        proto = proto_match.group(1) if proto_match else "tcp"
        port = extract_port(stripped)
        if not port:
            continue
        # Normalize whitespace for cleaner report output
        normalized_line = normalize_whitespace(stripped)
        ports.append({"port": int(port), "proto": proto, "line": normalized_line})
    return ports


def find_ports(raw, target_ports):
    parsed = parse_listening_ports(raw)
    targets = {int(port) for port in target_ports}
    found = []
    seen = set()
    for item in parsed:
        if item["port"] not in targets:
            continue
        key = (item["proto"], item["port"])
        if key in seen:
            continue
        seen.add(key)
        found.append(item)
    return found


def extract_port(line):
    # Handle UNIX style (e.g., *.22, 127.0.0.1.22) or Linux style (e.g., :::22, 0.0.0.0:22)
    # Match digit(s) preceded by : or . and followed by space or end of line
    # We look from the right to get the port in 'IP.PORT' or 'IP:PORT'
    matches = re.findall(r"[:.](\d+)(?:\s|$)", line)
    if matches:
        return matches[-1]
    return None


def is_garbage_line(line):
    if not line:
        return True
    lowered = line.lower()
    garbage_keywords = (
        "last successful login",
        "last unsuccessful login",
        "could not chdir",
        "task [",
        "play [",
        "ok:",
        "changed:",
        "msg:",
        "결과:",
    )
    return any(keyword in lowered for keyword in garbage_keywords)


def safe_int(value):
    try:
        return int(str(value).strip())
    except Exception:
        return None
