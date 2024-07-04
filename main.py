import requests
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat, textFormat, format_cell_range
from utils import get_soul_time

# Google Sheets API 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("./chuny-land-5c8ae110e16d.json", scope)
client = gspread.authorize(creds)

# 구글 시트 열기
spreadsheet = client.open("Chuny_land")
sheet = spreadsheet.sheet1  # 첫 번째 시트를 선택합니다. 시트 이름으로도 접근 가능합니다.

# 구글 시트 초기화
sheet.clear()
sheet.append_row([f"{get_soul_time()} 기준", "","","","신청수"])
sheet.append_row(["순위", "닉네임", "신청댓글", "UP수"])

# 신청수 입력
sheet.update_acell('F1', '=COUNT(A3:A)')

# 데이터 수집 및 입력
base_url = "https://bjapi.afreecatv.com/api/243000/title/129323759/comment"
page = 1
rank = 1
sheet_data = []

while True:
    headers = {
        # 브라우저로만 접속할수있게 제한한듯? 이거 없으면 404에러뜸
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # 필요한 경우 다른 헤더도 추가
        # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        # "Accept-Language": "en-US,en;q=0.5",
        # "Accept-Encoding": "gzip, deflate, br",
        # "Connection": "keep-alive",
        # "Upgrade-Insecure-Requests": "1",
        # "Referer": "https://example.com/",
        # "Cookie": "your_cookie_here",
    }
    response = requests.get(base_url, params={"page": page, "orderby": "like_cnt"},headers=headers)
    response.raise_for_status()  # HTTP 요청 에러를 확인하고, 에러가 있을 경우 예외를 발생시킵니다.
    print(f"request success : page {page}")
    data = response.json()
    
    if not data['data']:
        break

    for item in data['data']:
        user_nick = item['user_nick']
        like_cnt = item['like_cnt']
        comment_link = f"https://bj.afreecatv.com/243000/post/129323759#comment_noti{item['p_comment_no']}"
        sheet_data.append([rank, user_nick, comment_link, like_cnt])
        rank += 1
        

    if page >= data['meta']['last_page']:
        break

    page += 1

cnt = 1
for row in sheet_data:
    time.sleep(1.1)
    sheet.append_row(row)
    print(f"sheet data loading [{cnt}/{len(sheet_data)}]")
    cnt += 1

# 셀 가운데 정렬 설정
fmt = cellFormat(
    textFormat=textFormat(bold=False),
    horizontalAlignment='CENTER',
    verticalAlignment='MIDDLE'
)

# 전체 범위 지정
range_all = f"A1:D999"
format_cell_range(sheet, range_all, fmt)

print("데이터 수집 및 구글 시트 입력이 완료되었습니다.")