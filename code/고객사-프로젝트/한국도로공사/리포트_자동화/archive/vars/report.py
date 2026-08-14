import pandas as pd
import re
import os
 
raw_data = """

    =================================================
    D       Start           Host            End
    =================================================
    25      01:35:00        biviadb         01:35:18
    25      04:30:00        bptrfdb         04:33:59
    25      05:30:00        bpoprdb         05:48:15
    25      07:35:00        biviadb         07:35:17
    25      11:30:00        bpoprdb         12:01:01
    25      13:35:00        biviadb         13:35:18
    25      16:30:00        bptrfdb         16:32:14
    25      17:30:00        bpoprdb         18:16:39
    25      22:30:00        bptrfdb         22:37:17
    =================================================
"""
save_path = "./"
output_name = "copy_backup.xlsx"
mediaserver = "hosttest"

# 첫 번째부터 세 번째 줄과 마지막 줄 삭제
lines = raw_data.split('\n')[5:-2]

# 삭제된 라인을 제외하고 나머지 라인을 문자열로 합치기
extracted_data = '\n'.join(lines)

# 결과 출력
print(extracted_data)

# # DataFrame 생성
# columns = ["미디어서버","시작시간", "종료시간", "소요시간","백업상태", "비고"]
# df = pd.DataFrame(columns=columns)

# # 데이터 추출 및 입력
# df["미디어서버"] = [mediaserver] * len(data_lines)
# df["시작시간"] = [line.split()[1] for line in data_lines]
# df["종료시간"] = [line.split()[-1] for line in data_lines]
# df["소요시간"] = [(pd.to_datetime(line.split()[-1]) - pd.to_datetime(line.split()[1])).total_seconds() for line in data_lines]
# df["백업상태"] = ["정상" if line.split()[-1] else "확인 필요" for line in data_lines]
# df["비고"] = ""

# # Excel 파일로 저장
# output_filename = os.path.join(save_path, output_name)

# # 저장 경로가 없으면 생성
# os.makedirs(save_path, exist_ok=True)

# with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
#     # 데이터프레임을 Excel에 쓰기 (첫 번째 행은 제목, 그 이후부터는 데이터)
#     df.to_excel(writer, sheet_name='Sheet1', index=False)

#     # Excel 파일에 접근하여 워크북과 워크시트 객체 가져오기
#     workbook = writer.book
#     worksheet = writer.sheets['Sheet1']

#     # A1 셀에 제목 입력
#     title_format = workbook.add_format({
#         'bold': True, 
#         'font_size': 14, 
#         'align': 'center', 
#         'valign': 'vcenter',
#         'top': 2,  # 상단 테두리 스타일 추가
#         'bottom': 2,  # 하단 테두리 스타일 추가
#     })
#     worksheet.merge_range(0, 0, 0, len(df.columns)-1, '아카이브 백업 일지', title_format)

#     # 표 헤더에 대한 서식 설정
#     header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3'})
    
#     # 표 헤더에 대한 셀 병합 및 입력
#     for col_num, value in enumerate(df.columns.values):
#         worksheet.merge_range(1, col_num, 2, col_num, value, header_format)

#     # 표 내용에 대한 서식 설정
#     cell_format = workbook.add_format({
#         'align': 'center', 'valign': 'vcenter', 'bottom': 1, 'top': 1, 'left': 1, 'right': 1
#     })  # 상하좌우 테두리 스타일 추가

#     # 데이터프레임 내용 입력
#     for row_num, values in enumerate(df.values):
#         for col_num, value in enumerate(values):
#             worksheet.write(row_num + 3, col_num, value, cell_format)

#     # 셀 너비 자동 조절
#     for i, col in enumerate(df.columns):
#         max_len = max(df[col].astype(str).apply(len).max(), len(col))
#         worksheet.set_column(i, i, max_len + 2)  # +2는 여유 공간을 위한 것

# print("데이터프레임이 Excel 파일로 저장되었습니다.")