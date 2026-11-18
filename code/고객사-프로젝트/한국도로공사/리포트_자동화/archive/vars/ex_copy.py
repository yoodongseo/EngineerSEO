import pandas as pd
import re
import os

raw_data = os.environ.get('report_data', '')
save_path = os.environ.get('save_path', '')
output_name = os.environ.get('output_name', '')
mediaserver = os.environ.get('host', '')

# 첫 번째부터 세 번째 줄과 마지막 줄 삭제
lines = raw_data.split('\n')[4:-2]

# 삭제된 라인을 제외하고 나머지 라인을 문자열로 합치기
data_lines = '\n'.join(lines)

# # 결과 출력
# print(data_lines)

# 시간 형식을 나타내는 정규식 패턴
time_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}$')

# DataFrame 생성
columns = ["미디어서버","시작시간", "종료시간", "소요시간","백업상태", "비고"]
df = pd.DataFrame(columns=columns)

미디어서버_list = [mediaserver] * len(data_lines.split('\n'))  # 미디어서버 데이터 생성
시작시간_list = []  # 시작시간 리스트 초기화
종료시간_list = []  # 종료시간 리스트 초기화
소요시간_list = []  # 소요시간 리스트 초기화
백업상태_list = []  # 백업상태 리스트 초기화

# raw_data에서 각 줄을 처리
for line in data_lines.split('\n'):
    data = line.split()  # 공백을 기준으로 데이터를 나눔
    if len(data) != 4:  # 데이터의 길이가 4가 아니면 (종료시간이 없는 경우)
        종료시간_list.append(None)  # 종료시간에 None을 추가
        소요시간_list.append(None)  # 소요시간에 None을 추가
        백업상태_list.append("확인 필요")  # 백업상태에 "확인 필요"를 추가
    else:  # 데이터의 길이가 4인 경우 (종료시간이 있는 경우)
        종료시간_list.append(data[3])  # 종료시간을 추가
        if data[3]:  # 종료시간이 비어있지 않은 경우
            start_time = data[1]
            duration = pd.to_datetime(data[3]) - pd.to_datetime(start_time)
            소요시간_list.append(str(duration).split()[-1])  # 소요시간을 계산하여 추가
            백업상태_list.append("정상")  # 백업상태를 "정상"으로 추가
        else:  # 종료시간이 비어있는 경우
            소요시간_list.append(None)  # 소요시간에 None을 추가
            백업상태_list.append("확인 필요")  # 백업상태에 "확인 필요"를 추가

# 데이터프레임에 값 할당
df["미디어서버"] = 미디어서버_list
df["시작시간"] = [line.split()[1] for line in data_lines.split('\n')]
df["종료시간"] = 종료시간_list
df["소요시간"] = 소요시간_list
df["백업상태"] = 백업상태_list
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
    worksheet.merge_range(0, 0, 0, len(df.columns)-1, '아카이브 백업 일지', title_format)

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