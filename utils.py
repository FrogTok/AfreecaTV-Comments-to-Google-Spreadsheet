import pytz
from datetime import datetime
from pathlib import Path


def get_root_directory_path():
    # 파일 위치가 다른 디렉토리로 바뀌면 수정해야함
    return Path(__file__).parent.resolve()

def get_soul_time():
    # 대한민국 시간대 정의
    seoul_tz = pytz.timezone('Asia/Seoul')

    # 현재 UTC 시간 얻기
    utc_now = datetime.utcnow()

    # UTC 시간을 대한민국 시간대로 변환
    seoul_now = utc_now.replace(tzinfo=pytz.utc).astimezone(seoul_tz)

    # 시간 출력
    return seoul_now.strftime('%Y.%m.%d %H시 %M분')