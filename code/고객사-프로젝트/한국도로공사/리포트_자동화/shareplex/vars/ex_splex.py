import pandas as pd
import re
import os
from datetime import datetime # 날짜추가

raw_data = os.environ.get('report_data', '')
save_path = os.environ.get('save_path', '')
output_name = os.environ.get('output_name', '')
mediaserver = os.environ.get('host', '')

# "-" 라인을 찾습니다.
pattern = re.compile(r'-{2,}', re.MULTILINE)
matches = pattern.finditer(raw_data)

# 세 번째 "-" 라인 이후의 데이터를 찾습니다.
start_index = None
end_index = None
count = 0
for match in matches:
    count += 1
    if count == 3:  # 세 번째 "-" 라인을 찾으면
        start_index = match.end()  # 해당 라인의 끝 인덱스를 찾습니다.
    elif count == 4:  # 네 번째 "-" 라인을 찾으면
        end_index = match.start()  # 해당 라인의 시작 인덱스를 찾습니다.
        break
data_lines = raw_data[start_index:end_index].strip()  # 공백 제거
data = [line.split() for line in data_lines.split('\n') if line.strip()]
# DataFrame 생성
columns = ["Class","DBSID","Source","Target", "Source_1", "Target_1","Target_2"]
df = pd.DataFrame(columns=columns)

# 데이터 추출 및 입력
df["Class"] = [line[0] for line in data]
df["DBSID"] = [line[1] for line in data]
df["Source"] = ["정상" if line[2] == "Success" else "확인 필요" for line in data]
df["Target"] = ["정상" if line[3] == "Success" else "확인 필요" for line in data]
df["Source_1"] = ["정상" if line[4] == "Success" else "확인 필요" for line in data]
df["Target_1"] = ["정상" if line[5] == "Success" else "확인 필요" for line in data]
df["Target_2"] = ["정상" if line[6] == "Success" else "확인 필요" for line in data]

# Excel 파일로 저장
output_filename = os.path.join(save_path, output_name)

# 저장 경로가 없으면 생성
os.makedirs(save_path, exist_ok=True)

