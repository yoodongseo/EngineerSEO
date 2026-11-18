class FilterModule(object):
    def filters(self):
        return {
            'cut_str': self.cut_str
        }

    def cut_str(self, value, row_index, index=None, sub_index=None):
        if not isinstance(value, str):
            raise TypeError('The first argument must be a string')
        if not isinstance(row_index, int):
            raise TypeError('The second argument must be an integer')
        if index is not None and not isinstance(index, int):
            raise TypeError('The third argument must be an integer')
        if sub_index is not None and not isinstance(sub_index, int):
            raise TypeError('The fourth argument must be an integer or None')

        # 리스트형 문자열을 개행문자로 구분
        original_lines = value.split('\n')

        # cannot change locale 에러때문에 추가
        lines = [line for line in original_lines if 'ko_KR.UTF-8' not in line]

        # row 데이터를 받아와 인덱싱
        if row_index >= 0:
            row_index = row_index if row_index >= 0 else len(lines) + row_index
            if row_index < 0 or row_index >= len(lines):
                raise IndexError('Row index out of range')
            row = lines[row_index]
            element = row
        else:
            row = lines[row_index]
            element = row

        # 행 구분이 있을경우
        if index is not None:
            # 행을 공백으로 구분
            parts = row.split()

            # column 데이터를 받아와 인덱싱
            if index >= 0:
                index = index if index >= 0 else len(parts) + index
                if index < 0 or index >= len(parts):
                    raise IndexError('Index out of range')
                element = parts[index]
            else:
                element = parts[index]

        # 문자열 위치 구분이 있을경우
        if sub_index is not None:
            return element[:sub_index]

        return element