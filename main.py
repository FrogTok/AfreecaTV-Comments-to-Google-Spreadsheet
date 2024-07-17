import requests
import gspread
import time
import sys
import traceback
import threading
import configparser
import os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit)
from PySide6.QtGui import QIcon
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat, textFormat, format_cell_range, Color
from utils import get_soul_time, get_root_directory_path

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_settings() 

    def initUI(self):
        self.setWindowTitle('아프리카 댓글 줄세우기')
        icon_path = os.path.join(get_root_directory_path(), "assets/afreeca.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(400, 600)

        layout = QVBoxLayout()

        self.url_label = QLabel('게시글 URL:')
        self.url_input = QLineEdit(self)
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)

        self.sheet_label = QLabel('구글 스프래드 시트 이름(없으면 새로 생성):')
        self.sheet_input = QLineEdit(self)
        layout.addWidget(self.sheet_label)
        layout.addWidget(self.sheet_input)

        self.email_label = QLabel('구글 시트 계정(시트 생성할 때 사용):')
        self.email_input = QLineEdit(self)
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)

        self.favorite_label = QLabel('즐찾 컷:')
        self.favorite_input = QLineEdit(self)
        layout.addWidget(self.favorite_label)
        layout.addWidget(self.favorite_input)

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.submit_button = QPushButton('입력', self)
        self.submit_button.clicked.connect(self.start_update_thread)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def log(self, message):
        self.log_text.append(message)

    def load_settings(self):
        config = configparser.ConfigParser()

        if not os.path.exists('settings.ini'):
            with open('settings.ini', 'w') as configfile:
                config['SETTINGS'] = {
                    'base_url': '',
                    'spreadsheet_name': ''
                }
                config.write(configfile)
            self.log("Created new settings.ini file with default values.")
        else:
            config.read('settings.ini')
            self.url_input.setText(config['SETTINGS'].get('base_url', ''))
            self.sheet_input.setText(config['SETTINGS'].get('spreadsheet_name', ''))
            self.email_input.setText(config['SETTINGS'].get('share_email', ''))
            self.favorite_input.setText(config['SETTINGS'].get('favorite_cut', ''))

    def save_settings(self):
        config = configparser.ConfigParser()
        config['SETTINGS'] = {
            'base_url': self.url_input.text(),
            'spreadsheet_name': self.sheet_input.text(),
            'share_email': self.email_input.text(),
            'favorite_cut': self.favorite_input.text()
        }
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)

    def start_update_thread(self):
        self.save_settings() # 업데이트 하기 전에 setting 저장
        self.submit_button.setEnabled(False) # 스레드 완료될 때 까지 입력버튼 비활성화
        update_thread = threading.Thread(target=self.update_sheet)
        update_thread.start()

    def set_sheet_header(self, spreadsheet, sheet):
        # 업로드 날짜 셀 병합
        body = {
            'requests': [{
                'mergeCells': {
                    'range': {
                        'sheetId': sheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 4
                    },
                    'mergeType': 'MERGE_ALL'
                }
            }]
        }
        spreadsheet.batch_update(body)
        # 업로드 날짜 셀 셋팅
        fmt = cellFormat(
            textFormat=textFormat(bold=False, fontSize=26, foregroundColor=Color(1, 0, 0)),
            horizontalAlignment='CENTER',
            verticalAlignment='MIDDLE'
        )
        format_cell_range(sheet, 'A1', fmt)

        # 신청자 수 셀 셋팅
        fmt = cellFormat(
            textFormat=textFormat(bold=True, fontSize=17),
            horizontalAlignment='CENTER',
            verticalAlignment='MIDDLE'
        )
        format_cell_range(sheet, 'E1', fmt)

        # 신청자 수 값 셀 셋팅
        fmt = cellFormat(
            textFormat=textFormat(bold=False, fontSize=21),
            horizontalAlignment='CENTER',
            verticalAlignment='MIDDLE'
        )
        format_cell_range(sheet, 'F1', fmt)

    def request_favorite_cnt(self, bj_id: str):
        api_url = f"https://st.afreecatv.com/api/get_station_status.php?szBjId={bj_id}"
        response = requests.get(api_url)
        response.raise_for_status()  # HTTP 요청 에러를 확인하고, 에러가 있을 경우 예외를 발생시킵니다.
        data = response.json()
        
        if data["RESULT"] == 0:
            return -1
        
        return int(data["DATA"]["fan_cnt"])


    def update_sheet(self):
        post_url = self.url_input.text()
        sheet_name = self.sheet_input.text()
        if not post_url or not sheet_name:
            self.log("Post URL and Spreadsheet Name are required.")
            return
        post_url_split = post_url.split("/")
        bj_id = post_url_split[-3]
        post_id = post_url_split[-1]

        share_email = self.email_input.text()
        favorite_cut = int(self.favorite_input.text())

        try:
            # Google Sheets API 인증
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("./chuny-land-5c8ae110e16d.json", scope)
            client = gspread.authorize(creds)

            # 구글 시트 열기
            try:
                spreadsheet = client.open(sheet_name)
                self.log(f"Spreadsheet '{sheet_name}' opened successfully.")
            except gspread.SpreadsheetNotFound:
            # 구글 시트 생성
                spreadsheet = client.create(sheet_name)
                # 다른 계정에 권한 부여
                if share_email:
                    spreadsheet.share(share_email, perm_type='user', role='writer')
                    self.log(f"Spreadsheet shared with {share_email}")
                self.log(f"Spreadsheet '{sheet_name}' created successfully.")

            sheet = spreadsheet.sheet1  # 첫 번째 시트를 선택합니다. 시트 이름으로도 접근 가능합니다.

            # 구글 시트 초기화
            sheet.clear()
            sheet.append_row([f"{get_soul_time()} 기준", "","","","신청수"])
            self.set_sheet_header(spreadsheet, sheet) # 첫째 줄 글 크기, 색등 셋팅
            sheet.append_row(["순위", "닉네임", "신청댓글", "UP수", f"즐찾 충족 여부({favorite_cut}명)","참가자 한마디"])

            # 신청수 입력
            sheet.update_acell('F1', '=COUNT(A3:A)')

            # 데이터 수집 및 입력
            api_url = f"https://bjapi.afreecatv.com/api/{bj_id}/title/{post_id}/comment"
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
                response = requests.get(api_url, params={"page": page, "orderby": "like_cnt"},headers=headers)
                response.raise_for_status()  # HTTP 요청 에러를 확인하고, 에러가 있을 경우 예외를 발생시킵니다.
                self.log(f"request success : page {page}")
                data = response.json()
                
                if not data['data']:
                    break

                for item in data['data']:
                    user_nick = item['user_nick']
                    like_cnt = item['like_cnt']
                    comment_link = post_url + f"#comment_noti{item['p_comment_no']}"
                    favorite_cnt = self.request_favorite_cnt(item['user_id'])
                    self.log(f"favorite_cnt : {favorite_cnt}")
                    if favorite_cnt >= 0:
                        is_min_favorites_reached = ("O" if  favorite_cnt >= favorite_cut else "X")
                    else :
                        is_min_favorites_reached = "-"
                    comment = item['comment']
                    sheet_data.append([rank, user_nick, comment_link, like_cnt, is_min_favorites_reached, comment])
                    rank += 1

                if page >= data['meta']['last_page']:
                    break

                page += 1

            cnt = 1
            for row in sheet_data:
                time.sleep(1.1)
                sheet.append_row(row)
                self.log(f"sheet data loading [{cnt}/{len(sheet_data)}]")
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

            self.log("Data has been successfully updated in Google Sheets.")
        except Exception as e:
            self.log(f"An error occurred: {e}")
            self.log(traceback.format_exc())

        self.submit_button.setEnabled(True) # 스레드 완료 후 입력버튼 활성화

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())