with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
    # 데이터프레임을 Excel에 쓰기 (첫 번째 행은 제목, 그 이후부터는 데이터)
    # df.to_excel(writer, sheet_name='Sheet1', index=False, startrow=25)

    # Excel 파일에 접근하여 워크북과 워크시트 객체 가져오기
    workbook = writer.book
    worksheet = workbook.add_worksheet('Sheet1')
    # worksheet = writer.sheets['Sheet1']

    # A1 셀에 제목 입력
    title_format = workbook.add_format({
        'bold': True, 
        'font_size': 14, 
        'align': 'center', 
        'valign': 'vcenter',
        'bg_color': '#d9d9d9',  # 백그라운드 회색
        'top': 2,               # 상단 테두리 스타일 추가
        'bottom': 2,            # 하단 테두리 스타일 추가
    })
    worksheet.merge_range(0, 0, 0, 16, 'DB 데이터 동기화 일일점검 일지', title_format)

    # 3,4행에 오늘 날짜 셀에 쓰기
    today = datetime.today()
    today_with_korean_weekday = today.strftime('%Y년 %m월 %d일 ')
    weekday_str = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    weekday_index = today.weekday()
    today_with_korean_weekday += weekday_str[weekday_index]
        #today_with_weekday = datetime.today().strftime('%Y-%m-%d %A') #요일 영어 표기
    worksheet.merge_range(2,0,3,len(df.columns)-4, today_with_korean_weekday)

    # 표 헤더에 대한 서식 설정
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3' ,'bottom': 1, 'top': 1, 'left': 1, 'right': 1})
    
    # 표 헤더에 대한 셀 병합 및 입력
    # for col_num, value in enumerate(df.columns.values):
    #     worksheet.merge_range(6, col_num, 7, col_num, value, header_format)

    # 표 내용에 대한 서식 설정
    cell_format = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'bottom': 1, 'top': 1, 'left': 1, 'right': 1})
    cell_right_format =  workbook.add_format({
        'align': 'right', 'bottom': 1, 'top': 1, 'left': 1, 'right': 1
    })  # 상하좌우 테두리 스타일 추가

    # 3행 O열에 "점검자", 4행 O열에 "확인자" 입력
    worksheet.write('O3', '점검자', header_format)
    worksheet.write('O4', '확인자', header_format)

    # O열 3행부터 Q열 3행까지 빈 셀로 만들고 병합
    worksheet.merge_range('P3:Q3', '', cell_format)
    # O열 4행부터 Q열 4행까지 빈 셀로 만들고 병합
    worksheet.merge_range('P4:Q4', '', cell_format)

    # 5행, 19행 소제목 추가
    worksheet.merge_range(4, 0, 4,len(df.columns)-1, '1. Shareplex')
    worksheet.merge_range(18, 0, 18,len(df.columns)-1, '2. OGG')
    # 6~7행 고정 헤더 입력
    worksheet.merge_range(5,0,5,3,'Source', header_format)
    worksheet.merge_range(5,4,6,4,'동기화 →', header_format)
    worksheet.merge_range(5,5,5,8,'Target', header_format)
    worksheet.merge_range(5,9,6,9,'점검시간', header_format)
    worksheet.merge_range(5,10,5,11,'SharePlex 프로세스 상태 (show)', header_format)
    worksheet.merge_range(5,12,5,13,'Queue 상태 및 Backlog 수 (qstatus)', header_format)
    worksheet.write(5,14, 'Sync 상태 (show sync)', header_format)
    worksheet.merge_range(5,15,6,16,'비고', header_format)
    worksheet.write(6,0,'업무명', header_format)
    worksheet.write(6,1,'Hostname', header_format)
    worksheet.write(6,2,'Oracle SID', header_format)
    worksheet.write(6,3,'SharePlex 계정명', header_format)
    worksheet.write(6,5,'업무명', header_format)
    worksheet.write(6,6,'Hostname', header_format)
    worksheet.write(6,7,'Oracle SID', header_format)
    worksheet.write(6,8,'SharePlex 계정명', header_format)
    worksheet.write(6,10,'Source', header_format)
    worksheet.write(6,11,'Target', header_format)
    worksheet.write(6,12,'Source', header_format)
    worksheet.write(6,13,'Target', header_format)
    worksheet.write(6,14,'Target', header_format)
    #20~21행 고정헤더 입력
    worksheet.merge_range(19,0,19,3,'Source', header_format)
    worksheet.merge_range(19,4,20,4,'동기화 →', header_format)
    worksheet.merge_range(19,5,19,8,'Target', header_format)
    worksheet.merge_range(19,9,20,9,'점검시간', header_format)
    worksheet.merge_range(19,10,19,11,'OGG프로세스 상태(info all)', header_format)
    worksheet.merge_range(19,12,19,13,'Lag at Chkpt(10분 이상 지연시)', header_format)
    worksheet.merge_range(19,14,19,15,'Time Since Chkpt(10분 이상 지연시)', header_format)
    worksheet.merge_range(19,16,20,16,'비고', header_format)
    worksheet.write(20,0,'업무명', header_format)
    worksheet.write(20,1,'Hostname', header_format)
    worksheet.write(20,2,'Oracle SID', header_format)
    worksheet.write(20,3,'SharePlex 계정명', header_format)
    worksheet.write(20,5,'업무명', header_format)
    worksheet.write(20,6,'Hostname', header_format)
    worksheet.write(20,7,'Oracle SID', header_format)
    worksheet.write(20,8,'SharePlex 계정명', header_format)
    worksheet.write(20,10,'Source', header_format)
    worksheet.write(20,11,'Target', header_format)
    worksheet.write(20,12,'Source', header_format)
    worksheet.write(20,13,'Target', header_format)
    worksheet.write(20,14,'Source', header_format)
    worksheet.write(20,15,'Target', header_format)
    # 비고란 테두리
    for row in range(7, 18):
        worksheet.merge_range(row, 15, row, 16, '', cell_format)
    # 고정 데이터 삽입
    values_01 = ['통합정산','영업통합','영업통합','통행정보','경유지 수집','통행정보','경유지 수집','경유지 배포','전자문서','유러닝','홈페이지']
    for row, value in enumerate(values_01, start=7):
        worksheet.write(row, 0, value, cell_format)

    values_02 = ['bicaldb1', 'bclbbdb1', 'bclbbdb1', 'bcltidb1', 'biviadb1', 'bcltidb1', 'biviadb1', 'bviadb1', 'E950-a1', 'E950-b3', 'E950-b3']
    for row, value in enumerate(values_02, start=7):
        worksheet.write(row, 1, value, cell_format)

    values_03 = ['BPSTL1', 'BPOPR1', 'BPOPR1', 'BPTRF1', 'BIVIA1', 'BPTRF1', 'BIVIA1', 'BVIA1', 'ANKHCG', 'ALMS', 'AWWW']
    for row, value in enumerate(values_03, start=7):
        worksheet.write(row, 2, value, cell_format)

    values_04 = ['splex3', 'splex3', 'splex', 'splex', 'splex4', 'splex_dr', 'splex_dr', 'splex_dr', 'splexankhcg', 'splexalms', 'splexawww']
    for row, value in enumerate(values_04, start=7):
        worksheet.write(row, 3, value, cell_format)

    values_05 = ["운영\n→","운영\n→","운영\n→", "운영\n→","운영\n→","DR\n→","DR\n→","DR\n→","DR\n→","DR\n→","DR\n→"]
    for row, value in enumerate(values_05, start=7):
        worksheet.write(row, 4, value, cell_format)

    values_06 = ['영업통합', '통합정산', '통행정보', '영업통합', '통합정산', '통행정보 재해복구', '경유지수집 재해복구', '경유지배포 재해복구', '경영 재해복구', '경영 재해복구', '경영 재해복구']
    for row, value in enumerate(values_06, start=7):
        worksheet.write(row, 5, value, cell_format)

    values_07 = ['bclbbdb1', 'bicaldb1', 'bcltidb1', 'bclbbdb1', 'bicaldb1', 'bcltidb_DR', 'biviadb_DR', 'bviadb_DR', 'p780-c1', 'p780-c1', 'p780-c1']
    for row, value in enumerate(values_07, start=7):
        worksheet.write(row, 6, value, cell_format)

    values_08 = ['BPOPR1', 'BPSTL1', 'BPTRF1', 'BPOPR1', 'BPSTL1', 'BPTRF', 'BIVIA', 'BVIA', 'ANKHCG', 'ALMS', 'AWWW']
    for row, value in enumerate(values_08, start=7):
        worksheet.write(row, 7, value, cell_format)

    values_09 = ['splex3', 'splex3', 'splex', 'splex', 'splex4', 'splex_dr', 'splex_dr', 'splex_dr', 'splexankhcg', 'splexalms', 'splexawww']
    for row, value in enumerate(values_09, start=7):
        worksheet.write(row, 8, value, cell_format)

    values_10 = ['05:00', '05:00', '05:00', '05:00', '05:00', '05:00', '05:00', '05:00', '05:00', '05:00', '05:00']
    for row, value in enumerate(values_10, start=7):
        worksheet.write(row, 9, value, cell_format)

    values_11 = ['exTMS통합DB', 'exTMStotalDB1', 'ITSDB01', 'oracle', 'DR →', 'exTMS통합DB 재해복구', 'extmstotaldb_dr', 'ITSDB0', 'oracle', '05:00','','','','','','','' ]
    for column, value in enumerate(values_11, start=0):
        worksheet.write(21, column, value, cell_format)
    
