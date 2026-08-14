import pandas as pd
import re
import os

raw_data = os.environ.get('report_data', '')
save_path = os.environ.get('save_path', '')
output_name = os.environ.get('output_name', '')
mediaserver = os.environ.get('host', '')

# 첫 번째부터 세 번째 줄과 마지막 줄 삭제
lines = raw_data.split('\n')[5:-2]

# 삭제된 라인을 제외하고 나머지 라인을 문자열로 합치기
data_lines = '\n'.join(lines)

# # 결과 출력
# print(data_lines)

# DataFrame 생성
columns = ["호스트","백업정책", "시작시간", "종료시간","백업상태" ,"비고"]
df = pd.DataFrame(columns=columns)

# 데이터 추출 및 입력
df["호스트"] = [line.split()[0] for line in data_lines.split('\n')]
df["백업정책"] = [line.split()[1] for line in data_lines.split('\n')]
df["시작시간"] = [line.split()[3] for line in data_lines.split('\n')]
df["종료시간"] = ["Not Running" if line.split()[4] == "Not" else line.split()[4] for line in data_lines.split('\n')]
df["백업상태"] = ["확인필요" if line.split()[4] == "Not" else "정상" for line in data_lines.split('\n')]
df["비고"] = ""

# Excel 파일로 저장
output_filename = os.path.join(save_path, output_name)

# 저장 경로가 없으면 생성
os.makedirs(save_path, exist_ok=True)

with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
    # 데이터프레임을 Excel에 쓰기 (첫 번째 행은 제목, 그 이후부터는 데이터)
    df.to_excel(writer, sheet_name='Sheet1', index=False)

    # Excel 파일에 접근하여 워크북과 워크시트 객체 가져오기
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']

    # A1 셀에 제목 입력
    title_format = workbook.add_format({
        'bold': True, 
        'font_size': 14, 
        'align': 'center', 
        'valign': 'vcenter',
        'top': 2,  # 상단 테두리 스타일 추가
        'bottom': 2,  # 하단 테두리 스타일 추가
    })
    worksheet.merge_range(0, 0, 0, len(df.columns)-1, '무정차 민자 내부복제', title_format)

    # 표 헤더에 대한 서식 설정
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3'})
    
    # 표 헤더에 대한 셀 병합 및 입력
    for col_num, value in enumerate(df.columns.values):
        worksheet.merge_range(1, col_num, 2, col_num, value, header_format)

    # 표 내용에 대한 서식 설정
    cell_format = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'bottom': 1, 'top': 1, 'left': 1, 'right': 1
    })  # 상하좌우 테두리 스타일 추가

    # 데이터프레임 내용 입력
    for row_num, values in enumerate(df.values):
        for col_num, value in enumerate(values):
            worksheet.write(row_num + 3, col_num, value, cell_format)

    # 셀 너비 자동 조절
    for i, col in enumerate(df.columns):
        max_len = max(df[col].astype(str).apply(len).max(), len(col))
        worksheet.set_column(i, i, max_len + 3)  # +2는 여유 공간을 위한 것

print("데이터프레임이 Excel 파일로 저장되었습니다.")