from .base_filter import BaseFilter, filter_result
import json
import re


class MongodbJsonFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if self.command:
            is_success, is_pass, result, message = self.mongodb_type1(stdout_data)
        else:
            is_pass = 0
            is_success = 0
            message = "❌ 지원하지 않는 명령어입니다."
            result = message

        return {
            'message': message,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def _detect_mongo_error(self, stdout_data):
        if not stdout_data:
            return None

        lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]
        auth_patterns = [
            r'Authentication failed',
            r'AuthenticationFailed',
            r'not authorized',
            r'Unauthorized',
        ]
        connect_patterns = [
            r"couldn['’]t connect to server",
            r'connection attempt failed',
            r'Connection refused',
            r'exception:\s*connect failed',
            r'\bconnect failed\b',
            r'exiting with code\s*1',
        ]

        auth_lines = []
        connect_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in auth_patterns):
                auth_lines.append(line)
                continue
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in connect_patterns):
                connect_lines.append(line)

        def unique_preview(values):
            seen = []
            for value in values:
                if value not in seen:
                    seen.append(value)
            return "\n".join(seen[:5])

        if auth_lines:
            return "auth", unique_preview(auth_lines)
        if connect_lines:
            return "connect", unique_preview(connect_lines)
        return None

    def _parse_path(self, path_text):
        tokens = []
        current = []
        i = 0

        while i < len(path_text):
            ch = path_text[i]
            if ch == '.':
                if current:
                    tokens.append(''.join(current))
                    current = []
                i += 1
                continue

            if ch == '[':
                if current:
                    tokens.append(''.join(current))
                    current = []
                end = path_text.find(']', i)
                if end == -1:
                    raise ValueError(f"잘못된 path 형식입니다: {path_text}")
                inner = path_text[i + 1:end].strip()
                if inner == '*':
                    tokens.append('*')
                elif inner.isdigit():
                    tokens.append(int(inner))
                elif (inner.startswith("'") and inner.endswith("'")) or (inner.startswith('"') and inner.endswith('"')):
                    tokens.append(inner[1:-1])
                else:
                    tokens.append(inner)
                i = end + 1
                continue

            current.append(ch)
            i += 1

        if current:
            tokens.append(''.join(current))

        return tokens

    def _parse_scalar_value(self, value_text):
        text = value_text.strip().rstrip(',')

        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        if text == "true":
            return True
        if text == "false":
            return False
        if text == "null":
            return None
        if re.fullmatch(r'-?\d+', text):
            return int(text)
        if re.fullmatch(r'-?\d+\.\d+', text):
            return float(text)
        return text

    def _consume_function_call(self, text, start):
        depth = 0
        i = start
        in_string = False
        quote_char = ""
        escaped = False

        while i < len(text):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote_char:
                    in_string = False
                i += 1
                continue

            if ch in ['"', "'"]:
                in_string = True
                quote_char = ch
                i += 1
                continue

            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1], i + 1
            i += 1

        raise ValueError("Mongo 함수형 값을 닫는 ')'를 찾지 못했습니다.")

    def _quote_mongo_function_values(self, text):
        result = []
        i = 0
        in_string = False
        quote_char = ""
        escaped = False

        while i < len(text):
            ch = text[i]

            if in_string:
                result.append(ch)
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote_char:
                    in_string = False
                i += 1
                continue

            if ch in ['"', "'"]:
                in_string = True
                quote_char = ch
                result.append(ch)
                i += 1
                continue

            if re.match(r'[A-Za-z_$]', ch):
                start = i
                while i < len(text) and re.match(r'[A-Za-z0-9_$]', text[i]):
                    i += 1

                ident = text[start:i]
                if ident in ["true", "false", "null"]:
                    result.append(ident)
                    continue

                j = i
                while j < len(text) and text[j].isspace():
                    j += 1

                if j < len(text) and text[j] == "(":
                    func_expr, end_index = self._consume_function_call(text, start)
                    result.append(json.dumps(func_expr, ensure_ascii=False))
                    i = end_index
                    continue

                result.append(ident)
                continue

            result.append(ch)
            i += 1

        return "".join(result)

    def _normalize_special_scalar(self, value):
        if not isinstance(value, str):
            return value

        text = value.strip()

        match = re.fullmatch(r'NumberLong\("(-?\d+)"\)', text) or re.fullmatch(r'NumberLong\((-?\d+)\)', text)
        if match:
            return int(match.group(1))

        match = re.fullmatch(r'NumberInt\("(-?\d+)"\)', text) or re.fullmatch(r'NumberInt\((-?\d+)\)', text)
        if match:
            return int(match.group(1))

        match = re.fullmatch(r'NumberDecimal\("(-?\d+(?:\.\d+)?)"\)', text)
        if match:
            return float(match.group(1)) if "." in match.group(1) else int(match.group(1))

        match = re.fullmatch(r'ObjectId\("([^"]+)"\)', text)
        if match:
            return match.group(1)

        match = re.fullmatch(r'ISODate\("([^"]+)"\)', text)
        if match:
            return match.group(1)

        return text

    def _sanitize_mongo_json(self, stdout_data):
        text = stdout_data.strip()
        return self._quote_mongo_function_values(text)

    def _extract_json_text(self, stdout_data):
        text = self._sanitize_mongo_json(stdout_data)

        if "명령어 결과값:" in text:
            text = text.split("명령어 결과값:", 1)[1].strip()

        decoder = json.JSONDecoder()
        last_obj = None

        for index, ch in enumerate(text):
            if ch not in "[{":
                continue
            try:
                parsed_obj, _ = decoder.raw_decode(text[index:].strip())
                last_obj = parsed_obj
            except Exception:
                continue

        if last_obj is None:
            raise ValueError("파싱 가능한 JSON 블록을 찾지 못했습니다.")

        return json.dumps(last_obj, ensure_ascii=False)

    def _parse_records_from_json(self, current, path=None):
        if path is None:
            path = []

        records = []
        if isinstance(current, dict):
            for key, value in current.items():
                records.extend(self._parse_records_from_json(value, path + [key]))
            return records

        if isinstance(current, list):
            for index, value in enumerate(current):
                records.extend(self._parse_records_from_json(value, path + [index]))
            return records

        records.append((path, self._normalize_special_scalar(current)))
        return records

    def _load_json_records(self, stdout_data):
        json_text = self._extract_json_text(stdout_data)
        parsed = json.loads(json_text)
        return self._parse_records_from_json(parsed)

    def _parse_records(self, stdout_data):
        records = []
        stack = [{"type": "object", "path": []}]

        for raw_line in stdout_data.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line in {"{", "}"} and len(stack) == 1:
                continue

            if line.startswith("}") or line.startswith("]"):
                if len(stack) > 1:
                    stack.pop()
                continue

            current_context = stack[-1]

            if current_context["type"] == "array":
                if line.startswith("{"):
                    item_path = current_context["path"] + [current_context["next_index"]]
                    current_context["next_index"] += 1
                    stack.append({"type": "object", "path": item_path})
                    continue
                if line.startswith("["):
                    item_path = current_context["path"] + [current_context["next_index"]]
                    current_context["next_index"] += 1
                    stack.append({"type": "array", "path": item_path, "next_index": 0})
                    continue
                records.append((current_context["path"] + [current_context["next_index"]], self._parse_scalar_value(line)))
                current_context["next_index"] += 1
                continue

            key_match = re.match(r'^"([^"]+)"\s*:\s*(.+)$', line)
            if not key_match:
                continue

            key = key_match.group(1)
            value_part = key_match.group(2).strip()
            current_path = current_context["path"] + [key]

            if value_part.startswith("{"):
                if "}" in value_part:
                    continue
                stack.append({"type": "object", "path": current_path})
                continue

            if value_part.startswith("["):
                if "]" in value_part:
                    continue
                stack.append({"type": "array", "path": current_path, "next_index": 0})
                continue

            records.append((current_path, self._parse_scalar_value(value_part)))

        return records

    def _key_match(self, expected, actual):
        if not isinstance(expected, str) or not isinstance(actual, str):
            return expected == actual
        return expected.lstrip('$') == actual.lstrip('$')

    def _path_match(self, expected_tokens, actual_tokens):
        if len(expected_tokens) != len(actual_tokens):
            return False

        for expected, actual in zip(expected_tokens, actual_tokens):
            if expected == '*':
                if not isinstance(actual, int):
                    return False
                continue
            if isinstance(expected, int):
                if expected != actual:
                    return False
                continue
            if isinstance(actual, int):
                return False
            if not self._key_match(expected, actual):
                return False

        return True

    def _extract_value(self, records, path_text):
        expected_tokens = self._parse_path(path_text)
        values = [value for actual_tokens, value in records if self._path_match(expected_tokens, actual_tokens)]
        if not values:
            return None
        if '*' in expected_tokens:
            return values
        if len(values) == 1:
            return values[0]
        return values

    def _normalize_rules(self):
        criteria = self.inspection_criteria

        if isinstance(criteria, dict):
            return [{"path": key, "expected": value} for key, value in criteria.items()]

        raise ValueError("inspection_criteria는 key/value 딕셔너리 형식이어야 합니다.")

    def _to_number(self, value):
        if isinstance(value, bool):
            raise ValueError("bool 타입은 숫자 비교를 지원하지 않습니다.")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and re.fullmatch(r'-?\d+(?:\.\d+)?', value.strip()):
            return float(value.strip())
        raise ValueError(f"숫자 변환 불가: {value}")

    def _compare_threshold(self, actual, expected):
        match = re.fullmatch(f'\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*', expected)
        if not match:
            return None

        operator = match.group(1)
        threshold = float(match.group(2))

        if isinstance(actual, list):
            if not actual:
                return False
            actual_values = [self._to_number(item) for item in actual]
        else:
            actual_values = [self._to_number(actual)]

        if operator == ">=":
            return all(value >= threshold for value in actual_values)
        if operator == "<=":
            return all(value <= threshold for value in actual_values)
        if operator == ">":
            return all(value > threshold for value in actual_values)
        if operator == "<":
            return all(value < threshold for value in actual_values)

        return None

    def _compare(self, actual, expected):
        if isinstance(expected, str):
            threshold_result = self._compare_threshold(actual, expected)
            if threshold_result is not None:
                return threshold_result

        if isinstance(actual, list):
            if not actual:
                return False
            if isinstance(expected, list):
                return all(item in expected for item in actual)
            return all(item == expected for item in actual)

        if isinstance(expected, list):
            return actual in expected

        return actual == expected

    def _display_value(self, value):
        return json.dumps(value, ensure_ascii=False)

    def mongodb_type1(self, stdout_data):
        try:
            is_success = 1

            mongo_error = self._detect_mongo_error(stdout_data)
            if mongo_error:
                error_type, error_text = mongo_error
                is_success = 0
                is_pass = 0
                if error_type == "auth":
                    message = "❌ MongoDB 인증 또는 권한 오류가 발생했습니다.\n" + error_text
                else:
                    message = "❌ MongoDB 연결 오류가 발생했습니다.\n" + error_text
                result = message
                return is_success, is_pass, result, message

            try:
                rules = self._normalize_rules()
            except Exception as e:
                is_pass = 0
                message = f"❌ 점검 필요: inspection_criteria 설정 오류 - {str(e)}"
                result = message
                return is_success, is_pass, result, message

            try:
                records = self._load_json_records(stdout_data)
            except Exception:
                records = self._parse_records(stdout_data)
            if not records:
                is_pass = 0
                message = "❌ 점검 필요: MongoDB 출력에서 비교 가능한 key/value 데이터를 찾지 못했습니다."
                result = message
                return is_success, is_pass, result, message

            failed_rules = []

            for rule in rules:
                path = rule["path"]
                expected = rule["expected"]
                actual = self._extract_value(records, path)

                if actual is None:
                    failed_rules.append(
                        f"- 점검 항목: {path}\n"
                        f"  출력값: 경로 없음"
                        f"\n  기준값: {self._display_value(expected)}\n"
                    )
                    continue

                try:
                    matched = self._compare(actual, expected)
                except Exception as e:
                    failed_rules.append(
                        f"- 점검 항목: {path}\n"
                        f"  출력값: {self._display_value(actual)}\n"
                        f"  기준값: {self._display_value(expected)}\n"
                        f"  오류: {str(e)}"
                    )
                    continue

                if not matched:
                    failed_rules.append(
                        f"- 점검 항목: {path}\n"
                        f"  출력값: {self._display_value(actual)}\n"
                        f"  기준값: {self._display_value(expected)}\n"
                    )

            if failed_rules:
                is_pass = 0
                message = "❌ 점검 필요: MongoDB JSON 기준값을 확인하세요.\n" + "\n".join(failed_rules)
            else:
                is_pass = 1
                message = f"✅ 정상: MongoDB JSON 점검 기준 {len(rules)}건이 모두 일치합니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ MongoDB JSON 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

