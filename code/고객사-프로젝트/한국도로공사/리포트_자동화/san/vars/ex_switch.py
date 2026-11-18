import pandas as pd
import re
import os

raw_data = os.environ.get('report_data', '')
save_path = os.environ.get('save_path', '')
output_name = os.environ.get('output_name', '')

# '-' 다음부터 '=' 전까지의 데이터 영역 추출
data_section = re.search(r'[-]{3,}(.+)[-]{3,}', raw_data, re.DOTALL).group(1).strip().split('\n')[:-1]

# 공백 기준으로 나누기
data_lines = [line.split() for line in data_section]

pattern = r'\[\[\s*([^\]\s]+)\s+[^\]]+\s*\]\]'
matches = re.findall(pattern, raw_data)

# DataFrame 생성"
columns = ["SAN Switch", "업무명", "호스트명", "S/P", "RX", "TX", "ERR_CNT"]
df = pd.DataFrame(columns=columns)

# 데이터 추출 및 입력
df["SAN Switch"] = [matches[0]] * len(data_lines)
df["업무명"] = " "
#df["호스트명"] = [line.split()[0].replace(':', '') for line in data_lines]
df["호스트명"] = [sublist[0].replace(':', '') for sublist in data_lines]  # ":" 제거
df["S/P"] = [sublist[3] + "/" + sublist[4] for sublist in data_lines]
df["RX"] = [sublist[6] for sublist in data_lines]
df["TX"] = [sublist[8] for sublist in data_lines]
df["ERR_CNT"] = [sublist[10] for sublist in data_lines]

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
    worksheet.merge_range(0, 0, 0, len(df.columns)-1, '핵심서버 SAN Switch 라인 점검', title_format)

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
        worksheet.set_column(i, i, max_len + 2)  # +2는 여유 공간을 위한 것

print("데이터프레임이 Excel 파일로 저장되었습니다.")