#=======================데이터프레임 값 참조하여 키값이 일치하는 데이터프레임 값 출력 
    condition1 = df['DBSID'].isin(values_03)
    condition2 = df['Class'].str.split('>').str[1].str[:5].isin([x[:5] for x in values_07])
    condition3 = df['Class'].str.contains('>DR')
    filtered_rows = df[condition1 & condition2]
    filtered_rows_dr = df[condition1 & condition3]
#-------------------------------------------------------------------------------------------
    # 엑셀에 해당 행의 값을 출력합니다.
    for index, row in filtered_rows.iterrows():
        db_sid = row['DBSID']  # DBSID 값
        class_value = row['Class'].split('>')[1][:5]  # Class 값의 '>' 다음 문자의 첫 다섯글자를 추출합니다.
        # print(f"현재 처리 중인 행의 DBSID: {db_sid}, Class: {class_value}")

        # DBSID 값과 Class 값이 모두 values_03와 values_07에 있는 경우에만 처리합니다.
        if db_sid in values_03 and any(class_value == x[:5] for x in values_07):
            # DBSID와 Class 값이 모두 일치하는 행에 대해 올바른 엑셀 행 인덱스를 계산합니다.
            row_index_in_excel = None
            for i, (sid, cls,sync) in enumerate(zip(values_03, values_07, values_05)):
                if sid == db_sid and class_value == cls[:5] and '운영' in sync:
                    row_index_in_excel = i + 7
                    break
            
            if row_index_in_excel is not None:
                # print(f"현재 처리 중인 행의 엑셀 행 인덱스: {row_index_in_excel}")

                # 엑셀에 해당 행의 값을 출력합니다.
                for col_index, value in enumerate(row[2:], start=10):  # class,DBSID 값 제외하고 값을 출력합니다.
                    # print(f"현재 처리 중인 엑셀 행의 열 {col_index}의 값: {value}")   
                    worksheet.write(row_index_in_excel, col_index, value, cell_format)

