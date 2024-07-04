from datetime import datetime
import pytz

def get_soul_time():
    # 대한민국 시간대 정의
    seoul_tz = pytz.timezone('Asia/Seoul')

    # 현재 UTC 시간 얻기
    utc_now = datetime.utcnow()

    # UTC 시간을 대한민국 시간대로 변환
    seoul_now = utc_now.replace(tzinfo=pytz.utc).astimezone(seoul_tz)

    # 시간 출력
    return seoul_now.strftime('%Y.%m.%d %H시 %M분')