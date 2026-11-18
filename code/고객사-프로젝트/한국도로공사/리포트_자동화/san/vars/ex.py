import pandas as pd
import re
import os

# Oracle SID 값을 기반으로 업무 분류를 결정하는 함수 정의
def get_business_category(oracle_sid):
    # Oracle SID 값에 따라 업무 분류를 결정할 수 있는 로직을 추가합니다.
    # 예를 들어, 특정 Oracle SID의 경우 특정 업무 분류를 설정할 수 있습니다.
    # 여기에 필요한 로직을 추가하여 oracle_sid에 따라 업무 분류를 반환합니다.
    # 아래는 예시 코드입니다. 실제 로직에 맞게 수정해주세요.
    if (oracle_sid == 'ADQM' or 
        oracle_sid == 'APGD' or 
        oracle_sid == 'AEVAL' or 
        oracle_sid == 'ASECU' or 
        oracle_sid == 'ADAP' or 
        oracle_sid == 'ANKMIS' or
        oracle_sid == 'ALOGIN' or
        oracle_sid == 'APORTAL' or
        oracle_sid == 'ANKHCG' or
        oracle_sid == 'AEBID19' or
        oracle_sid == 'ALAND' or
        oracle_sid == 'ACRM' or
        oracle_sid == 'ACTI' or
        oracle_sid == 'AIFRS' or
        oracle_sid == 'ALMS' or
        oracle_sid == 'AMOFFICE' or
        oracle_sid == 'AOPEN' or
        oracle_sid == 'ASECDOC' or
        oracle_sid == 'AWWW' or
        oracle_sid == 'CSM' or
        oracle_sid == 'AEXMAIL' or
        oracle_sid == 'GDQM'):
        return '경영'
    elif (oracle_sid == 'ITSDB03' or
        oracle_sid == 'TTPS' or
        oracle_sid == 'TROAD' or
        oracle_sid == 'TIPORTAL' or
        oracle_sid == 'TTPSWAY' or
        oracle_sid == 'SHDAQ' or
        oracle_sid == 'SHBMS' or
        oracle_sid == 'TCBUITSDB1' or
        oracle_sid == 'TCBUITSDB2' or
        oracle_sid == 'TCSCITSDB1' or
        oracle_sid == 'TCSCITSDB2' or
        oracle_sid == 'ftmsdb' or
        oracle_sid == 'terdb'):
        return '교통'
    elif (oracle_sid == 'CBIM' or
        oracle_sid == 'CAIDIM' or
        oracle_sid == 'CBDATA' or
        oracle_sid == 'CFACIL' or
        oracle_sid == 'CHIMAN'):
        return '도로'
    elif (oracle_sid == 'BEREST' or
        oracle_sid == 'BPLM1' or
        oracle_sid == 'BPLM2' or
        oracle_sid == 'BMAX' or
        oracle_sid == 'BOBU' or
        oracle_sid == 'BHIDB' or
        oracle_sid == 'BPGP' or
        oracle_sid == 'BPGPT' or
        oracle_sid == 'BPBS' or
        oracle_sid == 'BPBST' or
        oracle_sid == 'BPBU' or
        oracle_sid == 'BPBUT' or
        oracle_sid == 'BPCN' or
        oracle_sid == 'BPCNT' or
        oracle_sid == 'BPDB' or
        oracle_sid == 'BPDBT' or
        oracle_sid == 'BPGW' or
        oracle_sid == 'BPGWT' or
        oracle_sid == 'BPINTCNDB' or
        oracle_sid == 'BPOCDB' or
        oracle_sid == 'BPOCDBT' or
        oracle_sid == 'BPPS' or
        oracle_sid == 'BPPST' or
        oracle_sid == 'BPSC' or
        oracle_sid == 'BPSCT' or
        oracle_sid == 'BPSG' or
        oracle_sid == 'BPSGT' or
        oracle_sid == 'BPSP' or
        oracle_sid == 'BPSPT' or
        oracle_sid == 'BPSY' or
        oracle_sid == 'BPSYT' or
        oracle_sid == 'BPVIA' or
        oracle_sid == 'BPDS' or
        oracle_sid == 'BPDST' or
        oracle_sid == 'BPIO' or
        oracle_sid == 'BPIOT' or
        oracle_sid == 'BPPH' or
        oracle_sid == 'BPPHT' or
        oracle_sid == 'BPOPR1' or
        oracle_sid == 'BPOPR2' or
        oracle_sid == 'BPTRF1' or
        oracle_sid == 'BPTRF2' or
        oracle_sid == 'BIBAT' or
        oracle_sid == 'BPSTL1' or
        oracle_sid == 'BPSTL2' or
        oracle_sid == 'BIVIA1' or
        oracle_sid == 'BIVIA2' or
        oracle_sid == 'BVIA' or
        oracle_sid == 'dbsvr1' or
        oracle_sid == 'dbsvr2' or
        oracle_sid == 'BPLM'):
        return '영업'
    elif (oracle_sid == 'RECO'):
        return '차세대'
    else:
        return '기타'
    
raw_data = os.environ.get('report_data', '')
save_path = os.environ.get('save_path', '')
output_name = os.environ.get('output_name', '')

# '-' 다음부터 '=' 전까지의 데이터 영역 추출
data_lines = re.search(r'[-]+(.+)[=]+', raw_data, re.DOTALL).group(1).strip().split('\n')[:-1]
print(data_lines)

# DataFrame 생성
columns = ["Policy 명", "업무 분류", "Oracle SID", "arch 사용률", "업데이트 시간"]
df = pd.DataFrame(columns=columns)

# 데이터 추출 및 입력
df["Policy 명"] = [f"{line.split()[0]}_arch_{line.split()[1].lstrip('/').split('_')[0]}" for line in data_lines]
df["업무 분류"] = [get_business_category(line.split()[1].split('/')[-1].replace("/", "_").split('_')[0]) for line in data_lines]
df["Oracle SID"] = [line.split()[1].split('/')[-1].replace("/", "_").split('_')[0] for line in data_lines]
df["arch 사용률"] = [int(line.split()[2]) for line in data_lines]
df["업데이트 시간"] = [line.split()[-1] for line in data_lines]

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