# DataFrame의 'Class' 의 '>' 다음문자가 'DR' 가 아닌 DataFrame을 대상으로, 'DBSID' 값이 'values_03' 값과 같고 'Class'의 '>' 다음 문자가 values_07의 앞 5글자와 같으면 
# DataFrame의 'DBSID' 값이 values_03 값과 같고 'Class'의 '>' 다음 문자가 values_07의 앞 5글자와 같고 'values_05' 내 '운영'이 있는 행의 K:8 부터 DataFrame의 class,DBSID 값 제외하고 EXCEL에 출력                   
#-----------------------------------------------------------------------------------------------DR                        
    for index, row in filtered_rows_dr.iterrows():
        db_sid = row['DBSID']  # DBSID 값
        class_value = row['Class'].split('>')[1][:2]  # Class 값의 '>' 다음 문자의 첫 두글자를 추출합니다.        
        # print(f"현재 처리 중인 행의 DBSID: {db_sid}, Class: {class_value}")

        # DBSID와 Class 값이 모두 values_03와 DR이 있는 경우에 대해서 처리합니다.
        if db_sid in values_03 and 'DR' in class_value:
            # DBSID와 values_05 값이 모두 일치하는 행에 대해 올바른 엑셀 행 인덱스를 계산합니다.
            row_index_in_excel = None
            for i, (sid, sync) in enumerate(zip(values_03, values_05)):
                if sid == db_sid and 'DR' in sync:  # 'DR'을 포함하는지 확인합니다.
                    row_index_in_excel = i + 7  # 엑셀 행 인덱스 계산
                    break

            if row_index_in_excel is not None:
                # print(f"현재 처리 중인 행의 엑셀 행 인덱스: {row_index_in_excel}")

                # 엑셀에 해당 행의 값을 출력합니다.
                for col_index, value in enumerate(row[2:], start=10):  # class,DBSID 값 제외하고 값을 출력합니다.
                    # print(f"현재 처리 중인 엑셀 행의 열 {col_index}의 값: {value}")   
                    worksheet.write(row_index_in_excel, col_index, value, cell_format)
## DataFrame의 'Class' 의 '>' 다음문자가 'DR'인 DataFrame을 대상으로, 'DBSID' 값이 'values_03' 값과 같고 'values_05' 내 'DR'이 있으면, 'DBSID' 값이 'values_03' 값과 같고 'values_05' 내 'DR'이 있는 행을 찾아 결과 값을 출력

#------------------------------
    # 데이터프레임 내용 입력
    # for row_num, values in enumerate(df.values):
    #     for col_num, value in enumerate(values):
    #         worksheet.write(row_num + 8, col_num, value, cell_format)

    # 셀 너비 자동 조절
    # for i, col in enumerate(df.columns):
    #     max_len = max(df[col].astype(str).apply(len).max(), len(col))
    #     worksheet.set_column(i, i, max_len + 2)  # +2는 여유 공간을 위한 것
    
    # 시트 전체의 최대 너비를 설정합니다.
    worksheet.set_column(0, 17,  18)  

    print("데이터프레임이 Excel 파일로 저장되었습니다.")
