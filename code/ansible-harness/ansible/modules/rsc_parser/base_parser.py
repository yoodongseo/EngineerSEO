import json


class BaseParser:
    def __init__(self, lines):
        self.lines = self._clean(lines)

    def _clean(self, lines):
        return [l for l in lines if l.strip() and "setlocale" not in l]
 
    def extract_json_lines(self):
        result = []
        for line in self.lines:
            line = line.strip()
            if not line.startswith("{") or not line.endswith("}"):
                continue
            try:
                obj = json.loads(line)
                result.append(obj)
            except (ValueError, TypeError):
                continue
        return result
    
    def strip_unit(self, value):
        return ''.join(filter(str.isdigit, value))

    def to_int(self, s, default=0):
        try:
            return int(s)
        except (ValueError, TypeError):
            return default

    def fallback(self):
        """
        어떤 파서도 정의되어 있지 않은 명령어 출력에 대한 기본 반환
        """
        if len(self.lines) == 1:
            return self.lines[0]
        return self.lines