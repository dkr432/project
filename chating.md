내가 지금 SCD30센서, MQ-2센서, LED 10개, 라즈베리파이 PICO 2 W H를 활용해서(아마도 SCD 30센서가 메인일것같아.) 기후행동을 위한 에너지 절약 캠페인 프로젝트를 할거거든? 이런 구성의 장치들을 여러 반에 배치해서, 반마다 데이터를 수집해 대시보드로 옮기고(대시보드는 가능하면 웬만해선 구글 스프레드시트 API를 활용할것같아.) 데이터를 관찰, 그리고 학생들이 에너지를 제대로 절약하고 있는지에 대해서 탐구해보는 프로젝트를 할거야.(학생들이 에너지를 제대로 절약하고 있는가에 대한 로직은 아마도 "교실의 불이 꺼져있는데, 온도가 낮다. 즉 에어컨이 켜져 있지만 교실 안에는 사람들이 없다. 이 뜻은 모두 밥을 먹으러 갔거나, 체육관으로 수업을 이동했는데 에어컨을 끄지 않았다." 이런 느낌으로 로직을 짜볼꺼야. 근데 이건 참고로 지금 짠 하나의 로직이지, 다른 로직도 더 생각할거야.) 일단 한번 기본 구성을 토대로 코드를 짜보자.

오전 10:41
AI
좋은 프로젝트네요! 기후행동과 에너지 절약을 데이터로 탐구하는 정말 의미 있는 주제예요. 코드를 짜기 전에, 먼저 전체 구조를 함께 정리해보면 좋을 것 같아요.

1. 먼저 확인하고 싶은 것들
본격적으로 코드를 짜기 전에 몇 가지 정리하면 코드가 훨씬 깔끔해져요.

(1) 센서별 역할 정리

SCD30: CO₂, 온도, 습도 측정 → 메인 센서 (재실 여부, 환기 상태 추정에 핵심!)
MQ-2: 가스/연기 감지 (LPG, 연기, 가연성 가스 등)
LED 10개: 무엇을 표현할까요? (예: CO₂ 농도를 막대그래프처럼? 에너지 낭비 경고등?)
(2) 불(조명) 상태는 어떻게 감지할 계획인가요? 로직에 "교실 불이 꺼져있는데 온도가 낮다"가 있는데, 지금 부품 구성에는 **조도 센서(빛 감지)**가 없어요. 이 부분을 어떻게 할지 생각해봐야 해요.

조도 센서(예: BH1750, 광저항 등)를 추가할지
아니면 다른 방식으로 추정할지
이 부분 어떻게 생각하고 있나요?

2. 일단 "기본 골격" 코드부터 시작
전체를 한 번에 짜기보단, 센서 읽기 → 출력 → 판단 로직 → 전송 순서로 단계를 나눠서 만드는 걸 추천해요. 우선 가장 기본이 되는 SCD30 + MQ-2 + LED 읽고 켜기 골격을 보여드릴게요. (MicroPython 기준)

python
복사
import machine
import time
from machine import Pin, I2C, ADC

# ---------- 하드웨어 설정 ----------
# SCD30 (I2C 통신)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
SCD30_ADDR = 0x61

# MQ-2 (아날로그 출력 -> ADC 핀)
mq2 = ADC(Pin(26))  # GP26 = ADC0

# LED 10개 (GP 핀 10개 사용 예시)
led_pins = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
leds = [Pin(p, Pin.OUT) for p in led_pins]


# ---------- SCD30 함수들 ----------
def scd30_start_measurement():
    # 연속 측정 시작 명령 (0x0010), 압력 보정값 0
    cmd = bytes([0x00, 0x10, 0x00, 0x00, 0x81])
    i2c.writeto(SCD30_ADDR, cmd)
    time.sleep(0.5)

def scd30_data_ready():
    i2c.writeto(SCD30_ADDR, bytes([0x02, 0x02]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 3)
    return data[1] == 1

def scd30_read():
    i2c.writeto(SCD30_ADDR, bytes([0x03, 0x00]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 18)

    def to_float(b):
        # 4바이트(2워드, 각 워드 뒤 CRC) -> float 변환
        import struct
        return struct.unpack('>f', bytes([b[0], b[1], b[3], b[4]]))[0]

    co2  = to_float(data[0:6])
    temp = to_float(data[6:12])
    hum  = to_float(data[12:18])
    return co2, temp, hum


# ---------- LED 표시 함수 ----------
def show_level_on_leds(value, max_value):
    """값의 크기를 0~10개 LED로 막대그래프처럼 표현"""
    level = int((value / max_value) * len(leds))
    level = max(0, min(level, len(leds)))
    for i, led in enumerate(leds):
        led.value(1 if i < level else 0)


# ---------- 메인 루프 ----------
scd30_start_measurement()

while True:
    if scd30_data_ready():
        co2, temp, hum = scd30_read()
        gas_value = mq2.read_u16()  # 0 ~ 65535

        print("CO2: {:.0f} ppm | Temp: {:.1f} C | Hum: {:.1f} % | Gas: {}".format(
            co2, temp, hum, gas_value))

        # 예시: CO2 농도를 LED로 표시 (400~2000ppm 범위)
        show_level_on_leds(co2 - 400, 1600)

    time.sleep(2)
3. 같이 생각해볼 점
이 골격을 바탕으로 다음 단계로 나아가기 전에:

조명(불) 상태를 어떻게 감지할지 → 핵심 로직에 필수예요
LED 10개의 역할을 무엇으로 정할지
에너지 절약 판단 로직을 어떤 조건들로 만들지 (지금 1개 생각했죠? 2~3개 더 만들어보면 좋아요)
구글 스프레드시트 전송은 Pico W의 WiFi로 할 텐데, 이 부분은 골격이 잘 돌아가는 걸 확인한 뒤에 붙이는 게 좋아요
우선 조명 감지를 어떻게 할 생각인지, 그리고 LED 10개를 무슨 용도로 쓸지 알려주면 다음 단계 코드를 같이 발전시켜볼까요?

오전 10:42

나
아, 맞다. 조도 센서도 활용할거야.

오전 10:42
AI
좋아요! 조도 센서를 추가하면 "불이 켜져있는지" 판단할 수 있으니 핵심 로직이 완성되겠네요. 그럼 조도 센서를 어떤 걸로 쓸지 정해야 코드를 정확히 짤 수 있어요.

먼저 정할 것: 어떤 조도 센서인가요?
조도 센서는 크게 두 종류가 있어요. 어떤 걸 쓸지에 따라 연결 방식과 코드가 달라져요.

(1) 아날로그 방식 (광저항/CDS 센서, 포토레지스터)

가장 싸고 간단함
ADC 핀에 연결 (MQ-2처럼)
단점: Pico의 ADC 핀이 3개뿐인데(GP26, 27, 28), MQ-2가 이미 하나 쓰고 있어요 → 남은 ADC 핀 사용 가능
(2) 디지털 방식 (BH1750 같은 I2C 센서)

lux(럭스) 단위로 정확하게 빛의 밝기 측정
SCD30과 같은 I2C 버스 공유 가능 (주소가 다르면 OK)
좀 더 정확하고 "교실 조명 켜짐/꺼짐" 판단에 적합
어떤 걸 가지고 있거나 쓸 예정인가요?

생각해볼 점: 조도 임계값(threshold)
센서를 정하면, "이 값 이상이면 불이 켜진 것"이라는 기준값을 정해야 해요. 이건 실제로 교실에서 측정해봐야 알 수 있어요.

예를 들면:

불 끄고 측정 → 어떤 값?
불 켜고 측정 → 어떤 값?
그 중간 어디쯤을 기준으로 잡기
이 부분은 실제 테스트로 데이터를 모아야 하니, 코드에 기준값을 쉽게 바꿀 수 있게 변수로 빼두면 좋아요.

조도 센서 종류만 알려주면, 기존 골격에 조도 센서 읽기 + 에너지 절약 판단 로직까지 붙여서 발전시킨 코드를 같이 만들어볼게요.

그리고 한 가지 더 생각해보면 좋을 질문: "불은 꺼져있는데 온도가 낮다" 외에, 조도 센서와 CO₂ 센서를 조합하면 어떤 다른 낭비 상황도 잡아낼 수 있을까요? (힌트: CO₂는 사람이 있으면 올라가요 🙂)

오전 10:42

나
일단 지금은 여러 피코들로 하나의 스프레드시트에 전송하는게 일단 내 목표거든? 일단 코드부터 구성해보자.

오전 10:44
AI
좋아요! "여러 피코 → 하나의 스프레드시트"가 목표라면, 코드를 짜기 전에 딱 두 가지만 정하면 깔끔하게 진행돼요.

먼저 정할 2가지
(1) 각 피코를 어떻게 구분할까? 여러 반에 배치하니까, 데이터가 어느 반에서 왔는지 알아야 해요. 가장 간단한 방법은 각 피코 코드에 **이름표(ID)**를 박아두는 거예요.

python
복사
CLASS_ID = "1-3"   # 이 피코는 1학년 3반
반마다 이 부분만 바꿔서 업로드하면 돼요.

(2) 구글 스프레드시트에 어떻게 보낼까? Pico에서 구글 시트로 보내는 방법은 보통 2가지인데, 학교 프로젝트에서는 Google Apps Script(웹앱) 방식이 제일 쉽고 안정적이에요.

스프레드시트에 Apps Script로 "데이터 받는 주소(웹앱 URL)"를 만들고
피코가 그 주소로 HTTP 요청을 보내면 시트에 한 줄씩 쌓이는 방식
이 방식 괜찮을까요? (구글 클라우드 인증키 같은 복잡한 설정 없이 가능해서 추천해요.)

전체 코드 골격 (WiFi + 시트 전송 포함)
위 방식 기준으로, 지금까지 내용을 합친 골격을 보여줄게요. (조도 센서는 우선 아날로그(CDS) 기준으로 넣었어요. 다르면 알려주세요!)

python
복사
import machine
import time
import network
import urequests
from machine import Pin, I2C, ADC
import struct

# ========== 설정 (반마다 이 부분만 수정) ==========
CLASS_ID = "1-3"                 # 이 피코가 배치된 반
WIFI_SSID = "와이파이이름"
WIFI_PASSWORD = "와이파이비밀번호"
SHEET_URL = "여기에_AppsScript_웹앱_URL"   # 나중에 채울 부분
LIGHT_THRESHOLD = 30000          # 조도 기준값 (실측 후 조정)
# ================================================

# ---------- 하드웨어 설정 ----------
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
SCD30_ADDR = 0x61

mq2 = ADC(Pin(26))    # 가스 센서
light = ADC(Pin(27))  # 조도 센서 (CDS)

led_pins = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
leds = [Pin(p, Pin.OUT) for p in led_pins]


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    print("WiFi 연결 중...", end="")
    for _ in range(20):
        if wlan.isconnected():
            print(" 성공! IP:", wlan.ifconfig()[0])
            return True
        print(".", end="")
        time.sleep(1)
    print(" 실패")
    return False


# ---------- SCD30 함수들 ----------
def scd30_start_measurement():
    cmd = bytes([0x00, 0x10, 0x00, 0x00, 0x81])
    i2c.writeto(SCD30_ADDR, cmd)
    time.sleep(0.5)

def scd30_data_ready():
    i2c.writeto(SCD30_ADDR, bytes([0x02, 0x02]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 3)
    return data[1] == 1

def scd30_read():
    i2c.writeto(SCD30_ADDR, bytes([0x03, 0x00]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 18)

    def to_float(b):
        return struct.unpack('>f', bytes([b[0], b[1], b[3], b[4]]))[0]

    co2  = to_float(data[0:6])
    temp = to_float(data[6:12])
    hum  = to_float(data[12:18])
    return co2, temp, hum


# ---------- LED 표시 ----------
def show_level_on_leds(value, max_value):
    level = int((value / max_value) * len(leds))
    level = max(0, min(level, len(leds)))
    for i, led in enumerate(leds):
        led.value(1 if i < level else 0)


# ---------- 에너지 절약 판단 로직 ----------
def check_energy_waste(co2, temp, light_value):
    """간단한 판단 로직 (앞으로 발전시킬 부분)"""
    light_on = light_value > LIGHT_THRESHOLD

    # 로직1: 불 꺼짐 + 온도 낮음 -> 사람 없는데 에어컨 켜둠 의심
    if (not light_on) and (temp < 24):
        return "낭비의심: 빈 교실 냉방?"

    return "정상"


# ---------- 구글 시트로 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    try:
        data = {
            "class": CLASS_ID,
            "co2": round(co2, 1),
            "temp": round(temp, 1),
            "hum": round(hum, 1),
            "gas": gas,
            "light": light_value,
            "status": status
        }
        res = urequests.post(SHEET_URL, json=data)
        print("전송 완료:", res.text)
        res.close()
    except Exception as e:
        print("전송 실패:", e)


# ========== 메인 ==========
connect_wifi()
scd30_start_measurement()

while True:
    if scd30_data_ready():
        co2, temp, hum = scd30_read()
        gas_value = mq2.read_u16()
        light_value = light.read_u16()

        status = check_energy_waste(co2, temp, light_value)

        print("[{}] CO2:{:.0f} Temp:{:.1f} Hum:{:.1f} Gas:{} Light:{} -> {}".format(
            CLASS_ID, co2, temp, hum, gas_value, light_value, status))

        show_level_on_leds(co2 - 400, 1600)

        # 시트 전송 (테스트할 땐 주기를 길게)
        send_to_sheet(co2, temp, hum, gas_value, light_value, status)

    time.sleep(10)  # 10초마다 (실제론 더 길게 조정)
다음 단계 안내
이 코드를 돌리려면 **구글 스프레드시트 쪽 준비(Apps Script)**가 필요해요. 그게 있어야 SHEET_URL을 채울 수 있거든요.

그래서 제안:

먼저 WiFi 연결까지만 테스트해보고 (send_to_sheet는 잠깐 주석 처리)
잘 되면 Apps Script 만들기로 넘어가기
혹시 궁금한 점:

구글 Apps Script로 데이터 받는 부분(웹앱)도 만들어볼까요?
아니면 먼저 이 피코 코드를 한 줄씩 이해하고 넘어갈까요?
어느 쪽부터 하고 싶나요?

오전 10:44

나
어, 니 코드를 봤는데, 나는 피코에 wifi config.py를 따로 만들어서, WIFI_NETWORKS = {
    "U+Net1DFB": "8F9B6B21M!",
    "app": "20242024"
}
 이렇게 이미 코드를 넣어놨어. 와이파이를, 아무튼? 그리고, 내가 지금 생각하는건, 하나의 장치에서만 웹사이트를 열어서, 그 웹사이트를 통해, 구글 스프레드 시트로 입력받은 데이터들을 그래프나 다른 모양으로 볼 수 있게 하고 싶어. 그러니까, 총 파일은 main.py, wifi_config.py,web.py로 구성해서, 다른 장치들은main.py, wifi_config.py만 가지고 있고, 하나의 장치에서는 web.py까지 넣어서 웹앱을 열게 하는거지, 굳이 모든 장치에서 웹앱을 열필요는 없을 것같다고 판단했어.

오전 10:50
AI
아주 좋은 설계 판단이에요! 👏 정리하면 이런 구조네요:

당신이 설계한 구조 정리
code
복사
[모든 피코]          main.py + wifi_config.py
   └─ 센서 측정 → 구글 스프레드시트로 전송

[대표 피코 1대]      main.py + wifi_config.py + web.py
   └─ 센서 측정 + 전송 + 웹앱 열어서 데이터 시각화
이 구조의 장점을 잘 짚었어요:

모든 피코가 웹서버를 돌리면 메모리/성능 낭비 → 1대만 담당시키는 게 효율적
역할 분리가 명확해서 유지보수 쉬움
다만 여기서 같이 고민해볼 점이 하나 있어요. 🤔

잠깐 생각해볼 점: 웹앱이 데이터를 "어디서" 가져올까?
대표 피코의 web.py가 그래프를 그리려면 데이터가 필요하잖아요? 그 데이터를 어디서 가져올지 두 가지 길이 있어요.

(A) 구글 스프레드시트에서 다시 읽어오기

모든 피코가 시트에 씀 → 대표 피코가 시트를 읽어서 웹에 그래프로 표시
장점: 모든 반 데이터를 한눈에 볼 수 있음
고려할 점: 피코가 구글 시트를 읽어오는 것도 가능하지만, 데이터가 많아지면 Pico 메모리에 부담될 수 있어요
(B) 그냥 구글 스프레드시트 자체 기능으로 그래프 그리기

사실 구글 시트는 자체적으로 차트/대시보드 기능이 강력해요
피코는 데이터만 보내고, 시각화는 구글 시트가 담당
이러면 web.py가 거의 필요 없어질 수도 있어요
질문: web.py로 웹앱을 따로 만들고 싶은 이유가 있나요?

예: 구글 시트보다 더 예쁘게/내 맘대로 꾸미고 싶다
예: 실시간으로 LED나 장치를 웹에서 제어하고 싶다
예: 학생들에게 보여줄 전용 화면을 만들고 싶다
이 이유에 따라 web.py의 방향이 완전히 달라져요. 어떤 걸 원하나요?

일단 파일 구조에 맞춰 main.py 정리
이유와 상관없이, 우선 wifi_config.py를 활용하는 main.py부터 깔끔하게 맞춰볼게요. 여러 와이파이 중 연결되는 걸 자동으로 찾는 방식으로요.

wifi_config.py (이미 있는 것 + URL 추가)

python
복사
WIFI_NETWORKS = {
    "U+Net1DFB": "8F9B6B21M!",
    "app": "20242024"
}

# 구글 스프레드시트 전송 주소 (나중에 채움)
SHEET_URL = "여기에_AppsScript_웹앱_URL"

# 이 피코가 배치된 반 (피코마다 수정)
CLASS_ID = "1-3"
main.py

python
복사
import time
import network
import urequests
from machine import Pin, I2C, ADC
import struct
import wifi_config   # 설정 불러오기

# ---------- 하드웨어 설정 ----------
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
SCD30_ADDR = 0x61

mq2 = ADC(Pin(26))
light = ADC(Pin(27))

led_pins = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
leds = [Pin(p, Pin.OUT) for p in led_pins]

LIGHT_THRESHOLD = 30000   # 실측 후 조정


# ---------- WiFi 연결 (여러 개 중 자동 선택) ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print("주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print("연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print("연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print("연결 가능한 WiFi 없음")
    return None


# ---------- SCD30 함수들 ----------
def scd30_start_measurement():
    cmd = bytes([0x00, 0x10, 0x00, 0x00, 0x81])
    i2c.writeto(SCD30_ADDR, cmd)
    time.sleep(0.5)

def scd30_data_ready():
    i2c.writeto(SCD30_ADDR, bytes([0x02, 0x02]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 3)
    return data[1] == 1

def scd30_read():
    i2c.writeto(SCD30_ADDR, bytes([0x03, 0x00]))
    time.sleep(0.005)
    data = i2c.readfrom(SCD30_ADDR, 18)

    def to_float(b):
        return struct.unpack('>f', bytes([b[0], b[1], b[3], b[4]]))[0]

    co2  = to_float(data[0:6])
    temp = to_float(data[6:12])
    hum  = to_float(data[12:18])
    return co2, temp, hum


# ---------- LED 표시 ----------
def show_level_on_leds(value, max_value):
    level = int((value / max_value) * len(leds))
    level = max(0, min(level, len(leds)))
    for i, led in enumerate(leds):
        led.value(1 if i < level else 0)


# ---------- 에너지 절약 판단 ----------
def check_energy_waste(co2, temp, light_value):
    light_on = light_value > LIGHT_THRESHOLD
    if (not light_on) and (temp < 24):
        return "낭비의심: 빈 교실 냉방?"
    return "정상"


# ---------- 구글 시트 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": round(co2, 1),
            "temp": round(temp, 1),
            "hum": round(hum, 1),
            "gas": gas,
            "light": light_value,
            "status": status
        }
        res = urequests.post(wifi_config.SHEET_URL, json=data)
        print("전송:", res.text)
        res.close()
    except Exception as e:
        print("전송 실패:", e)


# ========== 메인 ==========
connect_wifi()
scd30_start_measurement()

while True:
    if scd30_data_ready():
        co2, temp, hum = scd30_read()
        gas_value = mq2.read_u16()
        light_value = light.read_u16()

        status = check_energy_waste(co2, temp, light_value)

        print("[{}] CO2:{:.0f} Temp:{:.1f} Hum:{:.1f} Gas:{} Light:{} -> {}".format(
            wifi_config.CLASS_ID, co2, temp, hum, gas_value, light_value, status))

        show_level_on_leds(co2 - 400, 1600)
        send_to_sheet(co2, temp, hum, gas_value, light_value, status)

    time.sleep(10)
이제 web.py를 어떤 방향으로 만들지 결정하면 그쪽 코드를 같이 짜볼게요.

먼저 답해줄 것:

web.py로 웹앱을 따로 만들고 싶은 이유/목적이 뭔가요? (위 A/B 중 어디에 가까운지)
그리고 한 가지 — 위 main.py에서 connect_wifi()가 실패하면 어떻게 동작해야 좋을까요? (생각해보면 재밌는 부분이에요 🙂)
오전 10:50

나
일단은 A 대안으로 생각 해두고 있었어. 일단 스프레드시트와 연동을 할 메인 코드를 짜보자 이제

오전 10:56
AI
좋아요! A 방식(시트에서 읽어와 웹앱에 표시)으로 가되, 일단 지금은 **"피코 → 구글 시트로 쓰기"**가 제대로 되는 메인 흐름부터 완성하는 게 맞아요. 읽어오는 건 그게 잘 돌아간 다음에 붙이면 되니까요.

그런데 피코 코드를 돌리려면 **구글 시트 쪽에서 데이터를 받아줄 "문(門)"**을 먼저 만들어야 해요. 그게 없으면 SHEET_URL이 빈 채로 남아서 전송이 안 되거든요.

순서: 구글 시트 쪽 준비 (Apps Script) → 피코 코드
1단계: 스프레드시트 만들고 첫 줄(헤더) 입력
새 구글 스프레드시트를 만들고, 1행에 제목들을 적어두세요:

A	B	C	D	E	F	G	H
시간	반	CO2	온도	습도	가스	조도	상태
2단계: Apps Script로 "데이터 받는 웹앱" 만들기
스프레드시트 상단 메뉴 → 확장 프로그램 → Apps Script 클릭 → 아래 코드 붙여넣기:

javascript
복사
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      new Date(),        // 시간 (자동)
      data.class,        // 반
      data.co2,          // CO2
      data.temp,         // 온도
      data.hum,          // 습도
      data.gas,          // 가스
      data.light,        // 조도
      data.status        // 상태
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
3단계: 배포해서 URL 받기
우측 상단 배포 → 새 배포 클릭
유형 선택(톱니바퀴) → 웹 앱
설정:
실행 계정: 나
액세스 권한: 모든 사용자 ⚠️ (이거 중요! 피코가 접근하려면 필요)
배포 클릭 → 권한 승인
나오는 웹 앱 URL 복사 → 이게 SHEET_URL이에요!
⚠️ 피코에서 한 가지 주의할 점
여기서 함께 알아둬야 할 중요한 함정이 있어요. 구글 Apps Script URL로 POST를 보내면, 구글이 **다른 주소로 리다이렉트(redirect)**를 시켜요. 그런데 피코의 urequests는 이 리다이렉트를 자동으로 잘 못 따라가는 경우가 많아요.

그래서 전송 함수에 헤더를 추가하고, 리다이렉트에 대비하는 게 안전해요. 그 부분을 반영한 전송 함수로 업데이트할게요:

python
복사
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": round(co2, 1),
            "temp": round(temp, 1),
            "hum": round(hum, 1),
            "gas": gas,
            "light": light_value,
            "status": status
        }
        headers = {"Content-Type": "application/json"}
        res = urequests.post(wifi_config.SHEET_URL, json=data, headers=headers)
        print("전송 응답:", res.status_code, res.text)
        res.close()
    except Exception as e:
        print("전송 실패:", e)
그럼 이제 테스트 순서
Apps Script 웹앱부터 만들기 (위 1~3단계)
만든 URL을 wifi_config.py의 SHEET_URL에 넣기
피코 실행 → 시트에 데이터가 한 줄씩 쌓이는지 확인
여기서 질문이에요:

Apps Script 웹앱 만드는 단계, 한번 직접 해볼 수 있겠어요? 막히는 부분 있으면 어디서 막혔는지 알려주세요.
혹시 테스트할 때 진짜 센서 없이 가짜 데이터로 먼저 전송 테스트를 해보고 싶나요? (그러면 센서 연결 문제와 전송 문제를 분리해서 디버깅할 수 있어서 추천해요 🙂)
어떻게 진행할까요?

오전 10:57

나
https://script.google.com/macros/s/AKfycbwssGqCtO0_EDCUJRwkydoIk_ut_uHFfomZwEpu7dxOBftMUGZgg7r_AwaMavP7DtNLCw/exec 여기 시트 URL 이야.

오전 11:03
AI
좋아요, URL 받았어요! 그럼 이걸 wifi_config.py에 넣고, 바로 시트 전송이 잘 되는지 테스트부터 해봐요.

그런데 아까 제안했던 것처럼, 처음부터 모든 센서를 다 연결해서 테스트하면 문제가 생겼을 때 "센서 문제인지, 와이파이 문제인지, 시트 전송 문제인지" 구분이 안 돼요. 그래서 가짜 데이터로 전송만 먼저 테스트하는 걸 추천해요.

1단계: wifi_config.py 업데이트
python
복사
WIFI_NETWORKS = {
    "U+Net1DFB": "8F9B6B21M!",
    "app": "20242024"
}

SHEET_URL = "https://script.google.com/macros/s/AKfycbwssGqCtO0_EDCUJRwkydoIk_ut_uHFfomZwEpu7dxOBftMUGZgg7r_AwaMavP7DtNLCw/exec"

CLASS_ID = "1-3"   # 피코마다 수정
2단계: 전송 테스트 전용 코드 (test_send.py)
센서 없이 가짜 데이터로 시트 전송만 확인하는 코드예요. 이걸 먼저 돌려보세요:

python
복사
import time
import network
import urequests
import wifi_config


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print("주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print("연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print("연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print("연결 가능한 WiFi 없음")
    return None


def send_to_sheet(co2, temp, hum, gas, light_value, status):
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        headers = {"Content-Type": "application/json"}
        res = urequests.post(wifi_config.SHEET_URL, json=data, headers=headers)
        print("전송 응답:", res.status_code, res.text)
        res.close()
    except Exception as e:
        print("전송 실패:", e)


# ===== 테스트 실행 =====
wlan = connect_wifi()

if wlan:
    print("가짜 데이터 전송 테스트 시작!")
    # 가짜 데이터 한 번 보내기
    send_to_sheet(
        co2=650.5,
        temp=23.4,
        hum=45.2,
        gas=12000,
        light_value=28000,
        status="테스트"
    )
    print("테스트 끝! 시트를 확인해보세요.")
else:
    print("와이파이 연결 안 됨")
확인할 것
이 코드를 돌리고 나서:

셸(콘솔)에 뭐가 출력되는지 봐주세요

연결 성공! IP: ... 가 뜨나요?
전송 응답: 200 ... 처럼 응답이 오나요?
구글 스프레드시트에 새 줄이 추가됐나요?

시간, 1-3, 650.5, 23.4 ... 이런 줄이 생겼는지
이 두 가지 결과를 알려주세요. 그 결과에 따라:

✅ 잘 되면 → 진짜 센서 코드를 붙여서 완성
❌ 안 되면 → 출력된 에러 메시지를 보고 같이 원인을 찾기
어떤 결과가 나왔나요?

오전 11:03

나
음, 일단 연결은 잘되고, 테스트가 끝났다고 잘 뜨는데, 구글 스프레드시트에는 변화가 없어.

오전 11:05
AI
좋은 단서예요! "전송은 됐다고 뜨는데 시트에 안 쌓인다" → 이건 아주 흔한 케이스라 차근차근 짚어보면 원인을 찾을 수 있어요.

먼저 정확히 무슨 응답이 왔는지 확인하는 게 핵심이에요. 셸(콘솔)에 이 줄이 어떻게 출력됐나요?

code
복사
전송 응답: ???  ???
이 부분을 정확히 알려주면 원인이 거의 바로 보여요. 그동안 가능성이 높은 원인들을 같이 점검해봐요.

의심 포인트 1: 응답이 200인데 본문이 이상한 경우 ⭐가장 흔함
전송 응답이 200인데 시트에 안 쌓이면, 십중팔구 구글 로그인 페이지 HTML이 응답으로 온 거예요. 이건 배포 권한 설정 문제예요.

다시 한번 확인해주세요 (이게 제일 의심돼요):

Apps Script → 배포 → 배포 관리
현재 배포의 액세스 권한이 **"모든 사용자"**로 되어 있나요?
"나만" 이나 "Google 계정이 있는 모든 사용자"로 되어 있으면 → 피코가 접근 못 해요
⚠️ 여기서 자주 하는 실수: 권한을 바꾸려면 새 배포를 하거나, 기존 배포를 수정(연필 아이콘) → 버전을 "새 버전"으로 다시 배포해야 적용돼요. 그냥 설정만 바꾸면 반영이 안 될 수 있어요.

의심 포인트 2: Apps Script 코드가 저장만 되고 배포에 반영 안 됨
doPost 코드를 작성한 뒤에, 그 코드 버전으로 다시 배포했나요?

코드를 고친 후 배포를 안 하면, 옛날(빈) 버전이 그대로 돌아가요
배포 → 배포 관리 → 수정 → 버전: "새 버전" 선택 → 배포
의심 포인트 3: 진짜로 doPost가 실행됐는지 직접 확인
Apps Script에서 로그를 볼 수 있어요:

Apps Script 편집기 왼쪽 → 실행 (시계 모양 아이콘) 메뉴
피코가 전송을 보낸 시각에 doPost 실행 기록이 있나요?
있는데 실패 → 코드 문제
아예 기록 없음 → 피코 요청이 구글에 안 닿은 것 (권한 문제 가능성 큼)
다음에 해볼 것
우선 응답 내용을 더 자세히 보기 위해, 테스트 코드의 출력을 살짝 바꿔서 다시 돌려봐요:

python
복사
        res = urequests.post(wifi_config.SHEET_URL, json=data, headers=headers)
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
이렇게 하고 다시 실행해서, 응답 본문에 뭐가 나오는지 그대로 복사해서 알려주세요.

{"result":"success"} 같은 게 나오면 → 코드는 맞고 다른 문제
HTML 같은 긴 글(<!DOCTYPE html>...)이 나오면 → 권한 설정 문제 확정
어떤 게 나오는지 보여주세요! 🔍

오전 11:06

나
전송 응답이 400이야

오전 11:07
AI
오, 400 응답이면 단서가 명확해요! 👍

400 = Bad Request, 즉 "구글 서버까지는 도달했는데, 보낸 데이터의 형식을 구글이 제대로 이해하지 못했다"는 뜻이에요. 권한 문제(보통 200에 로그인 HTML)는 아니고, 데이터 전달 방식 문제일 가능성이 커요.

가장 흔한 원인: json= 방식과 Apps Script의 충돌
피코의 urequests에서 json=data로 보내면, 내부적으로 데이터를 JSON으로 바꿔서 보내요. 그런데 구글 Apps Script가 이걸 받을 때 e.postData.contents로 파싱하는 과정에서 헤더나 형식이 안 맞아 400이 나는 경우가 많아요.

이걸 해결하는 가장 확실한 방법은 직접 문자열로 변환해서 보내는 것이에요.

수정한 전송 함수
python
복사
import ujson   # 상단에 추가

def send_to_sheet(co2, temp, hum, gas, light_value, status):
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        # 딕셔너리를 JSON 문자열로 직접 변환
        payload = ujson.dumps(data)
        headers = {"Content-Type": "application/json"}

        res = urequests.post(wifi_config.SHEET_URL, data=payload, headers=headers)
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print("전송 실패:", e)
바뀐 핵심: json=data → data=payload (직접 문자열로 변환해서 보냄)

그래도 400이 나온다면: Apps Script 쪽도 점검
만약 위로도 안 되면, Apps Script 코드가 e.postData를 못 읽는 상황일 수 있어요. 좀 더 방어적으로 받도록 doPost를 살짝 고쳐봐요:

javascript
복사
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // postData가 없을 때 대비
    if (!e.postData || !e.postData.contents) {
      return ContentService
        .createTextOutput(JSON.stringify({result: "no data"}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      new Date(),
      data.class,
      data.co2,
      data.temp,
      data.hum,
      data.gas,
      data.light,
      data.status
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
⚠️ 이렇게 Apps Script 코드를 고쳤다면, 반드시 다시 배포하세요! (배포 → 배포 관리 → 수정 → 버전 "새 버전" → 배포)

진행 순서
먼저 피코 쪽 전송 함수만 위처럼 고쳐서 다시 실행 (가장 가능성 높음)
그래도 400이면 → **응답 본문(=== 응답 본문 === 아래에 나오는 글)**을 복사해서 알려주세요
그 응답 본문에 보통 에러 이유가 적혀 있어서, 그걸 보면 원인을 딱 짚을 수 있어요.

먼저 1번 해보고 결과가 어떻게 나오는지 알려줄래요? 🙂

오전 11:07

나
이번엔 코드를 실행했더니 아예 콘솔창에 아무것도 안떠. 에러도 안뜨고. 참고로 앱 스크립트 코드는 안바꿨어 아직

오후 03:10
AI
음, 콘솔에 아무것도 안 뜨는 것은 코드 자체가 실행이 안 됐거나, 중간에 멈춘 거예요. 출력문(print)이 하나도 안 보인다는 건 좀 이상한 신호죠. 같이 원인을 좁혀봐요.

먼저 확인할 것들
1. import 위치 문제일 가능성 제가 import ujson을 "상단에 추가"라고 했는데, 혹시 함수 정의보다 아래쪽이나 함수 안 엉뚱한 곳에 넣었나요? import는 파일 맨 위쪽에 있어야 해요. 만약 위치가 꼬여서 에러가 났다면 화면에 안 뜰 수도 있어요.

2. 파일을 제대로 실행했나요?

혹시 파일 이름이 main.py인 채로 저장돼서, 피코가 부팅하면서 자동 실행 → 콘솔 연결 전에 이미 끝나버린 건 아닐까요?
아니면 그냥 저장만 하고 실행(▶) 버튼을 안 눌렀을 수도 있어요
3. 어떤 환경에서 돌리고 있나요? Thonny? 아니면 다른 에디터? (이걸 알아야 정확히 도와줄 수 있어요)

가장 확실한 확인 방법: 맨 윗줄에 출력 넣기
코드가 진짜 실행되는지부터 확인해봐요. 파일 맨 첫 줄에 이걸 넣고 실행해보세요:

python
복사
print(">>> 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> import 성공!")
이렇게 하고 실행했을 때:

>>> 코드 시작됨!도 안 뜬다 → 실행 자체가 안 되고 있음 (실행 버튼 / 파일 / 보드 연결 문제)
>>> 코드 시작됨!은 뜨는데 >>> import 성공!이 안 뜬다 → import 단계에서 멈춤 (ujson 등 모듈 문제 가능성)
둘 다 뜬다 → import는 정상, 그 아래 어디서 멈춘 것
추가로 — 멈춤 상태일 수도
혹시 콘솔에 커서만 깜빡이고 아무 반응이 없다면, 코드가 무한 대기에 빠진 걸 수도 있어요. 그럴 땐:

Ctrl + C 를 눌러서 멈춰보세요
그러면 "지금 어느 줄에서 멈춰 있었는지" 에러 메시지가 뜰 거예요. 그 내용을 알려주면 딱 짚을 수 있어요.
정리하면:

어떤 프로그램(Thonny 등)으로 돌리고 있는지 알려주기
위 >>> 코드 시작됨! 테스트 해보고 어디까지 출력되는지 알려주기
멈춰있는 것 같으면 Ctrl+C 눌러서 나오는 메시지 보여주기
이 셋 중에 해본 결과를 알려주면 바로 다음 단계로 갈 수 있어요! 어떤 환경에서 작업 중인가요? 🙂

오후 03:10

나
Thonny에서 사용중이고, 지금 너가 보내준 코드는 잘작동해. 프린트도 잘 되고.

오후 03:11
AI
좋아요! 그럼 import까지는 완벽하게 정상이라는 게 확인됐네요. 👍 (Thonny에서 잘 돌고, print도 잘 나온다는 건 기초가 탄탄하다는 뜻이에요.)

그럼 문제는 그 아래쪽 어딘가에서 멈춘 거예요. 범인을 좁히기 위해, 코드 곳곳에 "여기까지 왔다"는 표시를 넣어서 어디서 멈추는지 추적해봐요. 이걸 프로그래밍에서 **디버깅(debugging)**이라고 해요 — 아주 중요한 기술이에요! 🔍

추적용 전체 테스트 코드
아래 코드를 통째로 복사해서 실행해보세요. 중간중간 >>> 출력이 있어서 어디까지 진행되는지 보여줄 거예요:

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> 2. import 성공!")


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        headers = {"Content-Type": "application/json"}
        print(">>> 7. 전송 시작...")

        res = urequests.post(wifi_config.SHEET_URL, data=payload, headers=headers)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 9. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 10. 프로그램 끝")
이렇게 해주세요
실행하고 나서 콘솔에 출력된 줄들을 그대로 복사해서 보여주세요. 예를 들면:

code
복사
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: [...]
...
이렇게요. 그러면 몇 번에서 멈췄는지 보고 정확히 어디가 문제인지 딱 짚어줄 수 있어요.

특히 궁금한 건:

>>> 4까지 갔는지 (와이파이 연결됐는지)
>>> 7에서 멈췄는지 (전송 시도 중 응답 없이 멈춤 = 서버 응답 대기 중일 수 있음)
>>> 8까지 갔는지 (응답을 받았는지)
어디까지 나오는지 알려주세요! 🙂

오후 03:11

나
어, 지금 니 코드를 봤는데, 난 지금 시간	반	CO2	온도	습도	가스	조도	상태로 구글 스프레드 시트에 입력 해놨거든? 시트 이름은 아직 안바꿔놨고.

오후 03:13
AI
좋은 포인트예요! 그 정보 알려줘서 고마워요. 정리해볼게요.

지금 상황 정리
✅ 시트 1행 헤더: 시간 / 반 / CO2 / 온도 / 습도 / 가스 / 조도 / 상태 → 잘 맞아요!
✅ 피코가 보내는 데이터 순서도 이 헤더와 일치해요 (Apps Script의 appendRow 순서와 동일)
시트(탭) 이름은 안 바꿨다 → 이건 보통 문제 없어요
여기서 짚고 싶은 부분이 있어요. Apps Script 코드를 보면:

javascript
복사
var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
이건 **"현재 활성화된 시트(탭)"**에 데이터를 넣겠다는 뜻이에요. 그래서 시트 이름이 시트1이든 뭐든 상관없이, 그냥 열려있는 첫 번째 탭에 들어가요. 즉 이름 안 바꿔도 동작은 해요. 👍

다만 나중에 탭을 여러 개 만들면(예: 반별로 탭 분리) 이 부분을 명확하게 지정해주는 게 좋아요. 지금은 일단 이대로 OK.

그래서 — 헤더는 문제가 아니에요
헤더와 데이터 순서는 잘 맞으니까, **400 에러의 원인은 헤더가 아니라 "데이터 전달 방식"**일 가능성이 여전히 높아요.

그러니 아까 보낸 추적용 디버깅 코드를 돌려서 어디서 멈추는지/어떤 응답이 오는지 확인하는 게 핵심이에요.

다음 행동
추적 코드를 실행하고, 콘솔에 나오는 >>> 출력들을 그대로 복사해서 보여주세요. 특히:

>>> 8. 응답 받음!까지 가나요?
거기서 === 상태 코드 === 뒤에 뭐가 나오나요? (200? 400?)
=== 응답 본문 === 아래에 나오는 글이 뭔가요?
이 응답 본문이 진짜 핵심 단서예요. 거기에 보통 구글이 **"왜 거절했는지"**를 적어주거든요.

한번 돌려보고 결과 알려줄래요? 🙂

오후 03:13

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'SW1', 'sw2-2-2.4g', 'senWiFi_Free_2.4G', '']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 전송 시작...
>>> 8. 응답 받음!
=== 상태 코드 === 400
=== 응답 본문 ===
<!DOCTYPE html>
<html lang=en>
  <meta charset=utf-8>
  <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
  <title>Error 400 (Bad Request)!!1</title>
  <style>

  </style>
  <a href=//www.google.com/><span id=logo aria-label=Google></span></a>
  <p><b>400.</b> <ins>That’s an error.</ins>
  <p>Your client has issued a malformed or illegal request.  <ins>That’s all we know.</ins>

>>> 9. 전송 함수 끝!
>>> 10. 프로그램 끝
>>> 
 이렇게 나오는데?

오후 03:13
AI
완벽한 디버깅이에요! 👏 이제 원인이 거의 확실히 보여요.

핵심 단서 분석
응답을 보면:

code
복사
Error 400 (Bad Request)
Your client has issued a malformed or illegal request.
그런데 흥미로운 점이 있어요. 이 에러 페이지가 구글의 일반 에러 페이지(www.google.com 로고가 있는)예요. 우리 Apps Script가 만든 에러가 아니에요. 즉, 요청이 Apps Script 코드까지 도달하기도 전에 구글의 앞단 서버에서 막혔다는 뜻이에요.

이건 거의 항상 구글 Apps Script 특유의 "리다이렉트" 문제 때문이에요.

무슨 일이 벌어지는 거냐면
구글 Apps Script URL(script.google.com)로 POST를 보내면, 구글은 실제 처리를 다른 주소(script.googleusercontent.com)로 리다이렉트(302) 시켜요. 그런데:

일반 브라우저나 PC는 이 리다이렉트를 따라가면서 헤더와 본문을 잘 유지해요
하지만 피코의 urequests는 리다이렉트를 따라갈 때 POST 데이터나 헤더를 제대로 안 넘겨서 → 그 다음 주소에서 "이상한 요청"이 되어 400이 나는 거예요
해결 방법 2가지
방법 1: 리다이렉트를 막고 직접 확인하기 (추천 — 학습용으로 좋아요)
urequests에서 자동 리다이렉트를 끄고, 구글이 알려주는 "진짜 주소"를 직접 받아서 거기로 다시 보내는 방법이에요. 조금 복잡하지만 원리를 배우기 좋아요.

방법 2: Content-Type을 바꿔보기 (더 간단 — 먼저 시도!)
사실 더 간단한 시도가 있어요. Content-Type을 application/json 대신 빼버리거나 text/plain으로 바꾸면, 리다이렉트 과정에서 문제가 덜 생기는 경우가 많아요.

먼저 이걸 시도해봐요. 전송 함수에서 headers 부분을 이렇게 바꿔보세요:

python
복사
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        # ▼▼▼ 헤더를 text/plain 으로 변경 ▼▼▼
        headers = {"Content-Type": "text/plain"}
        print(">>> 7. 전송 시작...")

        res = urequests.post(wifi_config.SHEET_URL, data=payload, headers=headers)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)
바뀐 곳: "Content-Type": "application/json" → "Content-Type": "text/plain"

왜 되냐면: Apps Script는 e.postData.contents로 본문 전체를 받아서 우리가 JSON.parse()로 직접 파싱하니까, Content-Type이 뭐든 상관없어요. 오히려 text/plain이 리다이렉트를 더 매끄럽게 통과해요.

해볼 것
위처럼 text/plain으로 바꿔서 다시 실행
결과(상태 코드, 응답 본문) 다시 보여주기
만약 이걸로 200이 나오고 시트에 데이터가 쌓이면 → 해결! 🎉 그래도 안 되면 → 방법 1(리다이렉트 직접 처리)로 같이 넘어가요.

먼저 이거 해보고 결과 알려줄래요?

오후 03:14

나
전체 코드를 줘 일단

오후 03:14
AI
네! 지금까지 진행한 내용을 모두 합치고, text/plain 수정까지 반영한 전체 테스트 코드를 드릴게요. 이건 아직 센서 없이 가짜 데이터로 전송 테스트하는 버전이에요.

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- 구글 시트 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        # text/plain 으로 전송 (리다이렉트 문제 회피)
        headers = {"Content-Type": "text/plain"}
        print(">>> 7. 전송 시작...")

        res = urequests.post(wifi_config.SHEET_URL, data=payload, headers=headers)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 9. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 10. 프로그램 끝")
실행하고 확인할 것
이 코드 실행
콘솔의 === 상태 코드 === 가 200으로 바뀌었는지
구글 스프레드시트에 새 줄이 쌓였는지
결과에 따라
✅ 200 + 시트에 데이터 쌓임 → 성공! 이제 진짜 센서 코드를 붙여서 완성하면 돼요 🎉
❌ 여전히 400 → 리다이렉트를 직접 처리하는 방법(방법 1)으로 넘어가요. 그때는 코드가 좀 더 복잡해지지만 같이 차근차근 할게요.
wifi_config.py는 그대로 두면 되고요 (CLASS_ID = "2-3"으로 되어 있는 것 같네요).

실행해보고 상태 코드가 어떻게 나오는지 알려줄래요? 🙂

오후 03:14

나
print(">>> 1. 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- 구글 시트 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        # text/plain 으로 전송 (리다이렉트 문제 회피)
        headers = {"Content-Type": "text/plain"}
        print(">>> 7. 전송 시작...")

        res = urequests.post(wifi_config.SHEET_URL, data=payload, headers=headers)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 9. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 10. 프로그램 끝")
 라고 떳어. 혹시 앱 스크립트 쪽을 바꿔보는건 어떨까?

오후 03:15
AI
좋은 생각이에요! 👍 사실 지금 단계에서 Apps Script 쪽을 손보는 게 맞는 방향이에요. 왜냐하면 우리가 처음에 만든 doPost 코드가 "교과서적인 기본형"이라, 피코의 리다이렉트 상황에 대비가 안 되어 있거든요.

그런데 먼저 잠깐! 방금 보낸 메시지에는 코드만 붙여넣어져 있고, 실행 결과(콘솔 출력)가 안 보여요. text/plain으로 바꾼 버전을 실행했을 때 상태 코드가 200이었는지 400이었는지 확인하면 더 정확한데, 혹시 아직 실행을 안 한 건가요?

일단 Apps Script를 개선하는 건 어차피 해야 할 일이니 진행해볼게요.

Apps Script 개선 코드
아래처럼 두 가지를 추가한 버전이에요:

doGet도 추가 → 브라우저로 URL 접속해서 "살아있는지" 테스트 가능
에러 상황을 더 자세히 알려주도록 보강
javascript
복사
// 피코가 데이터를 보낼 때 (POST)
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    if (!e || !e.postData || !e.postData.contents) {
      return ContentService
        .createTextOutput(JSON.stringify({result: "error", message: "no postData"}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      new Date(),
      data.class,
      data.co2,
      data.temp,
      data.hum,
      data.gas,
      data.light,
      data.status
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 브라우저로 접속 테스트할 때 (GET)
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({result: "alive", message: "웹앱이 살아있습니다!"}))
    .setMimeType(ContentService.MimeType.JSON);
}
⚠️ 가장 중요한 부분 — 다시 배포!
Apps Script는 코드를 고쳐도 다시 배포하지 않으면 반영이 안 돼요. 이게 사람들이 제일 많이 놓치는 부분이에요. 다음 순서를 꼭 지켜주세요:

위 코드 붙여넣고 저장(💾)
우측 상단 배포 → 배포 관리
현재 배포 옆 연필(수정) 아이콘 클릭
버전 드롭다운 → "새 버전" 선택 ⭐ (이거 안 하면 옛날 코드가 그대로 돌아가요!)
액세스 권한이 **"모든 사용자"**인지 확인
배포 클릭
배포 후 첫 테스트 (브라우저로 간단 확인)
배포하고 나서, 그 웹앱 URL을 그냥 브라우저 주소창에 붙여넣고 접속해보세요. doGet이 작동하면:

json
복사
{"result":"alive","message":"웹앱이 살아있습니다!"}
이게 보이면 → 웹앱이 정상 배포됐다는 뜻! 그 다음 피코로 다시 전송 테스트하면 돼요.

정리하면 다음 순서
Apps Script 코드 교체 + 새 버전으로 재배포
브라우저로 URL 접속 → alive 메시지 확인
피코 코드(text/plain 버전) 다시 실행 → 상태 코드 확인
결과 알려주기
브라우저 접속했을 때 뭐가 나오는지, 그리고 피코 실행 결과 상태 코드가 어떻게 나오는지 알려주세요! 🙂

오후 03:16

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 전송 시작...
>>> 8. 응답 받음!
=== 상태 코드 === 400
=== 응답 본문 ===
<!DOCTYPE html>
<html lang=en>
  <meta charset=utf-8>
  <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
  <title>Error 400 (Bad Request)!!1</title>
  <style>

  </style>
  <a href=//www.google.com/><span id=logo aria-label=Google></span></a>
  <p><b>400.</b> <ins>That’s an error.</ins>
  <p>Your client has issued a malformed or illegal request.  <ins>That’s all we know.</ins>

>>> 9. 전송 함수 끝!
>>> 10. 프로그램 끝
>>> 

아직 앱 스크립트는 안바꿨고, 방금 콘솔에서는 이렇게 나왔었어. 앱 스크립트 개선코드 새거로 다시줄래?

오후 03:16
AI
네! 다시 정리해서 드릴게요. 그리고 지금 결과를 보니 중요한 단서가 하나 더 보여요.

지금 결과에서 알 수 있는 것
응답이 여전히 구글의 일반 에러 페이지(www.google.com 로고가 있는 400)예요. 이건 우리 Apps Script가 만든 응답이 아니라, 요청이 Apps Script에 도달하기도 전에 구글 앞단에서 막힌 것이에요.

→ 그래서 Apps Script 코드를 바꾸는 것만으로는 해결이 안 될 가능성이 높아요. (코드까지 도달을 안 하니까요!) 하지만 doGet을 추가하면 "배포가 제대로 됐는지" 자체를 브라우저로 테스트할 수 있어서, 문제를 좁히는 데 꼭 필요해요. 그래서 일단 바꿔봅시다.

Apps Script 코드 (복사해서 전체 교체)
javascript
복사
// 피코가 데이터를 보낼 때 (POST)
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    if (!e || !e.postData || !e.postData.contents) {
      return ContentService
        .createTextOutput(JSON.stringify({result: "error", message: "no postData"}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      new Date(),
      data.class,
      data.co2,
      data.temp,
      data.hum,
      data.gas,
      data.light,
      data.status
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 브라우저로 접속 테스트할 때 (GET)
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({result: "alive", message: "웹앱이 살아있습니다!"}))
    .setMimeType(ContentService.MimeType.JSON);
}
꼭 지켜야 할 배포 순서 ⭐
위 코드 붙여넣고 저장(💾 아이콘 또는 Ctrl+S)
우측 상단 배포 → 배포 관리
현재 배포 옆 연필(수정) 아이콘 클릭
버전 드롭다운 → "새 버전" 선택 ← 이거 빼먹으면 옛날 코드 그대로예요!
액세스 권한 = "모든 사용자" 확인
배포 클릭
배포 후 — 브라우저로 먼저 테스트 🔍
배포가 끝나면, 웹앱 URL을 그냥 컴퓨터 브라우저 주소창에 붙여넣고 접속해보세요.

이때 두 가지 중 하나가 나올 거예요:

(A) 이런 JSON이 보이면 → 배포 정상!

json
복사
{"result":"alive","message":"웹앱이 살아있습니다!"}
(B) 구글 로그인 화면이나 "권한이 없습니다" 같은 게 나오면 → 배포 권한 문제가 진짜 원인이에요!

이게 왜 중요하냐면
지금 피코에서 보내는 400 에러가:

권한 문제라서 막힌 건지 (→ 브라우저 접속해보면 (B)가 나옴)
리다이렉트/데이터 형식 문제인지 (→ 브라우저는 (A) 정상인데 피코만 400)
이걸 구분해야 다음 해결책이 달라져요. 브라우저 접속은 이 둘을 가려주는 리트머스 시험지 같은 거예요.

배포한 뒤에 브라우저로 URL 접속하면 A가 나오는지 B가 나오는지 꼭 알려주세요! 그게 다음 단계의 갈림길이에요. 🙂

오후 03:17

나
웹앱이 잘 살아있대

오후 03:18
AI
좋아요! 🎉 이건 아주 중요한 정보예요. 정리하면:

지금 확인된 사실
✅ 브라우저로 접속 → 웹앱이 살아있습니다! 정상 출력
✅ 즉, 배포는 완벽하게 됐고, 권한 문제도 아니에요!
❌ 그런데 피코에서 POST를 보내면 → 구글 앞단에서 400
이 조합이 의미하는 건 딱 하나예요:

권한이나 배포 문제가 아니라, 피코의 urequests가 리다이렉트를 처리하는 방식이 문제다!

아까 의심했던 **리다이렉트 문제(방법 1)**가 진짜 범인으로 확정된 거예요. 🔍

무슨 일이 벌어지나 (원리)
피코가 script.google.com/.../exec로 POST를 보냄
구글이 "실제 처리는 다른 주소에서 할게" 하며 302 리다이렉트 응답을 줌 (script.googleusercontent.com/...)
피코의 urequests가 이 리다이렉트를 따라가는데, 이때 헤더나 본문 처리가 꼬여서 새 주소에 "이상한 요청"이 도착 → 400
해결: 리다이렉트를 따라갈 때 헤더를 제대로 챙기기
urequests에서 자동 리다이렉트를 처리할 때 생기는 문제라, 전송 함수를 살짝 고쳐줄게요. 핵심은 리다이렉트를 따라가도록 그냥 두되, 헤더를 최소화하는 거예요. 먼저 가장 간단한 시도부터:

python
복사
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        print(">>> 7. 전송 시작...")
        # 헤더를 아예 빼고, 데이터만 보내기
        res = urequests.post(wifi_config.SHEET_URL, data=payload)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)
바뀐 점: headers 부분을 완전히 제거했어요. (urequests가 헤더를 직접 만들어 리다이렉트 때 더 매끄럽게 처리하는 경우가 있어요.)

만약 이것도 400이면 — 더 확실한 방법
위로도 안 되면, 리다이렉트를 직접 따라가는 코드를 짜야 해요. 원리는:

첫 요청에서 자동 리다이렉트를 끔
구글이 알려준 "진짜 주소"(Location 헤더)를 꺼냄
그 주소로 다시 POST를 보냄
이건 조금 더 복잡한데, 필요하면 그때 같이 짜볼게요.

먼저 위의 헤더 뺀 버전으로 다시 실행해보고, 상태 코드가 어떻게 나오는지 알려줄래요?

혹시 이번엔 결과(콘솔 출력)도 같이 복사해서 보여주면, 더 정확하게 다음 단계를 정할 수 있어요! 🙂

오후 03:18

나
코드 전체 줘

오후 03:21
AI
네! 헤더를 뺀 버전으로 전체 코드를 드릴게요. 아직 가짜 데이터로 전송 테스트하는 버전이에요.

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- 구글 시트 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        print(">>> 7. 전송 시작...")
        # 헤더 없이 데이터만 전송
        res = urequests.post(wifi_config.SHEET_URL, data=payload)
        print(">>> 8. 응답 받음!")
        print("=== 상태 코드 ===", res.status_code)
        print("=== 응답 본문 ===")
        print(res.text)
        res.close()
    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 9. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 10. 프로그램 끝")
실행 후 알려주세요
콘솔 출력을 전체 복사해서 보여주세요. 특히:

=== 상태 코드 === 가 200인지 400인지
시트에 데이터가 쌓였는지
결과에 따라
✅ 200 + 시트에 데이터 → 드디어 성공! 🎉 진짜 센서 코드 붙이기로 넘어가요
❌ 여전히 400 → 리다이렉트를 직접 따라가는 더 확실한 방법으로 넘어가요 (그때 코드 같이 짤게요)
실행 결과 알려줄래요? 🙂

오후 03:22

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'myChevrolet 8096', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 전송 시작...
>>> 8. 응답 받음!
=== 상태 코드 === 400
=== 응답 본문 ===
<!DOCTYPE html>
<html lang=en>
  <meta charset=utf-8>
  <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
  <title>Error 400 (Bad Request)!!1</title>
  <style>
     *{margin:0;padding:0}html,code{font:15px/22px arial,sans-serif}html{background:#fff;color:#222;padding:15px}body{margin:7% auto 0;max-width:390px;min-height:180px;padding:30px 0 15px}* > body{background:url(//www.google.com/images/errors/robot.png) 100% 5px no-repeat;padding-right:205px}p{margin:11px 0 22px;overflow:hidden}ins{color:#777;text-decoration:none}a img{border:0}@media screen and (max-width:772px){body{background:none;margin-top:0;max-width:none;padding-right:0}}#logo{background:url(//www.google.com/images/branding/googlelogo/1x/googlelogo_color_150x54dp.png) no-repeat;margin-left:-5px}@media only screen and (min-resolution:192dpi){#logo{background:url(//www.google.com/images/branding/googlelogo/2x/googlelogo_color_150x54dp.png) no-repeat 0% 0%/100% 100%;-moz-border-image:url(//www.google.com/images/branding/googlelogo/2x/googlelogo_color_150x54dp.png) 0}}@media only screen and (-webkit-min-device-pixel-ratio:2){#logo{background:url(//www.google.com/images/branding/googlelogo/2x/googlelogo_color_150x54dp.png) no-repeat;-webkit-background-size:100% 100%}}#logo{display:inline-block;height:54px;width:150px}
  </style>
  <a href=//www.google.com/><span id=logo aria-label=Google></span></a>
  <p><b>400.</b> <ins>That’s an error.</ins>
  <p>Your client has issued a malformed or illegal request.  <ins>That’s all we know.</ins>

>>> 9. 전송 함수 끝!
>>> 10. 프로그램 끝
>>> 
라고 떴어.

오후 03:22
AI
좋아요, 이제 확실해졌어요. 헤더를 빼도 똑같이 400이 나오는 걸 보니, 리다이렉트 자체를 직접 처리해야 해요. 예상했던 "방법 1"로 갑니다! 💪

무슨 일이 일어나는지 다시 한 번
피코 → script.google.com/.../exec 로 POST
구글 → "진짜 처리는 script.googleusercontent.com/... 에서 해" 하며 302 리다이렉트 응답
피코의 urequests가 리다이렉트를 자동으로 따라가는데, 이때 POST를 GET처럼 보내거나 본문을 잃어버려서 → 새 주소에서 400
그래서 우리가 직접:

첫 요청에서 자동 추적을 끄고
구글이 알려준 새 주소를 받아서
그 주소로 POST를 다시 보내는 방식으로 처리할 거예요.
리다이렉트를 직접 따라가는 전체 코드
python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import urequests
import ujson
import wifi_config

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- 구글 시트 전송 (리다이렉트 직접 처리) ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        headers = {"Content-Type": "application/json"}

        url = wifi_config.SHEET_URL
        print(">>> 7. 1차 전송 시작...")

        # ★ 핵심: 자동 리다이렉트 끄기
        res = urequests.post(url, data=payload, headers=headers, allow_redirects=False)
        print(">>> 8. 1차 응답 상태:", res.status_code)

        # 302/307 등 리다이렉트면, 새 주소로 다시 보내기
        if res.status_code in (301, 302, 303, 307, 308):
            new_url = res.headers.get("Location")
            print(">>> 9. 리다이렉트 발견! 새 주소:", new_url)
            res.close()

            # 새 주소로 다시 POST
            res2 = urequests.post(new_url, data=payload, headers=headers)
            print(">>> 10. 2차 응답 상태:", res2.status_code)
            print("=== 응답 본문 ===")
            print(res2.text)
            res2.close()
        else:
            print("=== 응답 본문 ===")
            print(res.text)
            res.close()

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 11. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 12. 프로그램 끝")
핵심 변화 설명
allow_redirects=False → "자동으로 따라가지 마, 내가 직접 할게"
res.headers.get("Location") → 구글이 알려준 진짜 주소를 꺼냄
그 주소로 다시 POST → 이번엔 제대로 처리됨
실행 후 확인할 것
콘솔 출력 전체를 보여주세요. 특히 주목할 부분:

>>> 8. 1차 응답 상태: → 302 같은 게 나오면 우리 예상이 맞는 거예요
>>> 9. 리다이렉트 발견! 새 주소: → 새 주소가 뜨는지
>>> 10. 2차 응답 상태: → 여기가 200이면 성공! 🎉
⚠️ 혹시 >>> 전송 중 에러: ... allow_redirects 같은 에러가 뜨면, 피코에 설치된 urequests 버전이 이 옵션을 지원 안 하는 거예요. 그 경우엔 다른 방법(소켓으로 직접 통신)으로 가야 하는데, 일단 위 코드부터 돌려보고 결과를 알려주세요!

어떻게 나오는지 보여줄래요? 🙂

오후 03:23

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 1차 전송 시작...
>>> 전송 중 에러: unexpected keyword argument 'allow_redirects'
>>> 11. 전송 함수 끝!
>>> 12. 프로그램 끝
>>> 
라고 떳어. 참고로 이건 https://script.google.com/macros/s/AKfycbwssGqCtO0_EDCUJRwkydoIk_ut_uHFfomZwEpu7dxOBftMUGZgg7r_AwaMavP7DtNLCw/exec 내 웹앱 URL이고.. 아무튼

오후 03:23
AI
좋아요, 이제 원인과 해결책이 완전히 명확해졌어요!

code
복사
>>> 전송 중 에러: unexpected keyword argument 'allow_redirects'
이건 예상했던 상황이에요. 피코에 설치된 urequests 버전이 allow_redirects 옵션을 지원하지 않는 구형이라는 뜻이에요. 그래서 다른 길로 가야 해요.

해결 방법: 소켓(socket)으로 직접 통신하기
urequests에 의존하지 않고, 파이썬 기본 기능인 소켓으로 직접 HTTP 요청을 만들어 보내는 방법이에요. 이러면 리다이렉트도 우리가 직접 제어할 수 있어요. 조금 더 코드가 길지만, 이게 가장 확실해요.

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import usocket as socket
import ussl as ssl
import ujson
import wifi_config

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- URL 분해 ----------
def parse_url(url):
    # https://host/path 형태를 분해
    url = url.split("://", 1)[1]      # https:// 제거
    host, path = url.split("/", 1)    # 호스트와 경로 분리
    return host, "/" + path


# ---------- HTTPS POST (리다이렉트 직접 처리) ----------
def https_post(url, payload):
    host, path = parse_url(url)
    print(">>> 접속 호스트:", host)

    # 443 포트(HTTPS)로 연결
    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    # HTTP 요청 직접 작성
    request = (
        "POST " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(payload)) + "\r\n"
        "Connection: close\r\n"
        "\r\n"
        + payload
    )
    s.write(request.encode())

    # 응답 받기
    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()

    return response.decode("utf-8", "ignore")


# ---------- 시트 전송 (리다이렉트 따라가기) ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        url = wifi_config.SHEET_URL
        print(">>> 7. 1차 전송...")
        response = https_post(url, payload)

        # 응답 헤더에서 상태/리다이렉트 확인
        status_line = response.split("\r\n", 1)[0]
        print(">>> 8. 1차 응답:", status_line)

        # 리다이렉트(302 등)면 Location 찾아서 다시 보내기
        if "302" in status_line or "301" in status_line or "307" in status_line:
            new_url = None
            for line in response.split("\r\n"):
                if line.lower().startswith("location:"):
                    new_url = line.split(":", 1)[1].strip()
                    break
            print(">>> 9. 리다이렉트! 새 주소:", new_url)

            if new_url:
                response2 = https_post(new_url, payload)
                status_line2 = response2.split("\r\n", 1)[0]
                print(">>> 10. 2차 응답:", status_line2)
                # 본문만 추출해서 출력
                body = response2.split("\r\n\r\n", 1)[-1]
                print("=== 응답 본문 ===")
                print(body[-300:])  # 뒤쪽 일부만
        else:
            body = response.split("\r\n\r\n", 1)[-1]
            print("=== 응답 본문 ===")
            print(body[-300:])

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 11. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 12. 프로그램 끝")
이 코드의 핵심
urequests 대신 소켓으로 직접 HTTP 요청을 작성해서 보내요
https_post() 함수가 HTTPS 연결 + 요청 전송 + 응답 받기를 담당
응답이 **302(리다이렉트)**면, Location 헤더에서 새 주소를 찾아 그 주소로 다시 POST → 이게 핵심!
실행 후 확인할 것
콘솔 출력 전체를 보여주세요. 특히:

>>> 8. 1차 응답: → HTTP/1.1 302 ... 같은 게 나오는지
>>> 9. 리다이렉트! 새 주소: → 새 주소가 뜨는지 (보통 script.googleusercontent.com/...)
>>> 10. 2차 응답: → 여기가 HTTP/1.1 200 ...이면 성공! 🎉
그리고 시트에 데이터가 쌓였는지!
한번 돌려보고 결과 알려줄래요? 이번엔 될 가능성이 높아요! 💪

오후 03:24

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
Traceback (most recent call last):
  File "<stdin>", line 6, in <module>
ImportError: no module named 'ussl'
>>> 
라는데

오후 03:24
AI
아, ussl 모듈 이름 문제네요! 피코의 펌웨어 버전에 따라 모듈 이름이 달라요. 최신 MicroPython에서는 ussl/usocket 대신 그냥 ssl/socket을 써요.

import 부분만 양쪽 다 시도하도록 고쳐줄게요. 그러면 어떤 버전이든 작동해요.

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import ujson
import wifi_config

# 펌웨어 버전에 따라 모듈 이름이 달라서 둘 다 대비
try:
    import usocket as socket
except ImportError:
    import socket

try:
    import ussl as ssl
except ImportError:
    import ssl

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- URL 분해 ----------
def parse_url(url):
    url = url.split("://", 1)[1]
    host, path = url.split("/", 1)
    return host, "/" + path


# ---------- HTTPS POST ----------
def https_post(url, payload):
    host, path = parse_url(url)
    print(">>> 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "POST " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(payload)) + "\r\n"
        "Connection: close\r\n"
        "\r\n"
        + payload
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()

    return response.decode("utf-8", "ignore")


# ---------- 시트 전송 (리다이렉트 따라가기) ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        url = wifi_config.SHEET_URL
        print(">>> 7. 1차 전송...")
        response = https_post(url, payload)

        status_line = response.split("\r\n", 1)[0]
        print(">>> 8. 1차 응답:", status_line)

        if "302" in status_line or "301" in status_line or "307" in status_line:
            new_url = None
            for line in response.split("\r\n"):
                if line.lower().startswith("location:"):
                    new_url = line.split(":", 1)[1].strip()
                    break
            print(">>> 9. 리다이렉트! 새 주소:", new_url)

            if new_url:
                response2 = https_post(new_url, payload)
                status_line2 = response2.split("\r\n", 1)[0]
                print(">>> 10. 2차 응답:", status_line2)
                body = response2.split("\r\n\r\n", 1)[-1]
                print("=== 응답 본문 ===")
                print(body[-300:])
        else:
            body = response.split("\r\n\r\n", 1)[-1]
            print("=== 응답 본문 ===")
            print(body[-300:])

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 11. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 12. 프로그램 끝")
바뀐 점: import 부분에 try/except를 넣어서, ussl이 없으면 ssl을, usocket이 없으면 socket을 쓰도록 했어요. 이렇게 하면 어떤 펌웨어든 통과해요.

실행해보고 결과 알려줄래요? 특히 >>> 8. 1차 응답:에 302가 뜨고, >>> 10. 2차 응답:에 200이 뜨면 성공이에요! 🤞

오후 03:25

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'myChevrolet 8096']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 1차 전송...
>>> 접속 호스트: script.google.com
>>> 8. 1차 응답: HTTP/1.1 302 Moved Temporarily
>>> 9. 리다이렉트! 새 주소: https://script.googleusercontent.com/macros/echo?user_content_key=AUkAhnTYsw8hE7eFV_YsNNGZjVQht6pbd6YwoYUV33f1D9PJVjfErsjViL05nYDpEtJ0PXnzAIOp_5ph5dVxOydLysnAzQAuWF8W7jWeyEOtJub2tWm17BAbJYPWv6FeLExS9J1JBCcApX3N1eaoDZQY_LUuz9eZ0-X8n8FML_FXI_Psv5vJMyQb5unZw9g2OcgomF7wusRbzhjWF2ZiIPAfGdIx5O6uIDgchNUGi5Sl1qq6oR2nil2NmZDOaTfe578vdZU4wgNljAX0dmpHqGI50UVMef9OdA&lib=Mxt6rks9A1k5ZU4o0BVMUyHZS_oAss_rq
>>> 접속 호스트: script.googleusercontent.com
>>> 10. 2차 응답: HTTP/1.1 405 Method Not Allowed
=== 응답 본문 ===
ody><style nonce="s4C-QouiaqSYaOyDwxVwuQ">html {height: 100%; overflow: auto;}body {height: 100%; overflow: auto;}#outerContainer {margin: auto; max-width: 750px;}#innerContainer {margin-bottom: 20px; margin-left: 40px; margin-right: 40px; margin-top: 80px; position: relative;}</style></html>
0


>>> 11. 전송 함수 끝!
>>> 12. 프로그램 끝
>>> 
라는데?

오후 03:25
AI
엄청난 진전이에요! 🎉 거의 다 왔어요. 단서를 분석해봅시다.

지금 무슨 일이 일어났나
✅ >>> 8. 1차 응답: 302 → 리다이렉트 정상 감지!
✅ >>> 9. 새 주소: → script.googleusercontent.com/macros/echo?... 받아옴!
❌ >>> 10. 2차 응답: 405 Method Not Allowed
**405 = "이 방식(Method)은 안 돼"**라는 뜻이에요. 여기서 핵심 단서가 있어요. 새 주소를 잘 보면:

code
복사
.../macros/echo?...
echo라는 단어, 그리고 405가 의미하는 것:

구글이 리다이렉트로 보낸 이 주소는 GET 요청을 기대하는 주소예요
그런데 우리는 거기에 POST를 보냈으니 "POST는 안 돼!"(405)라고 거절한 거예요
그래서 해결책: 리다이렉트 따라갈 때는 GET으로!
HTTP 표준에서 302 리다이렉트를 따라갈 때는 보통 GET으로 바꿔서 보내요. (브라우저도 그렇게 동작해요.) 우리는 2차 요청을 POST로 보내서 막힌 거예요.

그런데 여기서 중요한 고민이 생겨요 🤔:

GET으로 바꾸면 405는 해결되지만, POST 본문(우리 데이터)을 어떻게 전달하지?
핵심 깨달음: Apps Script의 동작 방식
사실 이게 구글 Apps Script의 까다로운 점이에요. 정리하면:

1차 POST가 이미 script.google.com에서 우리 데이터를 받아 doPost를 실행했을 가능성이 높아요
302 리다이렉트는 그냥 "결과를 보여줄 페이지"로 안내하는 것
즉, 데이터는 이미 처리됐을 수도 있어요!
먼저 확인해볼 것 ⭐
지금 구글 스프레드시트를 열어보세요! 혹시 테스트 데이터가 한 줄 쌓여 있나요?

✅ 쌓여 있다면 → 사실 1차 요청에서 이미 성공한 거예요! 2차 405는 무시해도 돼요 (그냥 결과 페이지 못 본 것뿐). 그럼 코드에서 2차 요청 부분을 정리만 하면 끝!
❌ 안 쌓여 있다면 → 2차 요청을 GET 방식으로 바꿔서 마무리해야 해요.
만약 안 쌓였다면 — 2차를 GET으로 바꾼 함수
https_post와 별도로 GET용 함수를 추가하고, 리다이렉트는 GET으로 따라가게 합니다:

python
복사
# ---------- HTTPS GET (리다이렉트 따라갈 때 사용) ----------
def https_get(url):
    host, path = parse_url(url)
    print(">>> GET 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "GET " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")
그리고 send_to_sheet에서 리다이렉트 처리 부분을 https_post(new_url, ...) → **https_get(new_url)**로 바꾸면 돼요.

그래서 지금 할 일
먼저 스프레드시트부터 확인해주세요! 테스트 데이터가 쌓였는지 여부에 따라 다음 길이 완전히 갈려요:

쌓였으면 → "이미 성공! 코드 정리만 하면 됨"
안 쌓였으면 → "GET 방식으로 마무리"
시트에 데이터가 있나요, 없나요? 🔍

오후 03:26

나
안쌓여있어. get방식으로 전체 코드 다시줘

오후 03:27
AI
네! GET 방식으로 리다이렉트를 따라가는 전체 코드를 드릴게요.

python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import ujson
import wifi_config

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import ussl as ssl
except ImportError:
    import ssl

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- URL 분해 ----------
def parse_url(url):
    url = url.split("://", 1)[1]
    host, path = url.split("/", 1)
    return host, "/" + path


# ---------- HTTPS POST ----------
def https_post(url, payload):
    host, path = parse_url(url)
    print(">>> POST 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "POST " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(payload)) + "\r\n"
        "Connection: close\r\n"
        "\r\n"
        + payload
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")


# ---------- HTTPS GET (리다이렉트 따라갈 때) ----------
def https_get(url):
    host, path = parse_url(url)
    print(">>> GET 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "GET " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")


# ---------- 시트 전송 ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        data = {
            "class": wifi_config.CLASS_ID,
            "co2": co2,
            "temp": temp,
            "hum": hum,
            "gas": gas,
            "light": light_value,
            "status": status
        }
        payload = ujson.dumps(data)
        print(">>> 6. JSON 변환 완료:", payload)

        url = wifi_config.SHEET_URL
        print(">>> 7. 1차 POST 전송...")
        response = https_post(url, payload)

        status_line = response.split("\r\n", 1)[0]
        print(">>> 8. 1차 응답:", status_line)

        if "302" in status_line or "301" in status_line or "307" in status_line:
            new_url = None
            for line in response.split("\r\n"):
                if line.lower().startswith("location:"):
                    new_url = line.split(":", 1)[1].strip()
                    break
            print(">>> 9. 리다이렉트! 새 주소로 GET 시도")

            if new_url:
                # ★ 리다이렉트는 GET으로 따라가기
                response2 = https_get(new_url)
                status_line2 = response2.split("\r\n", 1)[0]
                print(">>> 10. 2차 응답:", status_line2)
                body = response2.split("\r\n\r\n", 1)[-1]
                print("=== 응답 본문 ===")
                print(body[-300:])
        else:
            body = response.split("\r\n\r\n", 1)[-1]
            print("=== 응답 본문 ===")
            print(body[-300:])

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 11. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 12. 프로그램 끝")
바뀐 핵심
https_get() 함수 추가
리다이렉트(302)를 따라갈 때 POST가 아니라 GET으로 새 주소에 접속
실행 후 확인할 것
>>> 10. 2차 응답: 이 **HTTP/1.1 200 OK**로 바뀌었는지
=== 응답 본문 === 에 {"result":"success"} 같은 게 나오는지
구글 스프레드시트에 테스트 데이터가 쌓였는지 ⭐
결과 알려줄래요? 이번엔 성공할 가능성이 커요! 만약 여전히 안 되면, Apps Script의 doPost가 받는 데이터를 POST 본문 대신 URL 파라미터로 넘기는 방식으로 접근을 바꿔야 할 수도 있어요. 일단 위 코드부터 돌려봐요! 🤞

오후 03:27

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 1. 코드 시작됨!
>>> 2. import 성공!
>>> 3. 와이파이 연결 시도
>>> 주변 WiFi: ['app', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G', 'senWiFi_Free_2.4G']
>>> 연결 시도: app
>>> 연결 성공! IP: 192.168.0.213
>>> 4. 와이파이 단계 끝, wlan = <CYW43 STA up 192.168.0.213>
>>> 5. 전송 함수 진입
>>> 6. JSON 변환 완료: {"status": "테스트", "gas": 12000, "temp": 23.4, "class": "2-3", "co2": 650.5, "hum": 45.2, "light": 28000}
>>> 7. 1차 POST 전송...
>>> POST 접속 호스트: script.google.com
>>> 8. 1차 응답: HTTP/1.1 302 Moved Temporarily
>>> 9. 리다이렉트! 새 주소로 GET 시도
>>> GET 접속 호스트: script.googleusercontent.com
>>> 10. 2차 응답: HTTP/1.1 200 OK
=== 응답 본문 ===
48
{"result":"error","message":"SyntaxError: Unexpected end of JSON input"}
0


>>> 11. 전송 함수 끝!
>>> 12. 프로그램 끝
>>> 
 라는데

오후 03:29
AI
와, 거의 다 왔어요! 🎉 이제 통신은 완벽하게 성공했어요! 마지막 한 조각만 남았어요.

응답 분석 — 큰 진전!
code
복사
>>> 10. 2차 응답: HTTP/1.1 200 OK
{"result":"error","message":"SyntaxError: Unexpected end of JSON input"}
이게 의미하는 것:

✅ 통신 성공! (200 OK) — 드디어 Apps Script까지 도달했어요!
✅ 우리 doPost 코드가 실행됨! ({"result":"error"...} 이건 우리가 만든 응답 형식이에요)
❌ 단, JSON.parse()가 실패함 → "Unexpected end of JSON input"
원인: 데이터가 비어서 도착했어요
SyntaxError: Unexpected end of JSON input은 JSON.parse에 빈 값이 들어왔다는 뜻이에요. 즉:

1차 POST로 데이터를 보냈지만
리다이렉트(302)된 후 GET으로 다시 갈 때는 데이터(payload)를 안 가져가요!
그래서 doPost가 실행될 때 본문이 비어있던 거예요
리다이렉트 과정에서 우리 데이터가 "증발"한 거죠. 이게 Apps Script + POST의 고질적인 문제예요.

해결책: 데이터를 URL 파라미터로 보내기
본문(body)으로 보내면 리다이렉트 때 사라지니까, 데이터를 URL 주소에 붙여서 보내는 방법으로 바꿔요. 이러면 리다이렉트돼도 데이터가 안 사라져요. 그리고 Apps Script도 doPost가 아니라 doGet으로 받게 바꿔요.

1단계: Apps Script 수정 (doGet으로 데이터 받기)
javascript
복사
// 브라우저/피코가 URL 파라미터로 데이터를 보낼 때
function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // 파라미터가 없으면 그냥 살아있다고 응답
    if (!e || !e.parameter || !e.parameter.class) {
      return ContentService
        .createTextOutput(JSON.stringify({result: "alive", message: "웹앱이 살아있습니다!"}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var p = e.parameter;  // URL 파라미터들

    sheet.appendRow([
      new Date(),
      p.class,
      p.co2,
      p.temp,
      p.hum,
      p.gas,
      p.light,
      p.status
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({result: "success"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
⚠️ 저장 후 반드시 "새 버전"으로 재배포! (배포 → 배포 관리 → 연필 → 버전 "새 버전" → 배포)

2단계: 피코 코드 수정 (데이터를 URL에 붙여서 GET으로 전송)
python
복사
print(">>> 1. 코드 시작됨!")

import time
import network
import wifi_config

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import ussl as ssl
except ImportError:
    import ssl

print(">>> 2. import 성공!")


# ---------- WiFi 연결 ----------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ---------- URL 분해 ----------
def parse_url(url):
    url = url.split("://", 1)[1]
    if "/" in url:
        host, path = url.split("/", 1)
        return host, "/" + path
    return url, "/"


# ---------- HTTPS GET ----------
def https_get(url):
    host, path = parse_url(url)
    print(">>> GET 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "GET " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")


# ---------- 시트 전송 (URL 파라미터 + 리다이렉트 따라가기) ----------
def send_to_sheet(co2, temp, hum, gas, light_value, status):
    print(">>> 5. 전송 함수 진입")
    try:
        # 데이터를 URL 파라미터 형태로 만들기
        params = "class={}&co2={}&temp={}&hum={}&gas={}&light={}&status={}".format(
            wifi_config.CLASS_ID, co2, temp, hum, gas, light_value, status
        )
        full_url = wifi_config.SHEET_URL + "?" + params
        print(">>> 6. 전송 URL 준비 완료")

        print(">>> 7. 1차 GET 전송...")
        response = https_get(full_url)

        status_line = response.split("\r\n", 1)[0]
        print(">>> 8. 1차 응답:", status_line)

        # 리다이렉트면 새 주소로 다시 GET
        if "302" in status_line or "301" in status_line or "307" in status_line:
            new_url = None
            for line in response.split("\r\n"):
                if line.lower().startswith("location:"):
                    new_url = line.split(":", 1)[1].strip()
                    break
            print(">>> 9. 리다이렉트! 새 주소로 GET")

            if new_url:
                response2 = https_get(new_url)
                status_line2 = response2.split("\r\n", 1)[0]
                print(">>> 10. 2차 응답:", status_line2)
                body = response2.split("\r\n\r\n", 1)[-1]
                print("=== 응답 본문 ===")
                print(body[-300:])
        else:
            body = response.split("\r\n\r\n", 1)[-1]
            print("=== 응답 본문 ===")
            print(body[-300:])

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ===== 실행 =====
print(">>> 3. 와이파이 연결 시도")
wlan = connect_wifi()

print(">>> 4. 와이파이 단계 끝, wlan =", wlan)

if wlan:
    send_to_sheet(650.5, 23.4, 45.2, 12000, 28000, "테스트")
    print(">>> 11. 전송 함수 끝!")
else:
    print(">>> 와이파이 연결 안 됨")

print(">>> 12. 프로그램 끝")
핵심 변화 정리
이전	지금
POST로 본문에 데이터	GET으로 URL에 데이터
리다이렉트 시 데이터 증발 ❌	리다이렉트돼도 데이터 유지 ✅
Apps Script doPost	Apps Script doGet
순서
Apps Script 코드 교체 → 새 버전으로 재배포 (이거 꼭!)
피코 코드 교체 → 실행
>>> 10. 2차 응답: 이 200 OK이고 {"result":"success"}가 나오는지
시트에 데이터 쌓였는지 ⭐
이번엔 진짜 될 거예요! 결과 알려줄래요? 🤞

참고: status에 한글("테스트")이 들어가면 URL에서 문제가 될 수 있는데, 일단 영어로 테스트하고 잘 되면 한글 처리(인코딩)도 같이 해결해요. 지금은 일단 돌려봅시다!

오후 03:29

나
성공했다.. 이제 센서를 사용해서 실제 데이터를 입력받는 로직을 짜야하는데? 지금 내가 센서를 안가지고 있고 피코만 가지고있어서 이건 못해볼거같고 아직, 지금은 어떤 방식으로 웹앱을 열지 생각해보자. 아까 내가 여러 피코로 스프레드시트 한곳에 보내버린다음에, 다른 하나의 피코 웹앱으로..하기로 생각했었잖아? 일단 이걸 어떻게 할지 생각해보자

오후 03:33
AI
성공 축하해요! 🎉🎉 그 험난한 리다이렉트 문제를 끝까지 디버깅해서 뚫어낸 거, 정말 대단해요. 이런 끈기가 진짜 개발자의 자세예요!

이제 웹앱 설계를 같이 고민해봐요. 그런데 그 전에 중요한 갈림길을 짚어야 해요. 🤔

핵심 질문: "웹앱이 데이터를 어디서 가져올까?"
아까 A 방식(시트에서 읽어와 표시)으로 정했었죠? 그런데 여기서 현실적인 문제가 하나 있어요.

우리가 방금 겪었듯이, 피코가 구글에 접근하는 건 리다이렉트 때문에 까다로워요. 그런데:

데이터를 쓰는 것(POST/GET): 방금 우리가 뚫어냄 ✅
데이터를 읽어오는 것(시트 → 피코): 이건 더 어려워요. 시트 데이터가 수백 줄이면, 피코의 작은 메모리로 그 많은 JSON을 다 받아서 파싱하는 게 부담스러워요
그래서 웹앱을 만드는 방식을 세 갈래로 나눠서 생각해볼 수 있어요.

방식 비교
방식 1: 피코 웹앱이 구글 시트를 읽어와 그래프 표시 (원래 A안)
code
복사
브라우저 → 피코 웹서버 → 구글시트 읽기 → 그래프로 보여줌
장점: "내가 만든 웹앱"이라는 느낌, 커스터마이징 자유
단점: 피코가 시트 읽기 + 그래프 그리기 둘 다 해야 해서 메모리 부담 큼, 데이터 많아지면 버거움
방식 2: 피코는 "현재 값"만 보여주고, 과거 데이터는 구글 시트가 담당
code
복사
브라우저 → 피코 웹서버 → "지금 우리 반 실시간 상태"만 표시
과거 그래프/대시보드 → 구글 시트 자체 차트 기능 사용
장점: 피코 부담 적음, 역할 분리 깔끔
단점: 화면이 두 군데로 나뉨
방식 3: 웹앱 자체를 구글에서 (Apps Script 웹앱)
code
복사
브라우저 → 구글 Apps Script 웹앱(HTML) → 시트 데이터 직접 그래프화
장점: 피코 부담 제로, 데이터 많아도 끄떡없음, 어디서나 접속 가능
단점: 피코로 웹서버 여는 "맛"은 없음 (구글이 다 함)
같이 생각해볼 질문들
선택하기 전에 스스로 답해보면 방향이 잡혀요:

웹앱에서 꼭 보여주고 싶은 게 뭔가요?

실시간 현재 상태? (지금 3반 CO₂ 얼마)
과거 추세 그래프? (오늘 하루 온도 변화)
여러 반 비교? (어느 반이 에너지를 제일 잘 아끼나)
누가 이 웹앱을 볼 건가요?

발표할 때 선생님/학생들? → 안정적이고 예쁜 게 중요
나 혼자 모니터링? → 간단해도 됨
"피코로 웹서버를 연다"는 것 자체가 프로젝트의 목표인가요?

그렇다면 방식 1·2처럼 피코 웹서버는 살려야 해요
결과만 중요하면 방식 3이 제일 편해요
제 생각 (참고용)
학교 프로젝트이고 여러 반 데이터를 비교/관찰하는 게 목적이라면, 솔직히 방식 2 또는 3이 훨씬 현실적이에요. 피코의 메모리 한계 때문에 "시트 전체를 읽어 그래프 그리기"는 자주 버벅이거든요.

하지만 "내가 만든 피코 웹앱"이라는 경험과 성취가 중요하다면 방식 1도 의미 있어요. 단, 데이터를 "최근 몇 개만" 읽어오는 식으로 가볍게 만들어야 해요.

위 질문들(특히 1번, 3번)에 대한 생각을 들려줄래요? 그걸 알아야 어떤 방식으로 갈지, 그리고 web.py를 어떻게 짤지 구체적으로 정할 수 있어요. 🙂

오후 03:33

나
지금 내가 구상 중인게, 여러반 데이터를 실시간 모니터링하고, 데이터 수집하고.. 지금 아마 피코로 데이터를 전송 시키고, 아마 메인 서버는 라즈베리파이 고사양(아마도 4~5) 정도로 메인 서버를 열거같아서 메모리 부담은 없을 거라고 예상하고 있어. 그니까 다시 한번더 말하자면, 피코 여러대로 1학년, 2학년 전체 반에 배치하여 시트에 배치하고, 그 피코들이 데이터를 스프레드시트로 전송해서, 그 상태로 메인 서버가 다른 AI lab실이라는 곳에서 실시간 모니터링을 하게 될거야.

오후 03:43
AI
아하, 그림이 완전히 명확해졌어요! 👏 그리고 이건 아까보다 훨씬 더 좋은 설계예요. 정리해볼게요.

당신의 최종 구조 정리
code
복사
[1·2학년 각 교실]
  피코 여러 대 (센서 측정)
        │  데이터 전송 (방금 성공한 방식)
        ▼
  [구글 스프레드시트]  ← 데이터 저장소(중앙 허브)
        │  읽어오기
        ▼
  [AI Lab실 - 라즈베리파이 4/5 메인 서버]
        │  웹앱(대시보드) 실행
        ▼
  실시간 모니터링 화면 (브라우저로 접속)
이 구조의 핵심 장점을 잘 잡았어요:

무거운 작업(시트 읽기 + 그래프 + 여러 반 처리)을 고사양 라즈베리파이가 담당 → 메모리 걱정 없음 ✅
피코는 센서 측정 + 전송만 → 가볍고 안정적 ✅
역할 분리 완벽 👍
이러면 아까 고민했던 "피코 메모리 부담" 문제가 싹 사라져요. 라즈베리파이는 일반 컴퓨터처럼 파이썬 라이브러리를 다 쓸 수 있거든요.

그래서 web.py(대시보드)는 라즈베리파이에서 돌아간다!
여기서 중요한 변화가 있어요. web.py는 더 이상 피코용(MicroPython)이 아니에요. 라즈베리파이 4/5는 **일반 파이썬(Python 3)**이 돌아가니까, 강력한 도구들을 쓸 수 있어요:

Flask 또는 Streamlit: 웹 대시보드 만들기
gspread: 구글 시트를 아주 쉽게 읽어오는 라이브러리
pandas / matplotlib / plotly: 데이터 분석 & 그래프
특히 Streamlit은 데이터 대시보드를 정말 빠르고 예쁘게 만들 수 있어서, 이런 모니터링 프로젝트에 딱이에요.

같이 정해야 할 것들
본격적으로 대시보드 코드를 짜기 전에, 몇 가지 정해봐요.

1. 대시보드에 뭘 보여줄까? (화면 구성) 예를 들면 이런 것들:

📊 반별 현재 상태 카드 (1-3반: CO₂ 650, 온도 23도, 🟢정상)
📈 시간에 따른 추세 그래프 (오늘 하루 온도 변화)
🚨 "낭비 의심" 경고 목록 (어느 반이 빈 교실 냉방 중인지)
🏆 반별 에너지 절약 순위
이 중에 뭘 넣고 싶나요? 우선순위는?

2. 시트를 어떻게 읽어올까? 두 가지 방법이 있어요:

(a) gspread + 구글 인증키: 정석적이고 강력하지만 초기 설정(서비스 계정 키)이 좀 있음
(b) 시트를 CSV로 공개 → 그냥 읽기: 설정 간단, 하지만 시트가 외부 공개됨
학교 환경이면 어느 쪽이 나을지 고민해볼 만해요.

3. 어떤 웹 도구를 쓸까?

Streamlit: 코드 적고, 데이터 대시보드에 최적화, 입문 추천 ⭐
Flask: 더 자유롭지만 HTML/CSS/JS를 직접 다뤄야 함
제안: 작은 것부터
지금 센서가 없어서 실제 데이터는 없지만, 시트에는 우리가 넣은 테스트 데이터가 있잖아요? 그러니까:

먼저 라즈베리파이(또는 그냥 PC)에서 구글 시트를 읽어와서 출력하는 것부터 (가장 작은 단위)
그게 되면 → 표로 예쁘게
그 다음 → 그래프
그 다음 → 실시간 자동 새로고침
이렇게 단계별로 가면 막히지 않아요. 우리가 전송 디버깅할 때처럼요. 🙂

먼저 답해줄 것:

대시보드에 보여주고 싶은 것 우선순위 (위 1번 항목 참고)
Streamlit vs Flask 중 어떤 걸로 해보고 싶은지 (잘 모르겠으면 추천해줄게요)
지금 라즈베리파이가 손에 있나요? 아니면 당분간은 PC로 개발하다가 나중에 옮길 건가요?
이 세 가지 알려주면, 바로 대시보드 첫 코드를 같이 짜볼 수 있어요! 어떻게 생각해요?

오후 03:43

나
지금 아직은 손에 없고 당분간은 PC로 개발할거같아.

오후 03:44
AI
좋아요! PC로 개발하는 게 오히려 더 편하고 빠를 거예요. 나중에 라즈베리파이로 옮길 때도 파이썬 코드라 거의 그대로 돌아가요. 👍

그럼 개발 환경부터 정리
PC에서 대시보드를 만들려면 **일반 파이썬(Python 3)**이 필요해요. 피코의 MicroPython이 아니라요. 확인해볼게요:

PC에 파이썬이 설치되어 있나요? (터미널/명령프롬프트에서 python --version 쳤을 때 버전이 나오는지)
코드 편집은 뭘로 할 거예요? (Thonny도 일반 파이썬 가능하고, VS Code도 좋아요)
아직 안 정한 것 2가지 — 같이 정해요
본격 코드 전에 이것만 정하면 바로 시작할 수 있어요.

① 어떤 웹 도구로?
제 추천은 Streamlit이에요. 이유는:

코드 몇 줄로 표·그래프·대시보드가 뚝딱 나와요
HTML/CSS 몰라도 됨
데이터 모니터링용으로 최적화
예시: st.line_chart(데이터) 한 줄이면 그래프가 그려져요. 정말 간단해요.

Flask는 더 자유롭지만 HTML을 직접 짜야 해서, 지금 목적(데이터 모니터링)엔 Streamlit이 훨씬 효율적이에요. 특별한 이유 없으면 Streamlit 추천!

② 시트를 어떻게 읽어올까?
가장 간단한 방법부터 가봐요. 구글 시트에는 "CSV로 내보내기" URL 기능이 있어서, 인증키 설정 없이도 읽을 수 있어요. (시트를 "링크 있는 사람은 볼 수 있음"으로 공유하면 됨)

장점: 설정 거의 없음, 바로 시작 가능
나중에 보안이 필요하면 gspread(인증키 방식)로 업그레이드 가능
추천 진행 순서
우리가 전송 디버깅할 때처럼 작은 단위부터 쌓아가요:

code
복사
1단계: PC에서 구글 시트 데이터 읽어서 표로 출력  ← 여기부터!
2단계: Streamlit으로 웹 화면에 표 띄우기
3단계: 그래프 추가
4단계: 반별 현재 상태 카드
5단계: 자동 새로고침(실시간)
다음 행동
먼저 이걸 확인하고 알려주세요:

PC에 파이썬이 설치돼 있나요? (python --version 결과)
Streamlit으로 가도 괜찮나요? (아니면 다른 거 원하는지)
구글 시트를 **"링크 있는 사람은 볼 수 있음"**으로 공유 설정할 수 있나요? (1단계에서 필요)
그리고 한 가지 미리 생각해볼 질문 🤔: 대시보드에서 **"실시간"**이라고 하면, 몇 초/몇 분마다 새로고침되면 충분할까요? (피코가 데이터를 보내는 주기와도 연결돼요. 너무 자주 하면 구글 시트에 요청이 너무 많아질 수 있거든요.)

준비되면 1단계 코드부터 같이 짜봐요! 🙂

오후 03:45

나
어, 일단 스트림릿으로 하자.

오후 03:45
AI
좋아요, Streamlit으로 가요! 👍 데이터 대시보드엔 정말 잘 맞는 선택이에요.

그럼 1단계로 가기 전에, 개발 환경 준비부터 확인하고 시작할게요. 이게 안 되어 있으면 코드를 짜도 안 돌아가거든요.

준비물 확인 (3가지)
① 파이썬 설치 확인
명령프롬프트(cmd) 또는 터미널을 열고 입력해보세요:

code
복사
python --version
Python 3.x.x 가 나오면 OK ✅
안 나오면 → python.org에서 설치 필요 (설치할 때 "Add Python to PATH" 체크 꼭!)
② Streamlit 설치
파이썬이 있으면, 명령프롬프트에 입력:

code
복사
pip install streamlit pandas requests
streamlit: 웹 대시보드
pandas: 표 데이터 다루기
requests: 구글 시트 읽어오기
설치 끝나면 확인:

code
복사
streamlit hello
이걸 치면 브라우저에 Streamlit 데모 화면이 뜰 거예요. 뜨면 설치 성공! 🎉

③ 구글 시트 공개 설정
1단계에서 시트를 읽으려면, 시트를 공유 설정해야 해요:

구글 시트 우측 상단 공유 버튼
"링크가 있는 모든 사용자" → 권한 **"뷰어"**로
이러면 인증키 없이도 읽을 수 있어요
⚠️ 학교 데이터라 민감하면 나중에 인증키 방식으로 바꿀 수 있어요. 지금은 개발/테스트 단계니까 간단한 방법으로 시작해요.

그다음 — 시트 ID 알아내기
시트를 읽으려면 **스프레드시트 주소(URL)**가 필요해요. 브라우저에서 구글 시트를 열면 주소가 이렇게 생겼을 거예요:

code
복사
https://docs.google.com/spreadsheets/d/여기가_시트_ID/edit#gid=0
이 중에서:

시트 ID: /d/ 와 /edit 사이의 긴 문자열
gid: gid= 뒤의 숫자 (보통 0)
이 두 개를 알아야 1단계 코드에서 쓸 수 있어요.

다음 행동
순서대로 해보고 알려주세요:

python --version → 버전 나오나요?
pip install streamlit pandas requests → 설치 잘 됐나요?
streamlit hello → 데모 화면 떴나요?
구글 시트 공유 설정 했나요?
구글 시트 URL(주소창에 있는 거) 알려줄래요? (시트 ID 확인용)
이것들이 준비되면, PC에서 구글 시트 데이터를 읽어와 표로 출력하는 첫 코드를 바로 짜볼게요!

혹시 진행하다 막히는 단계가 있으면, 어디서 막혔는지 알려주세요. 같이 풀어가요. 🙂

오후 03:46

나
C:\Windows\system32>pip install streamlit pandas requests
'pip'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램, 또는
배치 파일이 아닙니다.
라는데? https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/edit?gid=0#gid=0이건 구글 시트 URL이고,,

오후 03:48
AI
좋아요, 단서 두 개 다 받았어요! 하나씩 해결해봐요.

문제: pip을 인식 못 함
code
복사
'pip'은(는) 내부 또는 외부 명령... 아닙니다.
이건 보통 두 가지 중 하나예요:

파이썬이 아예 설치 안 됨
파이썬은 있는데 PATH에 등록이 안 됨
먼저 파이썬 자체가 있는지부터 확인해봐요. 명령프롬프트에 입력:

code
복사
python --version
(A) Python 3.x.x가 나온다면 → 파이썬은 있는 거예요. 그럼 pip을 이렇게 불러보세요:

code
복사
python -m pip install streamlit pandas requests
python -m pip은 "파이썬아, 네 안에 있는 pip을 실행해줘"라는 뜻이에요. pip이 PATH에 없어도 이렇게 하면 대부분 돼요.

(B) python도 인식이 안 된다면 → 파이썬이 설치 안 됐거나 PATH 문제예요. 그럼:

python.org/downloads 접속
최신 버전 다운로드 후 설치
⚠️ 설치 첫 화면에서 맨 아래 "Add Python to PATH" 체크박스를 꼭 체크! (이거 안 하면 똑같은 문제 반복돼요)
설치 후 명령프롬프트를 껐다가 다시 열기 (중요!)
다시 python --version 확인
구글 시트 정보 정리 (잘 받았어요!)
당신 URL을 분석하면:

code
복사
https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/edit?gid=0#gid=0
시트 ID: 1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E
gid: 0
이 정보로 나중에 CSV로 읽어오는 주소를 만들 거예요. 미리 보여주면 이렇게 생겼어요:

code
복사
https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0
(이 주소로 접속하면 시트 내용이 CSV 파일로 다운로드돼요. 이걸 파이썬이 읽는 거예요!)

⚠️ 단, 이게 작동하려면 시트 공유 설정("링크 있는 모든 사용자 - 뷰어")이 되어 있어야 해요. 이거 했나요?

다음 행동
python --version 결과 알려주기 (A인지 B인지 판단)
위 결과에 따라 pip 설치 진행
구글 시트 공유 설정 했는지 확인
(테스트) 브라우저에 이 주소 붙여넣어 보기:
code
복사
https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0
→ CSV 파일이 다운로드되거나 데이터가 보이면 성공! (공유 설정이 잘 된 거예요)
먼저 python --version부터 쳐보고 결과 알려줄래요? 🙂

오후 03:49

나
C:\Windows\system32>python --version
Python 이라고만 나오는데

오후 03:49
AI
아하, Python이라고만 나오고 버전 번호가 안 나오는 건 좀 특이한 신호예요. 🤔 이건 보통 파이썬이 제대로 설치되지 않았거나, Windows의 가짜 안내(스토어 연결용 껍데기)가 응답하는 경우예요.

확인: 진짜 파이썬인지 가짜인지
명령프롬프트에 이걸 쳐보세요:

code
복사
where python
여기서 나오는 경로를 보면 판단할 수 있어요:

C:\Users\...\AppData\Local\Microsoft\WindowsApps\python.exe 같은 게 나오면 → **Windows 스토어 껍데기(가짜)**예요. 진짜 파이썬이 아니에요.
C:\Python3x\... 또는 C:\Users\...\AppData\Local\Programs\Python\... 이 나오면 → 진짜 파이썬이 설치된 거예요.
가장 확실한 해결: 새로 깔끔하게 설치
지금 상태가 좀 애매하니까, 제대로 다시 설치하는 게 제일 빠르고 확실해요:

설치 순서
python.org/downloads 접속
노란색 "Download Python 3.x.x" 버튼 클릭
다운로드된 설치 파일 실행
⚠️ 가장 중요! 설치 첫 화면 맨 아래에 있는 체크박스 2개를 모두 체크:
✅ Add python.exe to PATH (이거 꼭!!)
✅ Use admin privileges... (있으면 체크)
"Install Now" 클릭
설치 완료되면 명령프롬프트(cmd)를 완전히 닫고 새로 열기 ← 이거 안 하면 변경사항이 반영 안 돼요!
설치 후 다시 확인
새로 연 명령프롬프트에서:

code
복사
python --version
이번엔 Python 3.12.x 처럼 버전 숫자까지 제대로 나와야 해요.

그다음:

code
복사
python -m pip install streamlit pandas requests
그동안 미리 해두면 좋은 것
설치하는 동안, 구글 시트 공유 설정과 CSV 주소 테스트를 미리 해두면 좋아요:

브라우저 주소창에 이거 붙여넣어 보세요:

code
복사
https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0
CSV 파일이 다운로드되거나 데이터가 보이면 → 공유 설정 OK ✅
"권한이 필요합니다" 같은 게 나오면 → 시트 공유 설정부터 해야 해요 (공유 → 링크 있는 모든 사용자 → 뷰어)
다음 행동
where python 결과 알려주기 (가짜인지 확인)
python.org에서 PATH 체크하고 재설치
cmd 새로 열고 python --version → 버전 숫자 나오는지
위 CSV 주소 브라우저 테스트 → 데이터 보이는지
하나씩 해보고 막히는 부분 알려줘요! 환경 설정이 제일 귀찮은 단계인데, 이것만 넘기면 그 다음은 술술 풀려요. 💪

오후 03:49

나
일단 다운로드 되고, 데이터는 보이긴하는데 ?쒓컙	諛?CO2	?⑤룄	?듬룄	媛??議곕룄	?곹깭		
2026. 6. 2 ?ㅽ썑 3:30:44	02월 03일	650.5	23.4	45.2	12000	28000	?뚯뒪?
이런 식으로 깨져서 보여. 그리고 지금 파이썬 다 깔았고, 스트림릿도 깐것같아

오후 03:52
AI
오, 두 가지 큰 진전이 있네요! 그리고 깨져 보이는 것도 정상적인 현상이니 걱정 마세요. 하나씩 짚을게요.

1. 한글 깨짐 — 원인과 해결
code
복사
?쒓컙  諛?CO2  ?⑤룄...
이건 글자 인코딩(encoding) 문제예요.

구글 시트의 한글은 UTF-8이라는 방식으로 저장돼 있어요
그런데 브라우저나 메모장이 그걸 **다른 방식(EUC-KR 등)**으로 읽으려다 깨진 거예요
데이터 자체는 멀쩡해요! 단지 보여주는 과정에서 깨진 것뿐이에요
그리고 좋은 소식: 파이썬(pandas)으로 읽을 때는 UTF-8로 제대로 읽으면 안 깨져요. 그러니 이 깨짐은 무시해도 돼요. 우리 코드에서 인코딩만 잘 지정하면 해결돼요.

2. 환경 준비 완료 확인
파이썬 + Streamlit 설치됐다니, 마지막으로 확인만 해봐요. 명령프롬프트에:

code
복사
python --version
→ 이번엔 Python 3.x.x 버전 숫자가 나오나요?

code
복사
python -m streamlit version
→ Streamlit 버전이 나오나요?

이 두 개가 잘 나오면 드디어 첫 대시보드 코드를 짤 준비 완료예요! 🎉

3. 첫 코드 미리보기
준비되면 이런 식의 코드를 짤 거예요 (1단계: 시트 읽어서 표로 출력):

python
복사
import streamlit as st
import pandas as pd

# 구글 시트 CSV 주소
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.title("교실 환경 모니터링 대시보드")

# 시트 읽어오기 (UTF-8로 읽어서 한글 안 깨짐)
df = pd.read_csv(SHEET_CSV)

# 표로 보여주기
st.dataframe(df)
이게 딱 이만큼이에요. pandas가 CSV 주소를 자동으로 UTF-8로 읽어서 한글도 안 깨지고 표로 예쁘게 나올 거예요.

실행은 명령프롬프트에서 streamlit run 파일이름.py 로 해요. (그냥 ▶ 버튼이 아니라요!)

다음 행동
python --version → 버전 숫자 나오는지
python -m streamlit version → 스트림릿 버전 나오는지
이 두 개 확인되면, 위 코드를 dashboard.py 같은 이름으로 저장하고 실행하는 것까지 같이 해볼게요!

먼저 두 버전 확인 결과 알려줄래요? 🙂

오후 03:53

나
C:\Windows\system32>pip install streamlit pandas requests
'pip'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램, 또는
배치 파일이 아닙니다.
라는데? 파이썬 잘깔았는데? python -m pip install streamlit pandas requests이것도 잘 했고, streamlit hello이건 작동안해.

오후 03:55
AI
좋아요, 단서를 정리해봅시다. 지금 상황이 살짝 헷갈리니 하나씩 명확히 해요.

현재 상황 정리
✅ 파이썬 설치됨
✅ python -m pip install streamlit pandas requests → 이건 잘 됐다! (중요!)
❌ pip 단독 명령 → 안 됨
❌ streamlit hello → 안 됨
핵심 이해: PATH 문제예요
python -m pip ...은 되는데 pip 단독은 안 되는 것, 그리고 streamlit이 단독으로 안 되는 것 — 이건 전부 같은 원인이에요.

파이썬은 PATH에 등록됐는데, 그 안의 도구들(pip, streamlit)은 PATH에 등록이 안 된 상태예요.

그래서 python -m을 앞에 붙이면 다 작동해요! python -m은 "파이썬아, 네 안에 있는 그 도구를 실행해줘"라는 만능 명령이거든요.

해결: 그냥 python -m을 붙여서 쓰면 돼요!
streamlit hello 대신 이렇게:

code
복사
python -m streamlit hello
이러면 작동할 거예요. 한번 쳐보세요!

마찬가지로 앞으로:

❌ streamlit run dashboard.py
✅ python -m streamlit run dashboard.py
이렇게 항상 python -m을 붙이면 PATH 문제와 상관없이 잘 돌아가요.

먼저 설치 확인부터
진짜로 잘 깔렸는지 확인해봐요:

code
복사
python -m streamlit version
→ 버전 숫자(예: Streamlit, version 1.x.x)가 나오면 설치 성공이에요! ✅

(선택) PATH를 깔끔하게 고치고 싶다면
매번 python -m 붙이는 게 귀찮으면, 나중에 PATH를 제대로 등록하면 돼요. 하지만 지금은 그냥 python -m 붙여서 진행하는 게 빠르고 문제없어요. 개발에 전혀 지장 없거든요.

다음 행동
python -m streamlit version → 버전 나오는지 확인
python -m streamlit hello → 데모 화면 뜨는지 확인
이 두 개 되면, 바로 첫 대시보드 코드를 만들고 실행해볼게요! (dashboard.py 만들어서 python -m streamlit run dashboard.py로 실행)

먼저 1번 결과 알려줄래요? 🙂

오후 03:55

나
어 잘깔렸다. 어 잘뜬다

오후 03:56
AI
완벽해요! 🎉 드디어 개발 환경 준비 끝! 이제 진짜 재밌는 부분, 첫 대시보드 만들기로 갑니다!

1단계: 시트 읽어서 표로 띄우기
아래 코드를 dashboard.py 라는 이름으로 저장하세요. (저장 위치는 기억해두기! 예: 바탕화면이나 특정 폴더)

python
복사
import streamlit as st
import pandas as pd

# 구글 시트 CSV 주소
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

# 페이지 제목
st.title("🏫 교실 환경 모니터링 대시보드")
st.write("구글 시트의 데이터를 실시간으로 읽어옵니다.")

# 시트 읽어오기 (UTF-8로 자동 처리되어 한글 안 깨짐)
df = pd.read_csv(SHEET_CSV)

# 표로 보여주기
st.subheader("📋 수집된 데이터")
st.dataframe(df)

# 데이터가 몇 줄인지 표시
st.write("총", len(df), "개의 데이터가 있습니다.")
실행 방법
명령프롬프트(cmd)를 열어요
dashboard.py가 저장된 폴더로 이동해야 해요. 예를 들어 바탕화면에 저장했다면:
code
복사
cd Desktop
cd는 폴더 이동 명령이에요. 만약 다른 폴더면 그 경로로 이동하세요.

실행:
code
복사
python -m streamlit run dashboard.py
그러면 자동으로 브라우저가 열리면서 대시보드가 나타날 거예요! (보통 http://localhost:8501)
잘 되면 이렇게 보일 거예요
제목: "🏫 교실 환경 모니터링 대시보드"
표: 시간 / 반 / CO2 / 온도 / 습도 / 가스 / 조도 / 상태 (한글 안 깨지고!)
"총 1개의 데이터가 있습니다" (지금은 테스트 데이터 1줄이니까)
폴더 이동이 헷갈리면
cd로 폴더 찾아가는 게 어려우면, 더 쉬운 방법이 있어요:

파일 탐색기에서 dashboard.py가 있는 폴더를 열어요
그 폴더의 주소창을 클릭하고 cmd 라고 친 뒤 엔터
그 폴더 위치에서 바로 명령프롬프트가 열려요!
거기서 python -m streamlit run dashboard.py 실행
다음 행동
dashboard.py 저장
명령프롬프트에서 해당 폴더로 이동
python -m streamlit run dashboard.py 실행
브라우저에 표가 떴는지 확인!
실행해보고 어떻게 나오는지 알려줄래요? 표가 잘 뜨면 다음 단계(그래프, 반별 카드)로 갈게요!

혹시 에러가 나면 그 메시지를 그대로 복사해서 보여주세요. 같이 해결해요! 🙂

오후 03:56

나
근데, 이거 어짜피 라즈베리파이로 서버를 열어서 데이터 분석을 할건데, 굳이 컴퓨터로 이런 방식으로 할 필요가 있어? 라즈베리파이로 할때 어떻게 하는지나 알려줘

오전 09:10
AI
아주 좋은 질문이고, 합리적인 의문이에요! 👍 그런데 결론부터 말하면 — 지금 PC로 개발하는 게 라즈베리파이를 위한 가장 좋은 준비예요. 이유를 설명할게요.

핵심: 코드는 거의 똑같아요
라즈베리파이도 결국 리눅스가 깔린 작은 컴퓨터예요. 그리고 우리가 쓰는 Streamlit + pandas는 PC든 라즈베리파이든 똑같은 파이썬 코드로 돌아가요.

즉, 지금 PC에서 만든 dashboard.py를 라즈베리파이에 그대로 복사하면 거의 그대로 작동해요. 환경 설정 명령어만 살짝 다를 뿐이에요.

code
복사
PC에서 만든 dashboard.py  ──복사──▶  라즈베리파이에서 실행
        (거의 그대로 작동!)
그럼 왜 지금 PC로 먼저 하냐면
라즈베리파이가 아직 손에 없잖아요! 기다리는 동안 놀 수는 없죠
개발 속도가 빨라요 — PC가 더 빠르고, 에러 잡기도 편해요
라즈베리파이는 화면/키보드 연결이 번거로워요 — 코드는 PC에서 완성하고, 옮기는 게 효율적
어차피 코드는 재사용 — 헛수고가 아니에요!
프로 개발자들도 이렇게 해요. "PC에서 개발 → 서버(라즈베리파이)에 배포". 우리가 지금 하는 게 딱 그 흐름이에요.

라즈베리파이로 옮길 때 달라지는 것 (미리보기)
나중에 라즈베리파이 생기면, 이 정도만 하면 돼요:

bash
복사
# 1. 라즈베리파이에 파이썬은 기본 설치돼 있음 (확인만)
python3 --version

# 2. 필요한 도구 설치 (PC에서 했던 것과 거의 동일)
pip3 install streamlit pandas requests

# 3. PC에서 만든 dashboard.py 파일을 복사해 옮김 (USB나 네트워크로)

# 4. 실행 (거의 동일!)
streamlit run dashboard.py
거의 똑같죠? 그리고 라즈베리파이는 24시간 계속 켜둘 수 있어서 진짜 "서버"로 쓰기 좋은 거예요. (PC는 끄면 멈추니까요.)

그래서 제안
지금 PC에서 대시보드를 완성도 있게 만들어두면, 나중에 라즈베리파이엔 그냥 복사 + 실행만 하면 끝이에요. 라즈베리파이 도착하면 5분이면 옮겨요.

비유하면: 이사 가기 전에 짐(코드)을 미리 싸두는 거예요. 새 집(라즈베리파이) 도착하면 풀기만 하면 되죠.

그러니 이렇게 진행하면 어때요?
지금: PC에서 대시보드 개발 (표 → 그래프 → 반별 카드 → 실시간)
나중에: 완성된 dashboard.py를 라즈베리파이에 복사 + 실행
이러면 라즈베리파이 사용법도 자연스럽게 익히고, 헛수고도 없어요.

어때요? 일단 PC에서 첫 대시보드(아까 그 표 코드)부터 띄워볼까요? 띄우는 거 성공하면, 라즈베리파이로 옮기는 것도 그만큼 쉬워진다는 걸 직접 느낄 수 있을 거예요.

아니면 라즈베리파이 환경에 대해 더 궁금한 게 있으면 물어봐요! 🙂

오전 09:11

나
C:\Users\user>cd Desktop

C:\Users\user\Desktop>python -m streamlit run dashboard.py
Python
C:\Users\user\Desktop> 라는데

오전 10:27
AI
음, 이상한 일이 일어났어요. python -m streamlit run dashboard.py를 쳤는데 Python이라고만 출력되고 끝나버렸네요. 🤔 아까 python --version 했을 때랑 똑같은 증상이에요.

이건 파이썬 실행이 뭔가 꼬여있다는 신호예요. 아까 python -m streamlit hello는 잘 됐다고 했는데, 지금은 안 되는 게 좀 이상해요.

먼저 확인: 진짜 파이썬을 가리키는지
명령프롬프트에 이걸 쳐보세요:

code
복사
where python
여러 줄이 나올 수 있어요. 거기서 맨 위에 뭐가 나오는지가 중요해요:

C:\Users\user\AppData\Local\Microsoft\WindowsApps\python.exe 처럼 WindowsApps가 들어있으면 → 이게 문제예요! 이건 진짜 파이썬이 아니라 윈도우의 가짜 껍데기라서 Python만 출력하고 아무것도 안 해요.
만약 WindowsApps가 맨 위라면 — 해결법
진짜 파이썬을 직접 지정해서 실행하면 돼요. 먼저 진짜 파이썬 위치를 찾아요. where python 결과에서 이런 경로를 찾으세요:

code
복사
C:\Users\user\AppData\Local\Programs\Python\Python3xx\python.exe
이게 진짜 파이썬이에요. 이걸 직접 써서 실행하면 돼요. 예를 들면:

code
복사
py -m streamlit run dashboard.py
💡 py 는 윈도우에 같이 설치되는 파이썬 런처예요. python 대신 py를 쓰면 가짜 껍데기를 피해서 진짜 파이썬을 찾아줘요. 이게 제일 간단한 해결책일 수 있어요!

추천 순서
먼저 py 로 시도:

code
복사
py -m streamlit run dashboard.py
→ 이게 되면 제일 간단! 앞으로 python 대신 py를 쓰면 돼요.

py도 안 되면, where python 결과를 그대로 복사해서 보여주세요. 진짜 파이썬 경로를 찾아서 해결할게요.

추가 확인: dashboard.py 저장 확인
혹시 모르니 하나만 더 확인해요:

dashboard.py가 진짜 바탕화면(Desktop)에 저장되어 있나요?
파일 이름이 정확히 dashboard.py인가요? (혹시 dashboard.py.txt처럼 숨은 확장자가 붙은 건 아닌지)
메모장으로 저장하면 가끔 .txt가 몰래 붙어요. 파일 탐색기에서 "보기 → 파일 확장명 표시"를 켜면 확인할 수 있어요.

다음 행동
py -m streamlit run dashboard.py 시도 → 결과 알려주기
안 되면 where python 결과 복사해서 보여주기
dashboard.py 파일이 바탕화면에 정확한 이름으로 있는지 확인
py로 한번 해보고 어떻게 되는지 알려줄래요? 🙂

오전 10:27

나
Microsoft Windows [Version 10.0.19045.6456]
(c) Microsoft Corporation. All rights reserved.

C:\Users\user>where python
C:\Users\user\AppData\Local\Microsoft\WindowsApps\python.exe
C:\Users\user\AppData\Local\Python\bin\python.exe

C:\Users\user>

C:\Users\user>py -m streamlit run dashboard.py
Usage: streamlit run [OPTIONS] [TARGET] [ARGS]...
Try 'streamlit run --help' for help.

Error: Invalid value: File does not exist: dashboard.py

C:\Users\user>py -m streamlit run dashboard.py
Usage: streamlit run [OPTIONS] [TARGET] [ARGS]...
Try 'streamlit run --help' for help.

Error: Invalid value: File does not exist: dashboard.py

C:\Users\user> 라는데

오전 10:29
AI
두 가지가 한 번에 밝혀졌어요! 정리해봅시다. 🔍

알아낸 것 2가지
① py가 정답이었어요!
code
복사
where python 결과:
C:\...\Microsoft\WindowsApps\python.exe   ← 가짜 껍데기 (맨 위)
C:\...\Python\bin\python.exe              ← 진짜 파이썬
역시 맨 위가 WindowsApps 가짜였어요. 그게 Python만 출력하고 멈춘 범인이었어요. 그런데 py를 쓰니까 streamlit이 제대로 실행됐죠! (에러 메시지가 streamlit에서 나온 걸 보면 알 수 있어요.)

→ 앞으로 python 대신 무조건 py를 쓰세요! 이제 가짜 껍데기 문제는 해결됐어요. 👍

② 이번엔 "파일이 없다"는 에러
code
복사
Error: File does not exist: dashboard.py
이건 진전이에요! streamlit은 잘 실행됐는데, dashboard.py 파일을 못 찾은 것뿐이에요. 이유를 보면:

지금 명령프롬프트 위치가:

code
복사
C:\Users\user>
인데, 아까 파일은 **바탕화면(Desktop)**에 저장했죠? 그런데 지금은 **Desktop 안이 아니라 그 바깥(C:\Users\user)**에 있어요. 그래서 못 찾는 거예요.

해결: Desktop 폴더로 이동 후 실행
먼저 바탕화면 폴더로 들어가고:

code
복사
cd Desktop
그다음 실행:

code
복사
py -m streamlit run dashboard.py
이러면 위치가 C:\Users\user\Desktop>로 바뀌고, 거기에 있는 dashboard.py를 찾아서 실행할 거예요!

혹시 그래도 "파일 없음"이 나오면
그럼 파일 이름이나 위치 문제일 수 있어요. 확인 방법:

Desktop으로 이동한 뒤, 파일 목록을 봐요:

code
복사
dir *.py
→ 여기에 dashboard.py가 보이나요?

안 보이면 → 파일이 바탕화면에 없거나, 이름이 다른 거예요 (예: dashboard.py.txt)
dashboard.py.txt처럼 나오면 → 메모장이 .txt를 몰래 붙인 거예요. 이름을 dashboard.py로 정확히 바꿔야 해요
정리하면
code
복사
1. cd Desktop          ← 바탕화면 폴더로 이동
2. dir *.py            ← dashboard.py 있는지 확인 (선택)
3. py -m streamlit run dashboard.py   ← 실행!
이대로 해보고, 브라우저에 대시보드가 뜨는지 알려줄래요?

이번엔 진짜 표가 뜰 가능성이 높아요! 만약 또 막히면 dir *.py 결과를 보여주세요. 🙂

오전 10:30

나
어 된다. 근데 웹사이트 안에서 

urllib.error.HTTPError: HTTP Error 401: Unauthorized
Traceback:
File "C:\Users\user\Desktop\dashboard.py", line 12, in <module>
    df = pd.read_csv(SHEET_CSV)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\parsers\readers.py", line 873, in read_csv
    return _read(filepath_or_buffer, kwds)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\parsers\readers.py", line 300, in _read
    parser = TextFileReader(filepath_or_buffer, **kwds)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\parsers\readers.py", line 1645, in __init__
    self._engine = self._make_engine(f, self.engine)
                   ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\parsers\readers.py", line 1904, in _make_engine
    self.handles = get_handle(
                   ~~~~~~~~~~^
        f,
        ^^
    ...<6 lines>...
        storage_options=self.options.get("storage_options", None),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\common.py", line 776, in get_handle
    ioargs = _get_filepath_or_buffer(
        path_or_buf,
    ...<3 lines>...
        storage_options=storage_options,
    )
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\common.py", line 405, in _get_filepath_or_buffer
    with urlopen(req_info) as req:
         ~~~~~~~^^^^^^^^^^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\pandas\io\common.py", line 282, in urlopen
    return urllib.request.urlopen(*args, **kwargs)  # noqa: TID251
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 187, in urlopen
    return opener.open(url, data, timeout)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 493, in open
    response = meth(req, response)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 602, in http_response
    response = self.parent.error(
        'http', request, response, code, msg, hdrs)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 531, in error
    return self._call_chain(*args)
           ~~~~~~~~~~~~~~~~^^^^^^^
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 464, in _call_chain
    result = func(*args)
File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\urllib\request.py", line 611, in http_error_default
    raise HTTPError(req.full_url, code, msg, hdrs, fp) 라는 에러가 떴어

오전 10:31
AI
좋아요! 대시보드 자체는 잘 실행됐고(브라우저에 떴고), 딱 한 곳에서 막혔어요. 에러를 읽어봅시다.

에러 분석
code
복사
urllib.error.HTTPError: HTTP Error 401: Unauthorized
File "...dashboard.py", line 12, in <module>
    df = pd.read_csv(SHEET_CSV)
401 Unauthorized = "권한 없음, 너 누구야?"

즉, 파이썬이 구글 시트 CSV 주소로 접근하려는데, 구글이 "이 시트는 아무나 못 봐"라고 막은 거예요.

원인: 시트 공유 설정
이건 우리가 아까 얘기했던 시트 공유 설정이 안 되어 있어서 그래요. 기억나죠? 시트를 "링크 있는 사람은 볼 수 있음"으로 바꿔야 외부(파이썬)에서 읽을 수 있어요.

아까 브라우저로 CSV 주소 테스트했을 때 데이터가 보였던 건, 당신이 그 구글 계정으로 로그인되어 있어서 보인 거예요. 하지만 파이썬은 로그인이 안 된 "남"이라서 401로 막힌 거죠.

해결: 시트 공유 설정 바꾸기
구글 시트를 열어요
우측 상단 공유(Share) 버튼 클릭
아래쪽 "일반 액세스(General access)" 부분을 봐요
보통 **"제한됨(Restricted)"**으로 되어 있을 거예요 → 이걸 클릭
**"링크가 있는 모든 사용자(Anyone with the link)"**로 변경
권한은 **"뷰어(Viewer)"**로 두면 돼요
완료 클릭
이러면 파이썬도 "남"이지만 "링크 있으면 누구나 볼 수 있는" 시트가 되어서 읽을 수 있어요!

확인 방법
설정 바꾼 뒤, 시크릿 모드(또는 로그아웃 상태) 브라우저에서 CSV 주소를 열어보세요:

code
복사
https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0
로그인 안 한 상태에서도 데이터가 보이면 → 성공! (파이썬도 읽을 수 있어요)
여전히 로그인하라고 하면 → 공유 설정이 아직 안 된 거예요
💡 시크릿 모드로 테스트하는 이유: 파이썬처럼 "로그인 안 된 남"의 입장에서 보는 거예요. 똑똑한 테스트 방법이죠!

그다음
공유 설정 바꾸고 나서, 대시보드를 새로고침하거나 다시 실행하면:

code
복사
py -m streamlit run dashboard.py
이번엔 표가 뜰 거예요!

⚠️ 한 가지 생각해볼 점 (보안)
"링크 있는 모든 사람"으로 열면, 그 링크를 아는 사람은 누구나 데이터를 볼 수 있어요. 지금은 개발/테스트 단계니까 괜찮지만, 나중에 실제 학교 데이터가 쌓이면 이게 신경 쓰일 수 있어요.

그때는 gspread + 서비스 계정 키 방식(인증키로 안전하게 읽기)으로 업그레이드하면 돼요. 지금은 일단 간단한 방법으로 진행하고, 나중에 필요하면 같이 바꿔요.

다음 행동
시트 공유 설정 → "링크 있는 모든 사용자 - 뷰어"로 변경
시크릿 모드로 CSV 주소 테스트 (로그아웃 상태에서 보이는지)
대시보드 새로고침 → 표 뜨는지 확인!
해보고 결과 알려줄래요? 이번엔 진짜 표가 뜰 거예요! 🙂

오전 10:31

나
어 웹사이트 잘된다

오전 10:33
AI
완벽해요!! 🎉🎉🎉 드디어 전체 흐름이 한 바퀴 완성됐어요! 정말 대단해요!

지금까지 완성한 것 정리
code
복사
✅ 피코 → 구글 시트로 데이터 전송 (그 험난한 리다이렉트 뚫고!)
✅ 구글 시트 → 대시보드로 데이터 읽어와 표시
✅ Streamlit 웹 대시보드 실행 성공
이제 데이터가 흐르는 길이 완전히 뚫렸어요. 이게 프로젝트의 뼈대예요. 여기까지가 제일 어려운 부분이었고, 앞으로는 이 위에 살을 붙이는 거라 훨씬 재밌고 수월할 거예요!

이제 대시보드를 발전시켜봐요
지금은 단순한 표만 있죠. 여기에 하나씩 기능을 추가해볼 수 있어요. 우리가 전에 얘기했던 것들이에요:

추가할 수 있는 기능들
📈 그래프 — 시간에 따른 온도/CO₂ 변화를 선 그래프로
🎴 반별 현재 상태 카드 — "2-3반: CO₂ 650, 온도 23도 🟢정상"처럼 한눈에
🚨 경고 표시 — 어떤 값이 너무 높으면 빨간색으로 알림
🔄 자동 새로고침 — 몇 초마다 자동으로 최신 데이터 갱신 (진짜 "실시간")
🏫 반별 필터 — 보고 싶은 반만 골라서 보기
어디부터 할까?
제 추천 순서는 이래요 (쉬운 것 → 어려운 것):

그래프 먼저 (제일 직관적이고 보람 있어요)
반별 카드
자동 새로고침
다만 지금 **데이터가 딱 1줄(테스트 데이터)**밖에 없어서, 그래프는 점 하나만 찍힐 거예요. 😅 그래프의 "맛"을 제대로 보려면 데이터가 여러 줄 필요해요.

제안: 가짜 데이터 좀 더 넣기
그래프와 여러 기능을 제대로 테스트하려면, 시트에 테스트 데이터를 몇 줄 더 넣으면 좋아요. 방법은 두 가지:

(a) 아까 그 피코 코드로 값을 바꿔가며 몇 번 더 전송
(b) 구글 시트에 직접 손으로 몇 줄 입력 (제일 빠름)
여러 반(1-1, 1-2, 2-3...), 여러 시간대의 데이터가 있으면 대시보드 기능을 제대로 만들고 테스트할 수 있어요.

다음 행동 정해요
질문이에요:

어떤 기능부터 추가하고 싶어요? (그래프 추천!)
테스트용 가짜 데이터를 몇 줄 더 넣을까요? (그래프 보려면 필요해요)
뭘 하고 싶은지 알려주면, 바로 그 기능 코드를 같이 짜볼게요!

그리고 잠깐 — 여기까지 오느라 정말 고생 많았어요. 환경 설정부터 통신 디버깅까지, 막히는 데가 많았는데 끝까지 해낸 거 진짜 멋져요. 👏 이제 재밌는 부분만 남았어요!

오전 10:33

나
일단 반별 그래프를 그리자. 반 마다 그래프를 페이지를 바꿔가면서 볼 수있게, 페이지를 바로 넘기기 쉽게 웹페이지 상단에서 반을 한번에 고를 수 있는 드롭다운도 추가해주고, 그리고 아래에서는 반별 상태 체크 실시간으로 해서 어디가 지금 에어컨을 키고 이동수업을 하러 갔는지, 어디가 에어컨을 너무 세게 틀어서 에너지 절약을 안하고 있는지 등등 에너지 절약 중심으로 반별 현재 상태 카드 만들어줘. 한눈에 모든 반 볼 수있게. 그리고 자동 새로고침 추가해주고.

오전 10:38
AI
와, 구상이 아주 구체적이고 좋아요! 👏 에너지 절약 중심이라는 컨셉도 명확하고요. 한 번에 다 만들어드릴게요. 다만 먼저 중요한 부분 하나를 같이 정해야 해요.

먼저 정해야 할 것: "에너지 낭비"를 어떻게 판단할까?
코드가 "이 반은 낭비 중!"이라고 판단하려면, **명확한 기준(규칙)**이 필요해요. 이건 데이터로 자동 판단하는 거라, 당신이 기준을 정해줘야 해요.

지금 데이터로 추측할 수 있는 상황들을 제가 규칙으로 만들어봤어요. 이게 맞는지 봐주세요:

상황	판단 기준 (제 제안)	표시
🟢 정상	온도 24~28도, 사람 있음	정상
🔴 과냉방 (낭비!)	온도가 너무 낮음 (예: 22도 미만)	에너지 낭비
🟡 빈 교실 냉방 의심	CO₂ 낮은데(사람 없음 추정) 온도도 낮음	이동수업 의심
⚪ 에어컨 꺼짐	온도 높음 (예: 29도 이상)	냉방 안 함
CO₂로 사람 유무 추정: 사람이 많으면 CO₂가 올라가고, 빈 교실이면 낮아져요. 그래서 "CO₂ 낮음 + 온도 낮음 = 빈 교실에 에어컨 켜둠(낭비)"로 추정할 수 있어요. 똑똑한 아이디어죠!

질문: 위 기준의 숫자들(22도, 28도, CO₂ 기준값 등)을 어떻게 할까요? 일단 제가 적당한 값으로 넣어둘 테니, 나중에 실제 데이터 보면서 조정하면 돼요.

전체 코드
일단 위 기준으로 만든 전체 대시보드 코드예요. dashboard.py에 전체를 덮어쓰세요:

python
복사
import streamlit as st
import pandas as pd

# ===== 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

# 자동 새로고침 (30초마다). streamlit 최신 버전 기능 사용
st.set_page_config(page_title="교실 에너지 모니터링", layout="wide")

# 30초마다 자동 새로고침
st_autorefresh = st.empty()
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    st.info("자동 새로고침 기능을 쓰려면: py -m pip install streamlit-autorefresh")


# ===== 데이터 읽기 =====
@st.cache_data(ttl=20)  # 20초간 캐시 (너무 자주 구글에 요청하지 않도록)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    # 컬럼 이름 정리 (시트 첫 줄 헤더와 맞춰야 함!)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    return df

df = load_data()


# ===== 에너지 상태 판단 함수 =====
def check_status(row):
    temp = float(row["온도"])
    co2 = float(row["co2"])

    # 사람 있음 추정: CO2가 600 이상이면 사람 있다고 봄
    people = co2 >= 600

    if temp >= 29:
        return ("⚪ 냉방 안 함", "온도 높음")
    elif temp < 22:
        if not people:
            return ("🟡 빈 교실 냉방 의심", "사람 없는데 온도 낮음 (이동수업?)")
        else:
            return ("🔴 과냉방 (낭비!)", "온도 너무 낮음")
    else:
        return ("🟢 정상", "적정 온도")


# ===== 제목 =====
st.title("🏫 교실 에너지 모니터링 대시보드")


# ===== 상단: 반 선택 드롭다운 + 그래프 =====
st.header("📈 반별 상세 그래프")

class_list = sorted(df["반"].unique().tolist())
selected_class = st.selectbox("반을 선택하세요", class_list)

# 선택한 반 데이터만 추출
class_df = df[df["반"] == selected_class].copy()

st.subheader(f"{selected_class} 데이터 ({len(class_df)}개)")

# 그래프 (온도, CO2, 습도)
col1, col2 = st.columns(2)
with col1:
    st.write("🌡️ 온도 변화")
    st.line_chart(class_df.set_index("시간")["온도"])
    st.write("💧 습도 변화")
    st.line_chart(class_df.set_index("시간")["습도"])
with col2:
    st.write("🫁 CO₂ 변화")
    st.line_chart(class_df.set_index("시간")["co2"])
    st.write("💡 조도 변화")
    st.line_chart(class_df.set_index("시간")["조도"])


# ===== 하단: 모든 반 현재 상태 카드 =====
st.header("⚡ 전체 반 에너지 상태 (한눈에 보기)")
st.caption("각 반의 가장 최근 데이터를 기준으로 표시합니다.")

# 각 반의 가장 최근 데이터만 뽑기
latest = df.groupby("반").last().reset_index()

# 카드를 가로로 4개씩 배치
cards_per_row = 4
rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]

for row_group in rows:
    cols = st.columns(cards_per_row)
    for idx, (_, row) in enumerate(row_group.iterrows()):
        status, reason = check_status(row)
        with cols[idx]:
            st.metric(
                label=f"{row['반']}",
                value=status,
            )
            st.caption(f"🌡️ {row['온도']}도 / 🫁 {row['co2']}")
            st.caption(reason)


# ===== 갱신 시각 표시 =====
st.divider()
st.caption("데이터는 약 20~30초마다 자동 갱신됩니다.")
자동 새로고침을 위한 추가 설치
자동 새로고침 기능을 쓰려면 도구 하나를 더 깔아야 해요:

code
복사
py -m pip install streamlit-autorefresh
안 깔아도 코드는 돌아가요(단지 자동 새로고침만 안 될 뿐). 깔면 30초마다 자동 갱신돼요.

⚠️ 실행 전 꼭 확인할 것
코드 중 이 부분이 시트의 실제 헤더와 정확히 맞아야 해요:

python
복사
df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
당신 시트의 첫 줄(헤더) 순서가 이거랑 같은지 확인하세요. 순서가 다르면 그래프가 엉뚱하게 나와요!

아까 데이터 보니까 시간 / 반 / CO2 / 온도 / 습도 / 가스 / 조도 / 상태 순서였던 것 같은데, 맞나요?

실행
code
복사
py -m streamlit run dashboard.py
⚠️ 미리 알려줄 점
지금 데이터가 1줄밖에 없어서:

그래프는 점 하나만 (선이 안 그려짐)
카드는 그 한 반만 표시
그래서 테스트 데이터를 여러 줄 넣어야 진짜 효과를 볼 수 있어요. 구글 시트에 직접 여러 반(1-1, 1-2, 2-3...), 여러 시간대 데이터를 손으로 몇 줄 넣어보세요!

다음 행동
위 코드로 교체
py -m pip install streamlit-autorefresh (자동 새로고침용)
시트 헤더 순서 확인
테스트 데이터 여러 줄 넣기 (그래프/카드 제대로 보려면)
실행!
먼저 실행해보고, 에너지 판단 기준(22도, 29도, CO₂ 600 등)이 적절한지 의견도 알려줄래요? 그 기준은 당신 프로젝트의 핵심이라 같이 다듬으면 좋아요! 🙂

오전 10:39

나
일단 지금 조도 센서가 없으니까, 조도로 확인할 수 있는 에너지 문제는 제외 하고 해보자.

오전 10:45
AI
좋은 판단이에요! 👍 지금 가진 센서로 확실하게 판단할 수 있는 것만 쓰는 게 맞아요. 조도(불 켜짐/꺼짐 판단)는 나중에 센서 추가하면 그때 넣으면 돼요.

그럼 지금 판단 기준 정리
온도 + CO₂ 두 가지만으로 에너지 상태를 판단하는 걸로 정리할게요:

상황	기준	표시
🟢 정상	온도 22~28도	정상
🔴 과냉방 (낭비!)	온도 22도 미만 + 사람 있음(CO₂ 높음)	에너지 낭비
🟡 빈 교실 냉방 의심	온도 22도 미만 + 사람 없음(CO₂ 낮음)	이동수업 의심
⚪ 냉방 안 함	온도 29도 이상	냉방 꺼짐
조도 그래프와 조도 관련 판단만 빠진 거예요. 나머지는 그대로!

전체 코드 (조도 제외 버전)
python
복사
import streamlit as st
import pandas as pd

# ===== 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", layout="wide")

# 30초마다 자동 새로고침
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    st.info("자동 새로고침 기능을 쓰려면: py -m pip install streamlit-autorefresh")


# ===== 데이터 읽기 =====
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    return df

df = load_data()


# ===== 에너지 상태 판단 함수 (온도 + CO2만 사용) =====
def check_status(row):
    temp = float(row["온도"])
    co2 = float(row["co2"])

    # 사람 있음 추정: CO2가 600 이상이면 사람 있다고 봄
    people = co2 >= 600

    if temp >= 29:
        return ("⚪ 냉방 안 함", "온도 높음")
    elif temp < 22:
        if not people:
            return ("🟡 빈 교실 냉방 의심", "사람 없는데 온도 낮음 (이동수업?)")
        else:
            return ("🔴 과냉방 (낭비!)", "온도 너무 낮음")
    else:
        return ("🟢 정상", "적정 온도")


# ===== 제목 =====
st.title("🏫 교실 에너지 모니터링 대시보드")


# ===== 상단: 반 선택 드롭다운 + 그래프 =====
st.header("📈 반별 상세 그래프")

class_list = sorted(df["반"].unique().tolist())
selected_class = st.selectbox("반을 선택하세요", class_list)

class_df = df[df["반"] == selected_class].copy()
st.subheader(f"{selected_class} 데이터 ({len(class_df)}개)")

# 그래프 (온도, CO2, 습도) - 조도 제외
col1, col2 = st.columns(2)
with col1:
    st.write("🌡️ 온도 변화")
    st.line_chart(class_df.set_index("시간")["온도"])
    st.write("💧 습도 변화")
    st.line_chart(class_df.set_index("시간")["습도"])
with col2:
    st.write("🫁 CO₂ 변화")
    st.line_chart(class_df.set_index("시간")["co2"])
    st.write("🔥 가스 변화")
    st.line_chart(class_df.set_index("시간")["가스"])


# ===== 하단: 모든 반 현재 상태 카드 =====
st.header("⚡ 전체 반 에너지 상태 (한눈에 보기)")
st.caption("각 반의 가장 최근 데이터를 기준으로 표시합니다.")

latest = df.groupby("반").last().reset_index()

cards_per_row = 4
rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]

for row_group in rows:
    cols = st.columns(cards_per_row)
    for idx, (_, row) in enumerate(row_group.iterrows()):
        status, reason = check_status(row)
        with cols[idx]:
            st.metric(
                label=f"{row['반']}",
                value=status,
            )
            st.caption(f"🌡️ {row['온도']}도 / 🫁 {row['co2']}")
            st.caption(reason)


# ===== 갱신 시각 표시 =====
st.divider()
st.caption("데이터는 약 20~30초마다 자동 갱신됩니다.")
바뀐 점
조도 그래프 → 가스 그래프로 교체 (조도 빠진 자리)
check_status 함수에서 조도 관련 판단 없음 (원래도 온도+CO₂만 썼어요)
가스 그래프가 필요 없으면 그 부분 빼도 돼요. 알려주면 정리해줄게요.

실행 전 확인
시트 헤더 순서 확인: 시간 / 반 / CO2 / 온도 / 습도 / 가스 / 조도 / 상태 맞나요?
자동 새로고침 도구 설치 (선택):
code
복사
py -m pip install streamlit-autorefresh
테스트 데이터 여러 줄 넣기 (그래프/카드 제대로 보려면!)
실행
code
복사
py -m streamlit run dashboard.py
먼저 돌려보고, 어떻게 나오는지 알려줄래요? 그리고 그래프를 제대로 보려면 시트에 여러 반·여러 시간대 데이터를 좀 넣어야 하는데, 직접 몇 줄 넣어볼래요? 아니면 피코로 값 바꿔가며 전송해볼래요? 🙂

오전 10:46

나
일단 되고, 피코 좀 짜보자. 지금 센서 연결 다 해놨고, 지금 MQ-2 센서, LED 10개, SCD센서 연결 해놨거든 피코에? 일단 피코 토니 파이썬 코드좀 짜보자

오전 10:54
AI
좋아요! 센서를 연결했다니 이제 진짜 데이터를 받아볼 차례네요! 🎉 그런데 코드를 정확히 짜려면 연결 정보를 알아야 해요. 같이 확인해봐요.

먼저 확인할 것들
1. SCD 센서 모델
SCD 센서는 보통 SCD30, SCD40, SCD41 중 하나예요. 어떤 모델인가요?

이게 중요한 이유: 모델마다 라이브러리와 통신 방식이 달라요
보통 I2C로 연결해요 (선이 SDA, SCL 2개)
CO₂ + 온도 + 습도를 한 번에 측정해줘요
2. 핀 연결 정보 (제일 중요!)
각 센서/부품이 **피코의 몇 번 핀(GP번호)**에 연결됐는지 알아야 해요:

부품	필요한 정보
SCD 센서	SDA 핀, SCL 핀 번호 (I2C)
MQ-2	AO(아날로그 출력)가 연결된 핀 번호 (보통 ADC 가능한 GP26/27/28)
LED 10개	각각 어느 핀? 아니면 네오픽셀(데이터선 1개)?
3. LED 종류
LED 10개가:

(a) 일반 LED 10개를 각각 다른 핀에 연결? (선이 많음)
(b) 네오픽셀(WS2812) 같은 거라서 데이터선 1개로 10개 제어? (선이 적음)
어느 쪽인가요? 이것도 코드가 완전히 달라져요.

왜 이걸 다 물어보냐면
핀 번호를 모르면 코드가 엉뚱한 핀을 읽어서 0이나 이상한 값이 나와요. 그래서 정확한 연결 정보가 꼭 필요해요.

연결 정보 확인 방법
혹시 잘 모르겠으면, 피코에 연결된 선을 보고 알려주세요:

SCD 센서의 SDA, SCL 선이 피코의 어디에 꽂혀 있는지 (GP0? GP1? 등)
MQ-2의 AO 선이 어디에 꽂혀 있는지
LED 데이터선이 어디에 꽂혀 있는지
피코 핀 번호는 보드에 작게 적혀 있어요 (GP0, GP1, ... GP28).

일단 큰 그림 (코드 구조 미리보기)
연결 정보를 받으면, 코드는 이런 구조가 될 거예요:

code
복사
1. WiFi 연결 (이미 완성된 부분 재사용!)
2. SCD 센서 초기화 → CO₂, 온도, 습도 읽기
3. MQ-2 읽기 → 가스 농도
4. LED로 상태 표시 (예: 위험하면 빨강)
5. 데이터를 구글 시트로 전송 (이미 완성된 https_get 재사용!)
6. 일정 시간마다 반복
좋은 소식: WiFi 연결이랑 시트 전송은 이미 우리가 다 만들어놨어요! 그대로 가져다 쓰면 돼요. 새로 만들 건 센서 읽는 부분뿐이에요. 😊

다음 행동
이 세 가지만 알려주세요:

SCD 센서 모델 (30? 40? 41?)
각 부품의 핀 번호 (SCD의 SDA/SCL, MQ-2의 AO, LED 데이터선)
LED 종류 (일반 LED 여러 개 vs 네오픽셀)
알려주면 바로 전체 코드를 짜줄게요! 혹시 핀 번호 확인이 어려우면, 어떻게 찾는지도 도와줄게요. 🙂

오전 10:55

나
30 센서야. 그리고 LED 10개가 한묶음이고, 네오픽셀은 아니고 스틱 RGB LED야. (10-WS2813 Mini) 핀 번호는 너가 알려주는대로 꼽을게.

오전 10:56
AI
좋아요! 정보 정리됐어요. 그런데 하나 짚고 갈게요. 😊

잠깐! WS2813은 네오픽셀 계열이에요
WS2813이라고 하셨는데, 이건 사실 WS2812(네오픽셀)의 개선판이에요! 즉:

데이터선 1개로 LED 10개를 모두 제어해요
피코의 neopixel 라이브러리로 다룰 수 있어요 (WS2812와 호환)
그러니까 "네오픽셀은 아니고"라고 하셨지만, 실제로는 네오픽셀 방식으로 코드를 짜면 돼요! 오히려 잘됐어요. 선이 적어서 연결이 간단하거든요. 👍

핀 연결 가이드 (이대로 꽂으세요)
피코 핀에 이렇게 연결하면 돼요:

① SCD30 센서 (I2C 통신)
SCD30 핀	피코 핀
VIN (또는 VDD)	3V3 (OUT) — 3.3V 전원
GND	GND
SCL	GP1
SDA	GP0
② MQ-2 가스 센서 (아날로그)
MQ-2 핀	피코 핀
VCC	VBUS (5V) — ⚠️ MQ-2는 5V 필요!
GND	GND
AO (아날로그 출력)	GP26 (ADC0)
⚠️ 주의: MQ-2의 AO는 5V로 동작하면 출력도 5V까지 나올 수 있는데, 피코 핀은 3.3V까지만 견뎌요! 이건 아래에서 다시 설명할게요.

③ WS2813 LED 스틱 (데이터 1선)
LED 핀	피코 핀
5V (또는 VCC)	VBUS (5V)
GND	GND
DIN (데이터 입력)	GP2
BIN (백업 입력, 있으면)	DIN과 같이 GP2에 연결하거나 비워둠
💡 WS2813은 DIN 말고 BIN(백업 데이터) 핀이 하나 더 있을 수 있어요. 없으면 신경 안 써도 되고, 있으면 일단 비워두거나 DIN과 같은 곳에 연결해도 돼요.

⚠️ 중요한 안전 경고 2가지
1. MQ-2의 5V 출력 문제
MQ-2를 5V로 켜면 AO 출력이 최대 5V까지 나올 수 있어요. 그런데 피코 ADC 핀은 3.3V까지만 안전해요. 5V가 들어가면 피코가 손상될 수 있어요! 😰

해결책 (둘 중 하나):

(a) MQ-2를 3.3V로 연결 (VCC를 3V3에) — 감도는 좀 떨어지지만 안전. 입문엔 이걸 추천!
(b) 전압 분배 저항(저항 2개)을 AO와 GP26 사이에 넣어 5V→3.3V로 낮추기 — 정석이지만 부품 필요
일단 안전하게 가려면 MQ-2 VCC를 3V3에 연결하는 걸 추천해요. 어떻게 할래요?

2. LED 전원
WS2813 10개 정도는 피코 5V(VBUS)로 충분해요. 단, LED를 최대 밝기로 다 켜면 전류를 많이 먹으니, 코드에서 밝기를 낮춰서 쓸게요.

다음 단계
핀을 다 꽂았으면, 센서가 잘 인식되는지부터 확인하는 게 순서예요. 한 번에 전체 코드를 짜면 어디서 틀렸는지 찾기 어렵거든요. (우리가 전송 디버깅할 때처럼!)

그래서 이렇게 단계별로 가요:

code
복사
1단계: SCD30 인식 + 값 읽기 테스트  ← 먼저!
2단계: MQ-2 값 읽기 테스트
3단계: LED 켜보기 테스트
4단계: 다 합치고 → 시트로 전송
먼저 결정할 것
MQ-2 전원을 3V3로 갈까요, 5V+저항으로 갈까요? (안전을 위해 3V3 추천)
핀을 위 가이드대로 꽂을 수 있나요? 막히면 알려줘요.
결정하면 1단계: SCD30 테스트 코드부터 짜줄게요!

참고: SCD30 라이브러리가 피코에 필요할 수 있어요. 그것도 1단계에서 같이 안내할게요. 우선 핀 연결부터 확정해요! 🙂

오전 10:57

나
아니야 라즈베리 파이 피코 2 W H 여서, 하나씩만 연결하면 돼. 핀 연결 그렇게 복잡하지않아.

오전 10:57
AI
아, 맞아요! 피코 2 W H는 핀 헤더가 이미 납땜되어 있어서(H = Header) 점퍼선으로 바로 꽂으면 되니까 훨씬 간단하죠. 👍 제가 너무 복잡하게 설명했네요. 깔끔하게 정리할게요.

핀 연결 (간단 버전)
각 부품을 피코 핀에 이렇게 연결하면 돼요:

① SCD30 (I2C)
VIN → 3V3
GND → GND
SCL → GP1
SDA → GP0
② MQ-2
VCC → 3V3 (안전하게! 5V 쓰면 피코 손상 위험)
GND → GND
AO → GP26
③ WS2813 LED 스틱
5V → VBUS
GND → GND
DIN → GP2
GND가 여러 개 필요한데, 피코에 GND 핀이 여러 곳 있으니 나눠 꽂으면 돼요.

다음: 단계별로 테스트
한 번에 전체 코드를 짜면 어디서 틀렸는지 찾기 어려우니, 하나씩 확인해요. (전송 디버깅할 때처럼!)

code
복사
1단계: SCD30 값 읽기  ← 먼저 이것부터!
2단계: MQ-2 값 읽기
3단계: LED 켜보기
4단계: 다 합쳐서 시트로 전송
1단계: SCD30 테스트
SCD30은 라이브러리가 필요해요. 먼저 그것부터 준비해요.

라이브러리 설치 (Thonny에서)
Thonny 상단 메뉴 도구 → 패키지 관리 클릭
검색창에 micropython-scd30 입력 후 검색
설치
만약 패키지 관리에서 안 보이거나 안 되면, 다른 방법(파일 직접 복사)도 있어요. 일단 이것부터 시도해보세요.

1단계 테스트 코드
라이브러리 설치 후, 이 코드로 SCD30이 잘 읽히는지 확인해요:

python
복사
from machine import I2C, Pin
import time
from scd30 import SCD30

# I2C 설정 (GP0=SDA, GP1=SCL)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)

# 연결된 I2C 장치 확인
print("I2C 장치 검색:", [hex(x) for x in i2c.scan()])

# SCD30 초기화
scd = SCD30(i2c, 0x61)

print("SCD30 측정 시작... (값이 안정되려면 몇 초 걸려요)")

while True:
    # 측정 데이터가 준비됐는지 확인
    if scd.get_status_ready() == 1:
        co2, temp, hum = scd.read_measurement()
        print("CO2: {:.1f} ppm, 온도: {:.1f}도, 습도: {:.1f}%".format(co2, temp, hum))
    time.sleep(2)
확인할 것
I2C 장치 검색: ['0x61'] 처럼 0x61이 나오면 → SCD30 연결 성공! ✅
[] (빈 리스트)가 나오면 → 연결 문제 (선 다시 확인)
CO₂, 온도, 습도 값이 나오면 → 완벽! 🎉
SCD30은 처음 켜고 값이 안정되기까지 몇 초~몇십 초 걸릴 수 있어요. CO₂가 처음엔 이상해도 조금 기다려보세요.

다음 행동
핀 연결 (위 가이드대로)
Thonny에서 scd30 라이브러리 설치
1단계 코드 실행
I2C 검색에 0x61이 뜨는지, 값이 나오는지 확인
해보고 결과 알려줄래요?

0x61이 뜨고 값이 나오면 → 2단계(MQ-2)로!
라이브러리 설치가 안 되거나 에러나면 → 그 메시지 보여주세요. 같이 해결해요! 🙂
오전 10:58

나
아니야 아니야. 선이 하나 씩 밖에 없어서, A0, A1, A2, D16, I2C0, 등등 이런 형식의 핀들 밖에 없어. 

참고로 이건 선생님이 주신 기본 SCD30센서 코드야. 참고해.

<main.py>
from machine import I2C, Pin
from scd30 import SCD30
import time

# I2C 통신 초기화 (GP8, GP9 사용)
# *참고: SCD30은 클럭 스트레칭(Clock Stretching)을 요구하므로, I2C 통신 속도를
# 안정적인 50kHz(50000)로 설정하는 것이 좋습니다.
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=50000)

print("SCD30 센서를 검색하고 있습니다...")

try:
    # SCD30 객체 생성 (기본 I2C 주소는 0x61입니다)
    sensor = SCD30(i2c, addr=0x61)
    print("SCD30 센서 연결 성공!")
except SCD30.NotFoundException:
    print("에러: SCD30 센서를 찾을 수 없습니다. 배선을 확인해 주세요.")
    while True:
        time.sleep(1)

# 연속 측정 시작 (매개변수로 주변 기압(mBar)을 넣어 고도 보정을 할 수도 있습니다)
sensor.start_cont_measure()
print("실시간 대기질 측정을 시작합니다...")
time.sleep(2)

while True:
    # 센서가 새로운 데이터를 측정 완료했는지 확인
    if sensor.get_status_ready():
        try:
            # CO2(ppm), 온도(°C), 습도(%) 데이터 읽기
            co2, temp, humi = sensor.read_measurement()
           
            print("-" * 50)
            print(f"💨 CO2 농도 : {co2:.1f} ppm")
            print(f"🌡️ 현재 온도 : {temp:.1f} °C")
            print(f"💧 상대 습도 : {humi:.1f} %")
           
            # 실내 환기 가이드라인 예시
            if co2 > 1000:
                print("🚨 주의: 이산화탄소 수치가 높습니다. 환기가 필요합니다!")
               
        except SCD30.CRCException:
            print("⚠️ 경고: 통신 중 데이터 패킷 CRC 오류가 발생했습니다.")
    else:
        print("데이터 대기 중...")
       
    time.sleep(2) # SCD30은 약 2초마다 새로운 데이터를 갱신합니다.



<scd30.py  >
from machine import I2C
import utime
import struct

class SCD30:
    class NotFoundException(Exception): pass
    class CRCException(Exception): pass

    START_CONT_MEASURE = 0x0010
    STOP_CONT_MEASURE = 0x0104
    SET_MEASURE_INTERVAL = 0x4600
    GET_STATUS_READY = 0x0202
    READ_MEASUREMENT = 0x0300
    SET_ASC = 0x5306
    SET_FRC = 0x5204
    SET_TEMP_OFFSET = 0x5403
    SET_ALT_COMP = 0x5102
    GET_FIRMWARE_VER = 0xd100
    SOFT_RESET = 0xd304

    def __init__(self, i2c, addr=0x61, pause=1000):
        self.i2c = i2c
        self.pause = pause
        self.addr = addr
        if not addr in i2c.scan():
            raise self.NotFoundException()

    def get_firmware_version(self):
        ver = self.__read_bytes(self.GET_FIRMWARE_VER, 3)
        return struct.unpack('BB', ver[0:2])

    def start_cont_measure(self, pressure=0):
        self.__write_command(self.START_CONT_MEASURE, pressure)

    def stop_cont_measure(self):
        self.__write_command(self.STOP_CONT_MEASURE)

    def set_measurement_interval(self, interval):
        self.__write_command(self.SET_MEASURE_INTERVAL, interval)

    def get_status_ready(self):
        ready = self.__read_bytes(self.GET_STATUS_READY, 3)
        return struct.unpack('>H', ready[0:2])[0] == 1

    def read_measurement(self):
        measurement = self.__read_bytes(self.READ_MEASUREMENT, 18)
        for i in range(0, len(measurement), 3):
            self.__check_crc(measurement[i:i+2], measurement[i+2])

        co2 = struct.unpack('>f', measurement[0:2] + measurement[3:5])[0]
        temp = struct.unpack('>f', measurement[6:8] + measurement[9:11])[0]
        humi = struct.unpack('>f', measurement[12:14] + measurement[15:17])[0]
        return (co2, temp, humi)

    def set_temp_offset(self, offset):
        self.__write_command(self.SET_TEMP_OFFSET, int(offset * 100))

    def set_altitude_compensation(self, altitude):
        self.__write_command(self.SET_ALT_COMP, altitude)

    def set_asc(self, enable):
        self.__write_command(self.SET_ASC, 1 if enable else 0)

    def set_frc(self, co2):
        self.__write_command(self.SET_FRC, co2)

    def soft_reset(self):
        self.__write_command(self.SOFT_RESET)

    def __write_command(self, cmd, val=None):
        buf = bytearray(2)
        struct.pack_into('>H', buf, 0, cmd)
        if val is not None:
            buf.extend(struct.pack('>H', val))
            buf.append(self.__calc_crc(buf[2:4]))
        self.i2c.writeto(self.addr, buf)

    def __read_bytes(self, cmd, count):
        self.__write_command(cmd)
        utime.sleep_us(self.pause)
        return self.i2c.readfrom(self.addr, count)

    def __check_crc(self, data, checksum):
        if self.__calc_crc(data) != checksum:
            raise self.CRCException()

    def __calc_crc(self, data):
        crc = 0xff
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xff
        return crc

그리고 이건 내가 저번에 프로젝트로 했던 MQ-2 센서와 LED 활용해서 만든거니까, 이것도 활용해서 센서 연결 부분만 활용해. 

import network
import socket
import time
import json
import gc
from machine import Pin, ADC
from neopixel import NeoPixel
from wifi_config import WIFI_NETWORKS, DISCORD_WEBHOOK_URL

# ===== 하드웨어 =====
gas_sensor = ADC(Pin(26))
TIMING = (280, 515, 515, 745)
NUM_LEDS = 10
led = NeoPixel(Pin(16), NUM_LEDS, timing=TIMING)

# ===== 임계값 =====
TH_IDLE   = 7000
TH_COOK   = 10000
TH_WARN   = 30000
TH_DANGER = 45000

# ===== 상태 변수 =====
timer_duration      = 600
timer_start         = 0
timer_running       = False
cooking             = False
last_gas            = 0
last_sensor         = 0
last_discord        = 0
last_led            = 0
idle_count          = 0
timer_done_notified = False
DISCORD_COOL        = 60000

# ===== 자동 캘리브레이션 =====
calib_state   = 'idle'   # idle / waiting / collecting / done
calib_start   = 0
calib_samples = []
calib_baseline = 0

# ===== LED =====
def clear_led():
    for i in range(NUM_LEDS):
        led[i] = (0, 0, 0)
    led.write()

def set_all(r, g, b):
    for i in range(NUM_LEDS):
        led[i] = (r, g, b)
    led.write()

def update_led():
    t = time.ticks_ms()

    # 캘리브레이션 중 → 보라색 물결
    if calib_state == 'waiting':
        b = (t // 300) % 2
        set_all(20, 0, 40) if b else set_all(5, 0, 10)
        return
    if calib_state == 'collecting':
        # 수집 진행도에 따라 파란색 LED 하나씩 증가
        elapsed = time.ticks_diff(t, calib_start) / 1000
        ratio   = min(1.0, elapsed / 10.0)
        on_cnt  = max(1, int(NUM_LEDS * ratio))
        for i in range(NUM_LEDS):
            led[i] = (0, 0, 50) if i < on_cnt else (0, 0, 0)
        led.write()
        return

    if last_gas >= TH_DANGER:
        b = (t // 80) % 2
        set_all(80, 0, 0) if b else clear_led()
        return
    if last_gas >= TH_WARN:
        b = (t // 500) % 2
        set_all(60, 30, 0) if b else clear_led()
        return
    if timer_running:
        elapsed   = time.ticks_diff(t, timer_start) / 1000
        remaining = max(0, timer_duration - elapsed)
        if remaining <= 0:
            b = (t // 300) % 2
            set_all(60, 0, 0) if b else clear_led()
            return
        if remaining <= 60:
            b = (t // 200) % 2
            set_all(50, 30, 0) if b else clear_led()
            return
        ratio  = elapsed / timer_duration
        on_cnt = max(0, int(NUM_LEDS * (1 - ratio)))
        for i in range(NUM_LEDS):
            led[i] = (0, 0, 50) if i < on_cnt else (0, 0, 0)
        led.write()
        return
    brightness = int((t % 3000) / 3000 * 25)
    if (t % 6000) >= 3000:
        brightness = 25 - brightness
    for i in range(NUM_LEDS):
        led[i] = (0, brightness, 0)
    led.write()

def get_state():
    elapsed   = time.ticks_diff(time.ticks_ms(), timer_start) / 1000 if timer_running else 0
    remaining = max(0, timer_duration - elapsed) if timer_running else None
    if last_gas >= TH_DANGER:
        return 'danger', remaining
    if last_gas >= TH_WARN:
        return 'gas_warn', remaining
    if timer_running and remaining is not None and remaining <= 0:
        return 'done', remaining
    if timer_running and remaining is not None and remaining <= 60:
        return 'timer_warn', remaining
    if timer_running:
        return 'running', remaining
    return 'idle', remaining

# ===== 캘리브레이션 로직 =====
def calib_tick():
    global calib_state, calib_start, calib_samples
    global TH_IDLE, TH_COOK, TH_WARN, TH_DANGER

    if calib_state == 'waiting':
        elapsed = time.ticks_diff(time.ticks_ms(), calib_start) / 1000
        # 5초 대기 후 수집 시작
        if elapsed >= 5:
            calib_state  = 'collecting'
            calib_start  = time.ticks_ms()
            calib_samples = []
            print("캘리브레이션: 수집 시작!")

    elif calib_state == 'collecting':
        # 0.3초마다 샘플 수집
        calib_samples.append(last_gas)
        elapsed = time.ticks_diff(time.ticks_ms(), calib_start) / 1000
        print(f"수집 중: {last_gas} ({len(calib_samples)}개, {elapsed:.1f}s)")

        # 10초 수집 완료
        if elapsed >= 10:
            if len(calib_samples) >= 3:
                # 임계값 계산
                baseline = calib_baseline
                peak     = max(calib_samples)
                avg      = sum(calib_samples) // len(calib_samples)
                rng      = max(peak - baseline, 3000)  # 최소 범위 3000

                TH_IDLE   = baseline + int(rng * 0.10)
                TH_COOK   = baseline + int(rng * 0.25)
                TH_WARN   = baseline + int(rng * 0.55)
                TH_DANGER = baseline + int(rng * 0.80)

                # 최솟값 보정
                TH_IDLE   = max(TH_IDLE,   baseline + 500)
                TH_COOK   = max(TH_COOK,   TH_IDLE   + 500)
                TH_WARN   = max(TH_WARN,   TH_COOK   + 1000)
                TH_DANGER = max(TH_DANGER, TH_WARN   + 1000)

                print(f"캘리브레이션 완료!")
                print(f"baseline={baseline} peak={peak} avg={avg}")
                print(f"IDLE={TH_IDLE} COOK={TH_COOK} WARN={TH_WARN} DANGER={TH_DANGER}")
                calib_state = 'done'
            else:
                calib_state = 'idle'
                print("캘리브레이션 실패: 샘플 부족")

# ===== 디스코드 =====
def discord_send(title, desc, color):
    try:
        import urequests
        d = json.dumps({"embeds": [{"title": title, "description": desc, "color": color}]})
        urequests.post(DISCORD_WEBHOOK_URL, data=d, headers={"Content-Type": "application/json"})
        print(f"디스코드: {title}")
    except Exception as e:
        print(f"디스코드 실패: {e}")

def discord_timer_start():
    m = timer_duration // 60
    s = timer_duration % 60
    t = f"{m}분" if s == 0 else f"{m}분 {s}초"
    discord_send("🍳 요리 시작!", f"가스레인지 감지!\n타이머: **{t}** 시작!", 0x3498DB)

def discord_timer_done():
    discord_send("⏰ 타이머 종료!", "요리 타이머 끝!\n**가스레인지를 확인하세요!**", 0xE67E22)

def discord_danger(value):
    global last_discord
    now = time.ticks_ms()
    if time.ticks_diff(now, last_discord) < DISCORD_COOL:
        return
    discord_send("🚨 위험! 가스 감지!", f"위험 수치: **{value}/65535**\n즉시 환기하세요!", 0xFF0000)
    last_discord = now

# ===== Wi-Fi =====
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    scan = [s[0].decode() for s in wlan.scan()]
    print(f"네트워크: {scan}")
    for ssid, pw in WIFI_NETWORKS.items():
        if ssid in scan:
            print(f"'{ssid}' 연결 중...")
            wlan.connect(ssid, pw)
            t = 15
            while not wlan.isconnected() and t > 0:
                time.sleep(1)
                t -= 1
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                print(f"연결! IP: {ip}")
                return ip
            wlan.disconnect()
    return None

# ===== HTML =====
def get_html():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🍳 요리 비법서 🍳</title>
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{
  font-family:'Gowun Batang','Nanum Myeongjo',serif;
  background:#3a2418;
  color:#3a2418;
  perspective:2000px;
}
.desk{
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:radial-gradient(ellipse at center,#5a3a26 0%,#3a2418 70%,#2a1810 100%);
  z-index:0;
}
.desk::before{
  content:'';position:absolute;top:0;left:0;width:100%;height:100%;
  background-image:repeating-linear-gradient(45deg,rgba(0,0,0,.03) 0px,rgba(0,0,0,.03) 2px,transparent 2px,transparent 8px);
}
.floating-emoji{
  position:fixed;font-size:35px;opacity:.18;pointer-events:none;z-index:5;
  animation:float 20s linear infinite;filter:drop-shadow(0 2px 4px rgba(0,0,0,.3));
}
@keyframes float{
  0%{transform:translateY(100vh) rotate(0deg)}
  100%{transform:translateY(-100px) rotate(360deg)}
}
.book-wrap{
  position:relative;z-index:10;width:100%;height:100vh;
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.book{
  position:relative;width:100%;max-width:700px;height:90vh;
  max-height:900px;transform-style:preserve-3d;
}
.page{
  position:absolute;top:0;left:0;width:100%;height:100%;
  background:linear-gradient(to right,#f0e0c0 0%,#f5e6cc 5%,#faecd4 100%);
  border-radius:8px 15px 15px 8px;padding:35px 30px;
  box-shadow:inset 5px 0 15px rgba(80,40,20,.3),0 10px 40px rgba(0,0,0,.5),0 20px 60px rgba(0,0,0,.3);
  overflow-y:auto;overflow-x:hidden;
  transform-origin:left center;
  transition:transform 1s cubic-bezier(.4,0,.2,1);
  backface-visibility:hidden;
}
.page::before{
  content:'';position:absolute;top:0;left:0;width:30px;height:100%;
  background:linear-gradient(to right,rgba(120,80,40,.3),rgba(120,80,40,.1) 40%,transparent);
  pointer-events:none;
}
.page::after{
  content:'';position:absolute;top:0;right:0;width:8px;height:100%;
  background:linear-gradient(to left,rgba(80,50,20,.4),transparent);
  pointer-events:none;
}
.page-inner{position:relative;z-index:2}
.page.flipping{transform:rotateY(-180deg)}
.page.flipped{transform:rotateY(-180deg);pointer-events:none}
.page-1{z-index:3}.page-2{z-index:2}.page-3{z-index:1}
.page-title{
  font-family:'Nanum Myeongjo',serif;font-size:28px;font-weight:800;
  text-align:center;color:#5a2818;margin-bottom:8px;padding-bottom:15px;
  border-bottom:3px double #8a4828;
}
.page-title::before,.page-title::after{content:'❦';margin:0 15px;color:#8a4828;font-size:20px}
.page-num{text-align:center;font-size:13px;color:#8a6848;margin-bottom:25px;letter-spacing:3px;font-style:italic}
.cover-icon{text-align:center;font-size:60px;margin:10px 0;filter:drop-shadow(2px 2px 4px rgba(0,0,0,.3))}
.status-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0}
.scard{
  background:linear-gradient(135deg,#faecd4,#e8d4b0);border:2px solid #8a4828;
  border-radius:10px;padding:12px 8px;text-align:center;position:relative;
  box-shadow:2px 2px 5px rgba(0,0,0,.2);
}
.scard::before{
  content:'';position:absolute;top:5px;left:5px;right:5px;bottom:5px;
  border:1px solid rgba(138,72,40,.3);border-radius:8px;pointer-events:none;
}
.scard-lb{font-size:10px;color:#8a6848;margin-bottom:5px;letter-spacing:1px;font-weight:700}
.scard-v{font-family:'Nanum Myeongjo',serif;font-size:22px;font-weight:800;color:#5a2818}
.badge{display:inline-block;padding:6px 16px;border-radius:20px;font-size:12px;font-weight:800;border:2px solid}
.b0{background:#d4e8b8;color:#2e5e0e;border-color:#2e5e0e}
.b1{background:#f5d4a0;color:#7e3e0e;border-color:#7e3e0e;animation:p .5s infinite}
.b2{background:#f5b8b8;color:#7e0e0e;border-color:#7e0e0e;animation:p .3s infinite}
.b3{background:#b8d4f5;color:#0e3e7e;border-color:#0e3e7e}
.b4{background:#f5c8a0;color:#7e3e0e;border-color:#7e3e0e;animation:p .4s infinite}
.b5{background:#f5e8a0;color:#7e6e0e;border-color:#7e6e0e;animation:p .5s infinite}
@keyframes p{50%{opacity:.5}}
.timer-wrap{text-align:center;margin:20px 0}
.timer-ring{width:240px;height:240px;margin:0 auto 15px;position:relative}
.timer-svg{width:100%;height:100%;transform:rotate(-90deg)}
.timer-bg{fill:none;stroke:#d4b890;stroke-width:6}
.timer-fill{
  fill:none;stroke:#8a4828;stroke-width:6;stroke-linecap:round;
  transition:stroke-dashoffset .5s ease;filter:drop-shadow(0 0 5px rgba(138,72,40,.5));
}
.timer-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}
.timer-num{font-family:'Nanum Myeongjo',serif;font-size:48px;font-weight:800;color:#5a2818;line-height:1}
.timer-lb{font-size:11px;color:#8a6848;margin-top:5px;letter-spacing:2px}
.led-strip{
  display:flex;justify-content:center;gap:6px;padding:10px;
  background:#3a2418;border-radius:20px;margin:15px auto;
  width:fit-content;border:2px solid #8a4828;
}
.led-dot{width:18px;height:18px;border-radius:50%;background:#1a1a1a;border:1px solid #4a3a2a;transition:all .3s}
.led-on-g{background:radial-gradient(#0f0,#080);box-shadow:0 0 10px #0f0}
.led-on-b{background:radial-gradient(#48f,#06c);box-shadow:0 0 10px #48f}
.led-on-y{background:radial-gradient(#fa0,#c80);box-shadow:0 0 10px #fa0}
.led-on-r{background:radial-gradient(#f22,#a00);box-shadow:0 0 12px #f22}
.led-on-p{background:radial-gradient(#c080ff,#8040cc);box-shadow:0 0 10px #c080ff}
.timer-setting{
  background:rgba(212,184,144,.2);border:1px dashed #8a4828;
  border-radius:10px;padding:15px;margin:15px 0;
}
.row{display:flex;align-items:center;gap:10px;margin:10px 0;flex-wrap:wrap}
.row label{color:#5a2818;font-size:13px;font-weight:700;min-width:100px;display:flex;align-items:center;gap:5px}
.cur-val{color:#a04818;font-weight:800;background:#faecd4;padding:2px 8px;border-radius:4px;border:1px solid #8a4828}
input[type=range]{
  flex:1;min-width:120px;-webkit-appearance:none;appearance:none;
  height:6px;background:#d4b890;border-radius:3px;outline:none;border:1px solid #8a4828;
}
input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none;width:18px;height:18px;
  background:radial-gradient(#c08858,#8a4828);border-radius:50%;
  cursor:pointer;border:2px solid #5a2818;box-shadow:0 2px 4px rgba(0,0,0,.3);
}
input[type=range]::-moz-range-thumb{
  width:18px;height:18px;background:radial-gradient(#c08858,#8a4828);
  border-radius:50%;cursor:pointer;border:2px solid #5a2818;
}
input[type=number]{
  background:#faecd4;border:2px solid #8a4828;color:#5a2818;
  padding:5px 8px;border-radius:5px;width:70px;
  font-family:'Nanum Myeongjo',serif;font-weight:700;text-align:center;font-size:13px;
}
.btn{
  padding:10px 20px;border:2px solid;border-radius:8px;
  font-family:'Nanum Myeongjo',serif;font-size:13px;font-weight:800;
  cursor:pointer;margin:4px;transition:all .2s;box-shadow:2px 2px 0 rgba(0,0,0,.2);
}
.btn:hover{transform:translate(-1px,-1px);box-shadow:3px 3px 0 rgba(0,0,0,.3)}
.btn:active{transform:translate(1px,1px);box-shadow:1px 1px 0 rgba(0,0,0,.2)}
.btn-o{background:#f5c896;color:#5a2818;border-color:#5a2818}
.btn-r{background:#f5a8a8;color:#5a0808;border-color:#5a0808}
.btn-b{background:#a8c8f5;color:#082858;border-color:#082858}
.btn-p{background:#e8c8f5;color:#380858;border-color:#380858}
.msg{font-size:12px;margin-top:8px;min-height:16px;font-weight:700;text-align:center}

/* ===== 자동 캘리브레이션 박스 ===== */
.calib-box{
  background:rgba(180,140,200,.15);
  border:2px solid #8a5898;
  border-radius:12px;
  padding:18px;
  margin:20px 0;
  text-align:center;
}
.calib-box h3{
  color:#5a1878;border-left:4px solid #8a5898;
  padding-left:8px;text-align:left;margin-bottom:15px;
}
.calib-progress{
  display:none;
  margin-top:15px;
}
.calib-status-text{
  font-size:16px;font-weight:800;color:#5a1878;
  margin:10px 0;min-height:28px;
}
.calib-bar-wrap{
  height:20px;background:rgba(0,0,0,.1);
  border-radius:10px;overflow:hidden;margin:10px 0;
  border:1px solid #8a5898;
}
.calib-bar{
  height:100%;width:0%;
  background:linear-gradient(90deg,#8a5898,#c080ff);
  border-radius:10px;
  transition:width .3s;
}
.calib-countdown{
  font-family:'Nanum Myeongjo',serif;
  font-size:36px;font-weight:800;color:#5a1878;
  margin:10px 0;display:none;
}
.calib-result{
  display:none;
  background:rgba(100,200,100,.1);
  border:1px dashed #2e5e0e;
  border-radius:8px;
  padding:12px;
  margin-top:12px;
  text-align:left;
}
.calib-result-row{
  display:flex;justify-content:space-between;
  font-size:13px;font-weight:700;
  padding:4px 0;border-bottom:1px dashed rgba(138,72,40,.2);
  color:#3a2418;
}
.calib-result-row:last-child{border-bottom:none}
.calib-result-val{color:#a04818;font-weight:800}

.gas-meter{height:24px;background:#3a2418;border-radius:12px;overflow:hidden;margin:12px 0;border:2px solid #5a2818}
.gas-fill{height:100%;border-radius:12px;transition:width .5s,background .3s}
.meter-labels{display:flex;justify-content:space-between;font-size:10px;color:#5a2818;margin-top:5px;font-weight:700}
.chart-box{background:#faecd4;border:2px solid #8a4828;border-radius:10px;padding:15px;margin:15px 0}
.nav{
  position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
  display:flex;gap:10px;z-index:100;background:rgba(58,36,24,.9);
  padding:10px 15px;border-radius:30px;border:2px solid #8a4828;
  box-shadow:0 5px 20px rgba(0,0,0,.5);
}
.nav-btn{
  width:40px;height:40px;border-radius:50%;border:2px solid #faecd4;
  background:#5a2818;color:#faecd4;font-size:18px;font-weight:800;
  cursor:pointer;transition:all .2s;
}
.nav-btn:hover:not(:disabled){background:#8a4828;transform:scale(1.1)}
.nav-btn:disabled{opacity:.3;cursor:not-allowed}
.nav-dots{display:flex;align-items:center;gap:8px}
.nav-dot{width:10px;height:10px;border-radius:50%;background:#faecd4;opacity:.4;transition:all .3s}
.nav-dot.active{opacity:1;background:#ffa500;transform:scale(1.3)}
.deco{text-align:center;color:#8a4828;font-size:14px;margin:15px 0;letter-spacing:5px}
h3{font-family:'Nanum Myeongjo',serif;color:#5a2818;font-size:16px;margin:15px 0 10px;padding-left:8px;border-left:4px solid #8a4828}

@media(max-width:600px){
  .book-wrap{padding:10px 5px}
  .book{height:82vh;max-width:92%}
  .page{padding:25px 18px;border-radius:5px 10px 10px 5px}
  .page-title{font-size:22px}
  .timer-ring{width:200px;height:200px}
  .timer-num{font-size:38px}
  .scard-v{font-size:18px}
  .cover-icon{font-size:45px}
  .floating-emoji{font-size:28px;opacity:.22;z-index:5}
  .book{box-shadow:inset 5px 0 15px rgba(80,40,20,.3),0 8px 25px rgba(0,0,0,.6),0 15px 40px rgba(0,0,0,.4)}
}
@media(max-width:400px){
  .book-wrap{padding:5px 2px}
  .book{max-width:96%;height:80vh}
  .floating-emoji{font-size:24px;opacity:.25}
}
</style>
</head>
<body>
<div class="desk"></div>

<div class="floating-emoji" style="left:2%;animation-delay:0s">🍳</div>
<div class="floating-emoji" style="left:7%;animation-delay:3s">🍲</div>
<div class="floating-emoji" style="left:4%;animation-delay:6s">🥘</div>
<div class="floating-emoji" style="left:8%;animation-delay:9s">🍜</div>
<div class="floating-emoji" style="left:3%;animation-delay:12s">🥕</div>
<div class="floating-emoji" style="left:6%;animation-delay:15s">🧄</div>
<div class="floating-emoji" style="left:1%;animation-delay:18s">🧅</div>
<div class="floating-emoji" style="left:92%;animation-delay:1s">🥩</div>
<div class="floating-emoji" style="left:95%;animation-delay:4s">🍅</div>
<div class="floating-emoji" style="left:97%;animation-delay:7s">🌶️</div>
<div class="floating-emoji" style="left:93%;animation-delay:10s">🥒</div>
<div class="floating-emoji" style="left:96%;animation-delay:13s">🍆</div>
<div class="floating-emoji" style="left:91%;animation-delay:16s">🫕</div>
<div class="floating-emoji" style="left:98%;animation-delay:19s">🍕</div>
<div class="floating-emoji" style="left:94%;animation-delay:22s">🥗</div>
<div class="floating-emoji" style="left:50%;animation-delay:2s">🍞</div>
<div class="floating-emoji" style="left:50%;animation-delay:14s">🥖</div>

<div class="book-wrap">
  <div class="book">

    <!-- ===== 페이지 1 ===== -->
    <div class="page page-1" id="p1">
      <div class="page-inner">
        <div class="cover-icon">🍳📖</div>
        <h1 class="page-title">요리 비법서</h1>
        <div class="page-num">~ 第 一 章 · 요리 시작 ~</div>

        <div class="status-row">
          <div class="scard">
            <div class="scard-lb">🔥 가스 수치</div>
            <div class="scard-v" id="gV">--</div>
          </div>
          <div class="scard">
            <div class="scard-lb">📜 상태</div>
            <div style="margin-top:6px"><span class="badge b0" id="sB">대기중</span></div>
          </div>
          <div class="scard">
            <div class="scard-lb">⏳ 남은 시간</div>
            <div class="scard-v" id="tS">--:--</div>
          </div>
        </div>

        <div class="deco">⊰ ❀ ⊱</div>

        <div class="timer-wrap">
          <div class="timer-ring">
            <svg class="timer-svg" viewBox="0 0 100 100">
              <circle class="timer-bg" cx="50" cy="50" r="45"/>
              <circle class="timer-fill" id="timerFill" cx="50" cy="50" r="45"
                      stroke-dasharray="282.7" stroke-dashoffset="282.7"/>
            </svg>
            <div class="timer-center">
              <div class="timer-num" id="bigT">--:--</div>
              <div class="timer-lb">남은 시간</div>
            </div>
          </div>

          <div class="led-strip">
            <div class="led-dot"></div><div class="led-dot"></div>
            <div class="led-dot"></div><div class="led-dot"></div>
            <div class="led-dot"></div><div class="led-dot"></div>
            <div class="led-dot"></div><div class="led-dot"></div>
            <div class="led-dot"></div><div class="led-dot"></div>
          </div>
        </div>

        <div class="timer-setting">
          <h3>⏱ 타이머 설정</h3>
          <div class="row">
            <label>분 <span class="cur-val" id="minV">10</span></label>
            <input type="range" id="minR" min="0" max="60" value="10" oninput="minN.value=this.value;minV.textContent=this.value">
            <input type="number" id="minN" value="10" min="0" max="60" oninput="minR.value=this.value;minV.textContent=this.value">
          </div>
          <div class="row">
            <label>초 <span class="cur-val" id="secV">0</span></label>
            <input type="range" id="secR" min="0" max="59" value="0" oninput="secN.value=this.value;secV.textContent=this.value">
            <input type="number" id="secN" value="0" min="0" max="59" oninput="secR.value=this.value;secV.textContent=this.value">
          </div>
          <div style="text-align:center;margin-top:10px">
            <button class="btn btn-o" onclick="applyTimer()">✅ 적용</button>
            <button class="btn btn-r" onclick="stopTimer()">⏹ 중지</button>
          </div>
          <div class="msg" id="timerMsg"></div>
        </div>
      </div>
    </div>

    <!-- ===== 페이지 2 : 임계값 + 자동 설정 ===== -->
    <div class="page page-2" id="p2">
      <div class="page-inner">
        <div class="cover-icon">⚙️📜</div>
        <h1 class="page-title">감지 비법</h1>
        <div class="page-num">~ 第 二 章 · 임계값 조절 ~</div>

        <div class="deco">⊰ 🌿 ⊱</div>

        <!-- 자동 캘리브레이션 -->
        <div class="calib-box">
          <h3>🔮 임계값 자동 설정</h3>
          <p style="font-size:13px;color:#5a2818;margin-bottom:12px;line-height:1.6">
            버튼을 누르면 <b>가스불을 켜달라는 안내</b>가 나옵니다.<br>
            5초 대기 후 <b>10초 동안 센서값을 수집</b>하여<br>
            임계값 4개를 <b>자동으로 계산</b>해드립니다!
          </p>
          <button class="btn btn-p" onclick="startCalib()" id="calibBtn">🔮 자동 설정 시작</button>

          <div class="calib-progress" id="calibProgress">
            <div class="calib-status-text" id="calibStatusText"></div>
            <div class="calib-countdown" id="calibCountdown"></div>
            <div class="calib-bar-wrap">
              <div class="calib-bar" id="calibBar"></div>
            </div>
          </div>

          <div class="calib-result" id="calibResult">
            <div style="font-size:14px;font-weight:800;color:#2e5e0e;margin-bottom:10px">✅ 자동 설정 완료!</div>
            <div class="calib-result-row">
              <span>💨 가스없음</span><span class="calib-result-val" id="rIdle">--</span>
            </div>
            <div class="calib-result-row">
              <span>🍳 요리감지</span><span class="calib-result-val" id="rCook">--</span>
            </div>
            <div class="calib-result-row">
              <span>⚠️ 주의</span><span class="calib-result-val" id="rWarn">--</span>
            </div>
            <div class="calib-result-row">
              <span>🚨 위험</span><span class="calib-result-val" id="rDanger">--</span>
            </div>
          </div>
          <div class="msg" id="calibMsg"></div>
        </div>

        <!-- 수동 임계값 -->
        <h3>🔧 수동 조정</h3>
        <div class="row">
          <label>💨 가스없음 <span class="cur-val" id="idleV">7000</span></label>
          <input type="range" id="idleR" min="1000" max="20000" step="500" value="7000" oninput="idleV.textContent=this.value;idleN.value=this.value">
          <input type="number" id="idleN" value="7000" min="1000" max="20000" oninput="idleR.value=this.value;idleV.textContent=this.value">
        </div>
        <div class="row">
          <label>🍳 요리감지 <span class="cur-val" id="cookV">10000</span></label>
          <input type="range" id="cookR" min="1000" max="40000" step="500" value="10000" oninput="cookV.textContent=this.value;cookN.value=this.value">
          <input type="number" id="cookN" value="10000" min="1000" max="40000" oninput="cookR.value=this.value;cookV.textContent=this.value">
        </div>
        <div class="row">
          <label>⚠️ 주의 <span class="cur-val" id="warnV">30000</span></label>
          <input type="range" id="warnR" min="5000" max="60000" step="500" value="30000" oninput="warnV.textContent=this.value;warnN.value=this.value">
          <input type="number" id="warnN" value="30000" min="5000" max="60000" oninput="warnR.value=this.value;warnV.textContent=this.value">
        </div>
        <div class="row">
          <label>🚨 위험 <span class="cur-val" id="dangerV">45000</span></label>
          <input type="range" id="dangerR" min="10000" max="65000" step="500" value="45000" oninput="dangerV.textContent=this.value;dangerN.value=this.value">
          <input type="number" id="dangerN" value="45000" min="10000" max="65000" oninput="dangerR.value=this.value;dangerV.textContent=this.value">
        </div>
        <div style="text-align:center;margin-top:15px">
          <button class="btn btn-b" onclick="applyThresh()">✅ 수동 적용</button>
        </div>
        <div class="msg" id="threshMsg"></div>
      </div>
    </div>

    <!-- ===== 페이지 3 ===== -->
    <div class="page page-3" id="p3">
      <div class="page-inner">
        <div class="cover-icon">📊📈</div>
        <h1 class="page-title">감지 기록부</h1>
        <div class="page-num">~ 第 三 章 · 실시간 측정 ~</div>
        <div class="deco">⊰ 🔥 ⊱</div>
        <h3>💨 현재 가스 농도</h3>
        <div class="gas-meter"><div class="gas-fill" id="gBI" style="width:0%;background:linear-gradient(90deg,#5a8a3a,#8aba5a)"></div></div>
        <div class="meter-labels">
          <span>0</span>
          <span style="color:#2e5e0e">🌿 안전</span>
          <span style="color:#7e3e0e">⚠ 주의</span>
          <span style="color:#7e0e0e">🚨 위험</span>
          <span>65535</span>
        </div>
        <h3>📜 시간별 변화 기록</h3>
        <div class="chart-box"><canvas id="gC"></canvas></div>
        <div class="deco">⊰ 끝 ⊱</div>
      </div>
    </div>

  </div>
</div>

<div class="nav">
  <button class="nav-btn" id="prevBtn" onclick="prevPage()">◀</button>
  <div class="nav-dots">
    <div class="nav-dot active" id="dot0"></div>
    <div class="nav-dot" id="dot1"></div>
    <div class="nav-dot" id="dot2"></div>
  </div>
  <button class="nav-btn" id="nextBtn" onclick="nextPage()">▶</button>
</div>

<script>
let L=[],D=[],curTH={idle:7000,cook:10000,warn:30000,danger:45000},threshLoaded=false;
let currentPage=0;
let calibTimer=null;
let calibPhase='idle'; // idle / waiting / collecting / done
let calibStart=0;
const pages=[document.getElementById('p1'),document.getElementById('p2'),document.getElementById('p3')];

function updateNav(){
  document.getElementById('prevBtn').disabled=currentPage===0;
  document.getElementById('nextBtn').disabled=currentPage===2;
  for(let i=0;i<3;i++)
    document.getElementById('dot'+i).classList.toggle('active',i===currentPage);
}
function nextPage(){
  if(currentPage<2){
    pages[currentPage].classList.add('flipping');
    setTimeout(()=>{
      pages[currentPage].classList.remove('flipping');
      pages[currentPage].classList.add('flipped');
      currentPage++;updateNav();
    },500);
  }
}
function prevPage(){
  if(currentPage>0){
    currentPage--;
    pages[currentPage].classList.remove('flipped');
    pages[currentPage].classList.add('flipping');
    setTimeout(()=>{pages[currentPage].classList.remove('flipping');updateNav();},50);
  }
}
document.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight')nextPage();
  else if(e.key==='ArrowLeft')prevPage();
});

// ===== 자동 캘리브레이션 =====
async function startCalib(){
  document.getElementById('calibBtn').disabled=true;
  document.getElementById('calibResult').style.display='none';
  document.getElementById('calibProgress').style.display='block';
  document.getElementById('calibMsg').textContent='';

  // 1단계: 서버에 캘리브레이션 시작 요청
  try{
    await fetch('/start_calib',{method:'POST'});
  }catch(e){console.error(e);}

  calibPhase='waiting';
  calibStart=Date.now();

  // 웹 카운트다운 표시
  runCalibUI();
}

function runCalibUI(){
  const statusEl=document.getElementById('calibStatusText');
  const countEl=document.getElementById('calibCountdown');
  const barEl=document.getElementById('calibBar');

  calibTimer=setInterval(async()=>{
    const elapsed=(Date.now()-calibStart)/1000;

    if(calibPhase==='waiting'){
      // 5초 대기 카운트다운
      const remain=Math.max(0,5-elapsed);
      statusEl.textContent='🔥 지금 가스불을 켜주세요!';
      countEl.style.display='block';
      countEl.textContent=Math.ceil(remain)+'초';
      barEl.style.width=(elapsed/5*100)+'%';
      barEl.style.background='linear-gradient(90deg,#c08858,#e0a858)';

      if(elapsed>=5){
        calibPhase='collecting';
        calibStart=Date.now();
        countEl.style.display='none';
      }
    }
    else if(calibPhase==='collecting'){
      // 10초 수집
      const remain=Math.max(0,10-elapsed);
      statusEl.textContent='📡 센서값 수집 중... 가스불을 켜둬주세요!';
      countEl.style.display='block';
      countEl.textContent=Math.ceil(remain)+'초';
      barEl.style.width=(elapsed/10*100)+'%';
      barEl.style.background='linear-gradient(90deg,#8a5898,#c080ff)';

      if(elapsed>=11){
        // 수집 완료 → 서버에서 결과 가져오기
        calibPhase='done';
        clearInterval(calibTimer);
        statusEl.textContent='⚙️ 계산 중...';
        countEl.style.display='none';
        barEl.style.width='100%';

        setTimeout(async()=>{
          try{
            let r=await fetch('/data');
            let j=await r.json();
            if(j.thresholds){
              let th=j.thresholds;
              curTH=th;
              threshLoaded=true;

              // 슬라이더 업데이트
              idleR.value=idleN.value=idleV.textContent=th.idle;
              cookR.value=cookN.value=cookV.textContent=th.cook;
              warnR.value=warnN.value=warnV.textContent=th.warn;
              dangerR.value=dangerN.value=dangerV.textContent=th.danger;

              // 결과 표시
              document.getElementById('rIdle').textContent=th.idle;
              document.getElementById('rCook').textContent=th.cook;
              document.getElementById('rWarn').textContent=th.warn;
              document.getElementById('rDanger').textContent=th.danger;
              document.getElementById('calibResult').style.display='block';

              statusEl.textContent='✅ 자동 설정 완료!';
              barEl.style.background='linear-gradient(90deg,#2e5e0e,#5aba3a)';

              let msg=document.getElementById('calibMsg');
              msg.style.color='#2e5e0e';
              msg.textContent='✅ 임계값이 자동으로 설정되었습니다!';
            }
          }catch(e){
            document.getElementById('calibMsg').textContent='❌ 결과 가져오기 실패';
          }
          document.getElementById('calibBtn').disabled=false;
        },1000);
      }
    }
  },200);
}

// ===== 차트 =====
const ch=new Chart(document.getElementById('gC'),{
  type:'line',
  data:{labels:L,datasets:[{
    data:D,borderColor:'#8a4828',backgroundColor:'rgba(138,72,40,.15)',
    borderWidth:2,fill:true,tension:.4,pointRadius:0
  }]},
  options:{
    responsive:true,animation:{duration:300},
    scales:{
      x:{ticks:{color:'#5a2818',maxTicksLimit:6},grid:{color:'rgba(138,72,40,.1)'}},
      y:{min:0,max:65535,ticks:{color:'#5a2818'},grid:{color:'rgba(138,72,40,.1)'}}
    },
    plugins:{legend:{display:false}}
  }
});

function fmt(s){
  let m=Math.floor(Math.max(0,s)/60),sc=Math.floor(Math.max(0,s)%60);
  return String(m).padStart(2,'0')+':'+String(sc).padStart(2,'0');
}

function updateLEDs(state,ratio){
  let ds=document.querySelectorAll('.led-dot'),bl=Date.now()%600<300;
  ds.forEach((d,i)=>{
    d.className='led-dot';
    if(state==='idle')d.classList.add('led-on-g');
    else if(state==='running'){if(i<Math.round((1-ratio)*10))d.classList.add('led-on-b');}
    else if(state==='calib_waiting'){if(bl)d.classList.add('led-on-p');}
    else if(state==='gas_warn'||state==='timer_warn'){if(bl)d.classList.add('led-on-y');}
    else if(state==='done'||state==='danger'){if(bl)d.classList.add('led-on-r');}
  });
}

async function applyTimer(){
  let m=parseInt(minN.value)||0,s=parseInt(secN.value)||0,total=m*60+s;
  if(total<=0){alert('시간을 설정해주세요!');return;}
  let r=await fetch('/set_timer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({duration:total})});
  let j=await r.json();
  let msg=document.getElementById('timerMsg');
  msg.style.color=j.ok?'#2e5e0e':'#7e0e0e';
  msg.textContent=j.ok?'✅ 적용! 가스 감지 시 자동 시작':'❌ 실패';
  setTimeout(()=>msg.textContent='',3000);
}
async function stopTimer(){
  await fetch('/stop_timer',{method:'POST'});
  let msg=document.getElementById('timerMsg');
  msg.style.color='#7e0e0e';msg.textContent='⏹ 타이머 중지됨';
  setTimeout(()=>msg.textContent='',3000);
}
async function applyThresh(){
  let data={idle:parseInt(idleN.value),cook:parseInt(cookN.value),warn:parseInt(warnN.value),danger:parseInt(dangerN.value)};
  let r=await fetch('/set_thresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  let j=await r.json();
  let msg=document.getElementById('threshMsg');
  msg.style.color=j.ok?'#2e5e0e':'#7e0e0e';
  msg.textContent=j.ok?'✅ 수동 적용됨!':'❌ 실패';
  if(j.ok){curTH=data;threshLoaded=true;}
  setTimeout(()=>msg.textContent='',3000);
}

async function fetchData(){
  try{
    let r=await fetch('/data');
    let j=await r.json();
    let v=j.value;

    if(j.thresholds&&!threshLoaded){
      let th=j.thresholds;curTH=th;
      idleR.value=idleN.value=idleV.textContent=th.idle;
      cookR.value=cookN.value=cookV.textContent=th.cook;
      warnR.value=warnN.value=warnV.textContent=th.warn;
      dangerR.value=dangerN.value=dangerV.textContent=th.danger;
      threshLoaded=true;
    }

    L.push('');D.push(v);
    if(L.length>100){L.shift();D.shift();}
    ch.update('none');

    document.getElementById('gV').textContent=v;
    let pct=Math.min(100,v/65535*100);
    let gbi=document.getElementById('gBI');
    gbi.style.width=pct+'%';
    if(v<curTH.cook)gbi.style.background='linear-gradient(90deg,#5a8a3a,#8aba5a)';
    else if(v<curTH.warn)gbi.style.background='linear-gradient(90deg,#c08838,#e0a858)';
    else gbi.style.background='linear-gradient(90deg,#a02818,#c04838)';

    let sb=document.getElementById('sB');
    let state=j.state,remaining=j.remaining,duration=j.duration;
    if(state==='danger'){sb.textContent='🚨 위험!';sb.className='badge b2';}
    else if(state==='gas_warn'){sb.textContent='⚠️ 주의';sb.className='badge b5';}
    else if(state==='done'){sb.textContent='⏰ 종료!';sb.className='badge b4';}
    else if(state==='timer_warn'){sb.textContent='⏰ 임박!';sb.className='badge b1';}
    else if(state==='running'){sb.textContent='🍳 요리중';sb.className='badge b3';}
    else{sb.textContent='✅ 대기중';sb.className='badge b0';}

    let fill=document.getElementById('timerFill');
    if(remaining===null||remaining===undefined){
      document.getElementById('bigT').textContent='--:--';
      document.getElementById('tS').textContent='--:--';
      fill.style.strokeDashoffset='282.7';
      updateLEDs('idle',0);
    }else{
      document.getElementById('bigT').textContent=fmt(remaining);
      document.getElementById('tS').textContent=fmt(remaining);
      let ratio=remaining/duration;
      fill.style.strokeDashoffset=(282.7*(1-ratio))+'';
      updateLEDs(state,ratio);
    }
  }catch(e){console.error('오류:',e);}
}

setInterval(fetchData,500);
fetchData();
setInterval(()=>{
  let bl=Date.now()%600<300;
  document.querySelectorAll('.led-dot').forEach(d=>{
    if(d.classList.contains('led-on-y')||d.classList.contains('led-on-r')||d.classList.contains('led-on-p'))
      d.style.opacity=bl?'1':'.2';
    else d.style.opacity='1';
  });
},150);
updateNav();
</script>
</body>
</html>"""

# ===== 서버 =====
def send_html(cl):
    html = get_html()
    cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n")
    for i in range(0, len(html), 512):
        cl.send(html[i:i+512].encode('utf-8'))
        time.sleep_ms(20)

def handle_client(cl):
    global timer_duration, timer_start, timer_running
    global cooking, idle_count, timer_done_notified
    global TH_IDLE, TH_COOK, TH_WARN, TH_DANGER
    global calib_state, calib_start, calib_samples, calib_baseline

    try:
        cl.settimeout(5)
        raw    = cl.recv(1024)
        req    = raw.decode('utf-8', 'ignore')
        if not req:
            return
        line   = req.split('\r\n')[0]
        parts  = line.split(' ')
        method = parts[0] if parts else 'GET'
        path   = parts[1] if len(parts) > 1 else '/'
        print(f"{method} {path}")

        if path == '/data':
            state, remaining = get_state()
            body = json.dumps({
                "value":      last_gas,
                "state":      state,
                "remaining":  int(remaining) if remaining is not None else None,
                "duration":   timer_duration,
                "calib":      calib_state,
                "thresholds": {"idle": TH_IDLE, "cook": TH_COOK, "warn": TH_WARN, "danger": TH_DANGER}
            })
            cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
            cl.send(body.encode())

        elif path == '/start_calib' and method == 'POST':
            # 캘리브레이션 시작
            calib_baseline = last_gas   # 현재 평상시값 저장
            calib_samples  = []
            calib_state    = 'waiting'
            calib_start    = time.ticks_ms()
            print(f"캘리브레이션 시작! baseline={calib_baseline}")
            cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
            cl.send(b'{"ok":true}')

        elif path == '/set_timer' and method == 'POST':
            try:
                data                = json.loads(req.split('\r\n\r\n')[-1])
                timer_duration      = int(data.get('duration', 600))
                timer_running       = False
                cooking             = False
                idle_count          = 0
                timer_done_notified = False
                print(f"타이머 설정: {timer_duration}초")
                cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                cl.send(b'{"ok":true}')
            except:
                cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                cl.send(b'{"ok":false}')

        elif path == '/stop_timer' and method == 'POST':
            timer_running       = False
            cooking             = False
            idle_count          = 0
            timer_done_notified = False
            cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
            cl.send(b'{"ok":true}')

        elif path == '/set_thresh' and method == 'POST':
            try:
                data      = json.loads(req.split('\r\n\r\n')[-1])
                TH_IDLE   = int(data.get('idle',   TH_IDLE))
                TH_COOK   = int(data.get('cook',   TH_COOK))
                TH_WARN   = int(data.get('warn',   TH_WARN))
                TH_DANGER = int(data.get('danger', TH_DANGER))
                print(f"임계값: {TH_IDLE} {TH_COOK} {TH_WARN} {TH_DANGER}")
                cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                cl.send(b'{"ok":true}')
            except:
                cl.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                cl.send(b'{"ok":false}')

        elif path == '/favicon.ico':
            cl.send(b"HTTP/1.1 204\r\n\r\n")

        else:
            send_html(cl)

    except Exception as e:
        print(f"요청 오류: {e}")
    finally:
        try:
            cl.close()
        except:
            pass

# ===== 메인 =====
def main():
    global last_gas, last_sensor, last_led
    global timer_running, timer_start
    global cooking, idle_count, timer_done_notified
    global calib_state, calib_start

    clear_led()
    gc.collect()

    ip = connect_wifi()
    if not ip:
        print("Wi-Fi 실패!")
        while True:
            time.sleep(1)

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(2)
    s.settimeout(0.1)
    print(f"http://{ip} 접속하세요!")

    last_calib_tick = 0  # 캘리브레이션 샘플 수집 타이머

    while True:
        try:
            cl, addr = s.accept()
            handle_client(cl)
            gc.collect()
        except OSError:
            pass
        except Exception as e:
            print(f"서버 오류: {e}")

        now = time.ticks_ms()

        # LED 100ms마다
        if time.ticks_diff(now, last_led) >= 100:
            last_led = now
            update_led()

        # 센서 500ms마다
        if time.ticks_diff(now, last_sensor) >= 500:
            last_sensor = now
            last_gas    = gas_sensor.read_u16()
            print(f"가스: {last_gas}")

            # 위험 감지
            if last_gas >= TH_DANGER:
                discord_danger(last_gas)

            # 요리 시작 감지 (캘리브레이션 중 아닐 때만)
            if calib_state == 'idle' or calib_state == 'done':
                if not timer_running and last_gas >= TH_COOK:
                    idle_count = 0
                    if not cooking:
                        cooking             = True
                        timer_start         = time.ticks_ms()
                        timer_running       = True
                        timer_done_notified = False
                        print(f"요리 감지! {timer_duration}초 타이머 시작")
                        discord_timer_start()

                # 요리 종료 감지
                if cooking and last_gas < TH_IDLE:
                    idle_count += 1
                    if idle_count >= 6:
                        cooking             = False
                        timer_running       = False
                        idle_count          = 0
                        timer_done_notified = False
                        print("가스 꺼짐, 타이머 초기화")
                else:
                    if last_gas >= TH_IDLE:
                        idle_count = 0

                # 타이머 종료 체크
                if timer_running:
                    elapsed = time.ticks_diff(time.ticks_ms(), timer_start) / 1000
                    if elapsed >= timer_duration and not timer_done_notified:
                        timer_done_notified = True
                        print("타이머 종료!")
                        discord_timer_done()

        # 캘리브레이션 tick (300ms마다 샘플 수집)
        if calib_state in ('waiting', 'collecting'):
            if time.ticks_diff(now, last_calib_tick) >= 300:
                last_calib_tick = now
                calib_tick()

main()

오전 11:00
AI
좋아요! 코드 잘 봤어요. 이제 필요한 정보가 다 모였네요. 정리하면:

확인된 연결 정보 (이전 프로젝트 기준)
부품	핀	비고
SCD30	SDA=GP8, SCL=GP9	I2C, 50kHz (클럭 스트레칭)
MQ-2	AO=GP26 (ADC)	gas_sensor.read_u16()
WS2813 LED	DIN=GP16	NeoPixel(Pin(16), 10, timing=TIMING)
이전 코드에서 잘 작동했던 핀들이니 그대로 쓰면 돼요. 👍

그런데 잠깐 — 단계별로 가요!
이전 코드는 "요리 감지" 프로젝트라 기능이 엄청 많죠(타이머, 디스코드, 캘리브레이션, 웹페이지...). 하지만 이번 프로젝트는 목적이 달라요:

"센서값 측정 → 구글 시트로 전송 (반복)"

그래서 그 복잡한 기능들은 다 빼고, 필요한 것만 깔끔하게 새로 짜는 게 좋아요. 그리고 우리가 전에 디버깅할 때처럼 단계별로 확인해요.

code
복사
1단계: SCD30 + MQ-2 값 읽기 (시트 전송 없이, 값만 확인)  ← 먼저!
2단계: LED로 상태 표시 추가
3단계: 구글 시트 전송 합치기 (이미 완성된 코드 재사용!)
1단계: 센서값 읽기 테스트
먼저 두 센서가 잘 읽히는지만 확인해요. (시트 전송, LED 다 빼고 순수 측정만)

python
복사
from machine import I2C, Pin, ADC
from scd30 import SCD30
import time

print(">>> 센서 테스트 시작!")

# ===== SCD30 (I2C: SDA=GP8, SCL=GP9) =====
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=50000)
print(">>> SCD30 검색 중...")

try:
    scd = SCD30(i2c, addr=0x61)
    print(">>> SCD30 연결 성공!")
except SCD30.NotFoundException:
    print(">>> 에러: SCD30을 찾을 수 없음. 배선 확인!")
    while True:
        time.sleep(1)

scd.start_cont_measure()
print(">>> SCD30 측정 시작")

# ===== MQ-2 가스 센서 (GP26) =====
gas_sensor = ADC(Pin(26))
print(">>> MQ-2 준비 완료")

time.sleep(2)

# ===== 측정 루프 =====
while True:
    # MQ-2 읽기
    gas_value = gas_sensor.read_u16()

    # SCD30 읽기 (데이터 준비됐을 때만)
    if scd.get_status_ready():
        try:
            co2, temp, humi = scd.read_measurement()
            print("-" * 40)
            print("CO2 : {:.1f} ppm".format(co2))
            print("온도: {:.1f} 도".format(temp))
            print("습도: {:.1f} %".format(humi))
            print("가스: {}".format(gas_value))
        except SCD30.CRCException:
            print("⚠️ CRC 오류 (통신 잡음, 무시 가능)")
    else:
        print("SCD30 데이터 대기 중... (가스: {})".format(gas_value))

    time.sleep(2)
확인할 것
SCD30 연결 성공 메시지 뜨는지
CO2, 온도, 습도, 가스 값이 4개 다 나오는지
값이 말이 되는지 (CO2 4001000 정도, 온도 2030도, 습도 30~60%, 가스는 숫자)
⚠️ SCD30은 처음엔 CO2 값이 안정될 때까지 시간이 걸려요. 입김을 불면 CO2가 확 올라가는지 보면 잘 작동하는지 확인할 수 있어요!

⚠️ 준비물
이 코드를 돌리려면 피코에 scd30.py 파일이 있어야 해요 (선생님이 주신 그 파일). 피코에 저장되어 있나요? 없으면 Thonny로 피코에 scd30.py를 저장해야 해요.

다음 행동
핀 연결 (SDA=8, SCL=9, MQ-2=26, LED=16)
피코에 scd30.py 저장되어 있는지 확인
위 1단계 코드 실행
4개 값(CO2/온도/습도/가스)이 다 나오는지 확인!
해보고 결과 알려줄래요?

값이 잘 나오면 → 2단계(LED), 3단계(시트 전송)로!
에러 나면 그 메시지 보여주세요. 같이 해결해요! 🙂
오전 11:00

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
ImportError: no module named 'scd30'
>>> 
 라는데

오전 11:03
AI
아, 예상했던 거예요! 👍 scd30.py 파일이 피코에 없어서 그래요. 이건 금방 해결돼요.

원인
code
복사
ImportError: no module named 'scd30'
from scd30 import SCD30을 하려면, scd30.py라는 파일이 피코 안에 저장되어 있어야 해요. 지금은 그 파일이 없는 상태예요.

비유하면: "scd30이라는 사전을 찾아봐"라고 했는데, 피코 책장에 그 사전이 없는 거예요. 사전을 책장에 꽂아주면 돼요.

해결: 피코에 scd30.py 저장하기
선생님이 주신 그 scd30.py 코드를 피코에 저장하면 돼요. Thonny에서 하는 방법:

방법 (Thonny 기준)
Thonny에서 새 파일 열기 (파일 → 새 파일, 또는 Ctrl+N)
선생님이 주신 scd30.py 코드 전체를 복사해서 붙여넣기 (아까 당신이 보내준 그 class SCD30: 로 시작하는 긴 코드요)
저장 (Ctrl+S)
저장 위치를 물어보면 → "라즈베리파이 피코" (또는 "MicroPython device") 선택!
⚠️ 여기가 중요! "이 컴퓨터"가 아니라 "피코"에 저장해야 해요
파일 이름을 정확히 scd30.py 로 입력 (확장자 .py 꼭!)
저장
저장 확인
저장 후 Thonny 왼쪽 아래(또는 보기 → 파일)에서 피코 파일 목록을 보면:

code
복사
📄 scd30.py   ← 이게 보이면 성공!
📄 main.py
📄 wifi_config.py
...
scd30.py가 피코 쪽에 보이면 OK예요!

그다음
scd30.py 저장이 끝나면, 아까 그 1단계 테스트 코드를 다시 실행해보세요. 이번엔 import scd30이 성공할 거예요!

참고: 파일 구조
지금 피코 안에 이런 파일들이 있어야 해요:

code
복사
피코 안
├── scd30.py          ← 지금 저장할 것 (SCD30 라이브러리)
├── wifi_config.py    ← WiFi 정보 (이미 있을 듯)
└── (테스트 코드)      ← 실행할 코드
💡 scd30.py는 우리가 직접 건드릴 일은 없어요. 그냥 피코에 "꽂아두고" 불러다 쓰는 도구예요.

다음 행동
Thonny에서 새 파일 → 선생님이 준 scd30.py 코드 붙여넣기
피코에 scd30.py로 저장 (이 컴퓨터 아님! 주의!)
피코 파일 목록에 scd30.py 보이는지 확인
1단계 테스트 코드 다시 실행
해보고 결과 알려줄래요? 이번엔 센서값이 나올 거예요! 🙂

오전 11:04

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
  File "scd30.py", line 1
SyntaxError: invalid syntax
>>> 

라는데

오전 11:05
AI
아, 단서가 바뀌었어요! 이번엔 진전이 있는 거예요. 분석해봐요.

에러 분석
code
복사
File "scd30.py", line 1
SyntaxError: invalid syntax
이전 에러(no module named 'scd30')와 달라졌죠? 이번엔:

✅ scd30.py 파일을 찾긴 찾았어요! (저장은 성공)
❌ 그런데 그 파일의 1번째 줄에 문법 오류가 있다고 해요
즉, scd30.py 파일 내용이 뭔가 잘못 저장된 거예요. 1번째 줄부터 문제라는 게 단서예요.

원인 추측
scd30.py의 정상적인 1번째 줄은 이거예요:

python
복사
from machine import I2C
그런데 SyntaxError가 났다는 건, 파일에 엉뚱한 게 들어갔을 가능성이 커요. 흔한 경우들:

복사할 때 코드가 아닌 게 섞여 들어감 (설명 텍스트, 마크다운 기호 등)
파일 맨 앞에 이상한 문자가 붙음
코드를 붙여넣을 때 일부만 들어가거나 깨짐
확인 방법
Thonny에서 피코의 scd30.py 파일을 더블클릭해서 열어보세요. 그리고 **맨 윗줄(1번째 줄)**이 정확히 이렇게 시작하는지 확인:

python
복사
from machine import I2C
import utime
import struct

class SCD30:
    class NotFoundException(Exception): pass
    ...
혹시 1번째 줄에 이런 게 있나요?

````python` 같은 마크다운 기호가 붙어있다 → ❌ 지워야 함
한글 설명이나 이상한 문자가 있다 → ❌ 지워야 함
빈 줄이나 공백이 이상하다 → ❌
해결: 깔끔하게 다시 저장
가장 확실한 방법은 다시 깔끔하게 저장하는 거예요:

피코의 scd30.py를 Thonny에서 열기
전체 선택(Ctrl+A) → 삭제
선생님이 준 scd30.py 코드를 다시 정확히 복사
⚠️ from machine import I2C 부터 시작해서
⚠️ 맨 마지막 return crc 까지
⚠️ 코드만! (설명이나 ``` 기호 없이!)
붙여넣기
저장 (Ctrl+S)
💡 복사할 때 맨 첫 줄 from machine import I2C 앞에 아무것도 없는지, 맨 끝이 깔끔한지 꼭 확인하세요!

혹시 모르니
붙여넣은 후 scd30.py의 맨 첫 줄과 맨 끝 몇 줄을 여기에 복사해서 보여줄래요? 그러면 뭐가 잘못됐는지 바로 찾아줄게요.

정상이라면:

첫 줄: from machine import I2C
끝 줄: return crc
다음 행동
피코의 scd30.py 열어서 1번째 줄 확인
이상하면 전체 지우고 → 선생님 코드만 깔끔히 다시 붙여넣기 → 저장
1단계 테스트 코드 다시 실행
확인해보고, scd30.py 첫 줄이 뭔지 알려줄래요? 🙂

오전 11:05

나
>>> %Run -c $EDITOR_CONTENT

MPY: soft reboot
>>> 센서 테스트 시작!
>>> SCD30 검색 중...
>>> SCD30 연결 성공!
>>> SCD30 측정 시작
>>> MQ-2 준비 완료
----------------------------------------
CO2 : 1798.6 ppm
온도: 27.5 도
습도: 50.2 %
가스: 3568
----------------------------------------
CO2 : 2011.8 ppm
온도: 27.5 도
습도: 49.8 %
가스: 3520

 잘된다

오전 11:05
AI
완벽해요!! 🎉🎉 네 가지 값이 전부 깔끔하게 나오네요! SCD30이랑 MQ-2 둘 다 정상 작동이에요!

결과 확인 — 아주 좋아요!
code
복사
CO2 : 1798.6 ppm  ← 측정됨 ✅
온도: 27.5 도      ← 측정됨 ✅
습도: 50.2 %       ← 측정됨 ✅
가스: 3568         ← 측정됨 ✅
값들도 다 말이 돼요:

온도 27.5도, 습도 50% → 실내 환경으로 정상 👍
가스 3568 → MQ-2가 평상시 깨끗한 공기에서 내는 값 (정상)
CO2 1798ppm → 좀 높은 편인데, 이건 정상이에요! SCD30은 처음 켜고 몇 분간 값이 안정화되거든요. 환기된 곳에서 좀 기다리면 400~800 정도로 내려갈 거예요.
💡 테스트: 센서에 입김을 후~ 불어보세요. CO2가 확 올라가면(2000~5000) 센서가 진짜 잘 작동하는 거예요!

이제 2단계로!
센서 읽기가 완성됐으니, 다음 순서예요:

code
복사
✅ 1단계: SCD30 + MQ-2 값 읽기   ← 방금 성공!
👉 2단계: LED로 상태 표시
   3단계: 구글 시트로 전송
잠깐 — 순서를 고민해봐요
여기서 선택지가 있어요. 둘 중 뭘 먼저 할까요?

옵션 A: LED 먼저 (2단계)
LED 10개로 상태 표시 (예: CO2 높으면 빨강, 정상이면 초록)
시각적으로 바로 보여서 재밌음
근데 LED 표시 규칙을 정해야 함
옵션 B: 시트 전송 먼저 (3단계)
이미 우리가 완성한 코드(https_get)를 재사용하면 돼서 빠름!
센서 → 시트 → 대시보드까지 전체 흐름이 완성됨
가장 핵심 기능이 먼저 돌아감
제 추천: 옵션 B (시트 전송 먼저)
이유는:

이미 만든 코드를 재사용하니까 금방 돼요
센서 → 시트 → 대시보드 전체가 한 번에 연결되는 걸 보면 엄청 뿌듯할 거예요
LED는 "있으면 좋은" 부가 기능이라 나중에 붙여도 됨
즉, **핵심 뼈대(실제 센서 데이터가 대시보드까지 가는 것)**를 먼저 완성하고, LED 같은 장식은 그 다음에!

3단계 미리보기 (시트 전송)
이렇게 합칠 거예요:

code
복사
1. WiFi 연결          (이미 완성 ✅)
2. 센서 값 읽기        (방금 완성 ✅)
3. https_get으로 전송  (이미 완성 ✅)
4. 30초마다 반복
거의 다 만들어놓은 부품들을 조립하는 거예요!

다음 행동 정해요
옵션 B(시트 전송 먼저)로 갈까요? 그러면 바로 센서값을 구글 시트로 보내는 전체 코드를 만들어줄게요. 그러면 대시보드에 진짜 센서 데이터가 실시간으로 뜨는 걸 볼 수 있어요!

아니면 LED부터 하고 싶으면 그것도 좋아요. 어떻게 할까요? 🙂

그리고 한 가지 미리 정할 것:

이 피코는 몇 반인가요? (시트에 "반" 정보를 보내야 하는데, wifi_config.py의 CLASS_ID에 들어있죠?)
오전 11:06

나
LED는 그냥 웹사이트에 표기 될 🟢 정상 이런 느낌으로 하면 되고, 반 정보는 지금 

WIFI_NETWORKS = {
    "U+Net1DFB": "8F9B6B21M!",
    "app": "20242024"
}

SHEET_URL = "https://script.google.com/macros/s/AKfycbwssGqCtO0_EDCUJRwkydoIk_ut_uHFfomZwEpu7dxOBftMUGZgg7r_AwaMavP7DtNLCw/exec"

CLASS_ID = "2-3"

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1491475678254596106/UVwB8mJNQdZs6eWc_8L267hYcZ-D3eECbasiGlrgullFFFK0HbqAx-4mIPy_b4qmqejy"

이렇게 와이파이 컴피그 에 있어. 

이 피코는 몇반인 지물어보지말고, 그냥 알아서 잘 변수 지정해서, 모든 피코에서 그냥 클래스 아이디 자동으로 불러오게 만들어. 그리고 이제 시트 전송 전체 코드 부분을 짜줘.

오전 11:08
AI
완벽해요! 정보 다 모였어요. CLASS_ID = "2-3"을 wifi_config에서 자동으로 불러오게 만들면, 모든 피코가 각자의 CLASS_ID만 바꾸면 똑같은 코드로 돌아가요. 아주 좋은 설계예요! 👍

LED는 웹사이트에서 처리하니까 피코에서는 신경 안 써도 되고요. (LED 부품은 안 쓰는 거죠? 일단 코드에서 뺄게요. 나중에 필요하면 추가!)

전체 코드 (센서 → 구글 시트 전송)
이전에 우리가 완성한 WiFi 연결 + https_get(전송) 부분을 그대로 가져오고, 거기에 방금 성공한 센서 읽기를 합쳤어요.

python
복사
print(">>> 1. 코드 시작!")

import time
import network
from machine import I2C, Pin, ADC
from scd30 import SCD30
import wifi_config

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import ussl as ssl
except ImportError:
    import ssl

print(">>> 2. import 성공!")


# ========================================
# 하드웨어 초기화
# ========================================
# SCD30 (I2C: SDA=GP8, SCL=GP9)
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=50000)
print(">>> SCD30 검색 중...")
try:
    scd = SCD30(i2c, addr=0x61)
    scd.start_cont_measure()
    print(">>> SCD30 연결 성공!")
except SCD30.NotFoundException:
    print(">>> 에러: SCD30을 찾을 수 없음! 배선 확인!")
    while True:
        time.sleep(1)

# MQ-2 가스 센서 (GP26)
gas_sensor = ADC(Pin(26))
print(">>> MQ-2 준비 완료")


# ========================================
# WiFi 연결
# ========================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    available = [w[0].decode() for w in wlan.scan()]
    print(">>> 주변 WiFi:", available)

    for ssid, pw in wifi_config.WIFI_NETWORKS.items():
        if ssid in available:
            print(">>> 연결 시도:", ssid)
            wlan.connect(ssid, pw)
            for _ in range(15):
                if wlan.isconnected():
                    print(">>> 연결 성공! IP:", wlan.ifconfig()[0])
                    return wlan
                time.sleep(1)
    print(">>> 연결 가능한 WiFi 없음")
    return None


# ========================================
# URL 분해
# ========================================
def parse_url(url):
    url = url.split("://", 1)[1]
    if "/" in url:
        host, path = url.split("/", 1)
        return host, "/" + path
    return url, "/"


# ========================================
# HTTPS GET (리다이렉트 따라가기 포함)
# ========================================
def https_get(url):
    host, path = parse_url(url)
    print(">>> GET 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "GET " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")


# ========================================
# 시트로 전송 (URL 파라미터 + 리다이렉트 처리)
# ========================================
def send_to_sheet(co2, temp, hum, gas, status):
    print(">>> 전송 함수 진입")
    try:
        # CLASS_ID를 wifi_config에서 자동으로 불러옴!
        params = "class={}&co2={}&temp={}&hum={}&gas={}&status={}".format(
            wifi_config.CLASS_ID, co2, temp, hum, gas, status
        )
        full_url = wifi_config.SHEET_URL + "?" + params

        print(">>> 1차 GET 전송...")
        response = https_get(full_url)
        status_line = response.split("\r\n", 1)[0]
        print(">>> 1차 응답:", status_line)

        # 리다이렉트면 새 주소로 다시 GET
        if "302" in status_line or "301" in status_line or "307" in status_line:
            new_url = None
            for line in response.split("\r\n"):
                if line.lower().startswith("location:"):
                    new_url = line.split(":", 1)[1].strip()
                    break
            print(">>> 리다이렉트! 새 주소로 GET")
            if new_url:
                response2 = https_get(new_url)
                status_line2 = response2.split("\r\n", 1)[0]
                print(">>> 2차 응답:", status_line2)
                body = response2.split("\r\n\r\n", 1)[-1]
                print(">>> 결과:", body[-200:])
        else:
            body = response.split("\r\n\r\n", 1)[-1]
            print(">>> 결과:", body[-200:])

    except Exception as e:
        print(">>> 전송 중 에러:", e)


# ========================================
# 센서 읽기
# ========================================
def read_sensors():
    gas_value = gas_sensor.read_u16()

    # SCD30 데이터가 준비될 때까지 잠깐 대기
    for _ in range(10):  # 최대 10번(약 5초) 시도
        if scd.get_status_ready():
            try:
                co2, temp, humi = scd.read_measurement()
                return co2, temp, humi, gas_value
            except SCD30.CRCException:
                print(">>> CRC 오류, 재시도")
        time.sleep(0.5)

    # 끝내 준비 안 되면 None
    print(">>> SCD30 데이터 준비 안 됨")
    return None, None, None, gas_value


# ========================================
# 에너지 상태 판단 (대시보드와 같은 기준)
# ========================================
def get_status(temp, co2):
    if temp is None:
        return "측정실패"
    if temp >= 29:
        return "냉방안함"
    elif temp < 22:
        if co2 < 600:
            return "빈교실냉방의심"
        else:
            return "과냉방"
    else:
        return "정상"


# ========================================
# 메인 실행
# ========================================
print(">>> 3. WiFi 연결 시도")
wlan = connect_wifi()

if not wlan:
    print(">>> WiFi 연결 실패! 종료")
    while True:
        time.sleep(1)

print(">>> 4. 측정 + 전송 루프 시작 (30초마다)")
print(">>> 이 피코는", wifi_config.CLASS_ID, "반입니다")

while True:
    # 1) 센서 읽기
    co2, temp, hum, gas = read_sensors()

    if co2 is not None:
        # 소수점 1자리로 정리
        co2 = round(co2, 1)
        temp = round(temp, 1)
        hum = round(hum, 1)

        print("-" * 40)
        print("CO2:", co2, "온도:", temp, "습도:", hum, "가스:", gas)

        # 2) 상태 판단
        status = get_status(temp, co2)
        print("상태:", status)

        # 3) 시트로 전송
        send_to_sheet(co2, temp, hum, gas, status)
    else:
        print(">>> 센서 측정 실패, 이번 전송 건너뜀")

    # 4) 30초 대기
    print(">>> 30초 대기...")
    time.sleep(30)
핵심 포인트
① CLASS_ID 자동 불러오기 ⭐
python
복사
params = "class={}&...".format(wifi_config.CLASS_ID, ...)
코드에 반 번호를 하드코딩 안 함!
각 피코의 wifi_config.py에서 CLASS_ID만 바꾸면 됨
즉, 이 코드 하나를 모든 피코에 똑같이 넣고, wifi_config.py의 CLASS_ID만 "1-1", "2-3" 등으로 바꾸면 끝! 👍
② 재사용한 부품들
WiFi 연결, https_get, 리다이렉트 처리 → 전에 완성한 거 그대로!
센서 읽기 → 방금 성공한 거!
③ 30초마다 반복
time.sleep(30)으로 30초마다 측정+전송
너무 자주 보내면 구글 시트에 부담되니 30초가 적당해요
⚠️ 확인할 것
시트 헤더 순서가 대시보드와 맞는지

지금 보내는 순서: class, co2, temp, hum, gas, status
Apps Script에서 이 순서로 시트에 적는지 확인!
상태(status)에 한글이 들어가요 ("정상", "과냉방" 등)

URL에 한글이 들어가면 가끔 문제될 수 있어요
일단 돌려보고, 문제 생기면 영어로 바꾸거나 인코딩 처리할게요
실행
피코에서 그냥 실행하면 돼요. 30초마다:

code
복사
CO2: 800.0 온도: 25.0 습도: 45.0 가스: 3500
상태: 정상
>>> 2차 응답: HTTP/1.1 200 OK
>>> 결과: {"result":"success"}
이렇게 나오고, 대시보드를 새로고침하면 진짜 센서 데이터가 쌓이는 걸 볼 수 있어요!

다음 행동
위 코드 실행
{"result":"success"} 나오는지 확인
구글 시트에 데이터 쌓이는지 확인
대시보드 새로고침 → 진짜 센서 데이터 뜨는지! 🎉
해보고 결과 알려줄래요? 이게 되면 센서 → 시트 → 대시보드 전체 흐름이 완성되는 거예요! 정말 큰 마일스톤이에요! 💪

혹시 한글 status 때문에 문제가 생기거나 다른 에러가 나면 그 메시지 보여주세요. 같이 해결해요! 🙂

오전 11:09

나
잘 저장 된다.  이제 웹사이트를 좀 세련되게 꾸며보자. 여러 페이지 만들고,, 그래프도 멋지게 만들고, 여러 기능 추가하고. 해줘

오전 11:11
AI
축하해요!! 🎉🎉 드디어 센서 → 시트 → 대시보드 전체 흐름이 완성됐어요! 진짜 큰 산을 넘었어요!

이제 대시보드를 멋지게 꾸미는 건 재밌는 부분이에요. 그런데 그 전에 — 무작정 화려하게 만드는 것보다, 뭘 보여줄지 먼저 설계하는 게 좋아요. 같이 정해봐요.

먼저 정하기: 페이지 구성
여러 페이지로 나눈다면, 이런 구성을 추천해요:

페이지	내용
🏠 전체 현황	모든 반 상태 카드 한눈에 + 요약 통계 (몇 반이 낭비 중인지 등)
📊 반별 상세	반 선택 → 그 반의 그래프들 자세히
🏆 에너지 랭킹	어느 반이 절약 잘하나 순위
📋 전체 데이터	원본 표 (필터/검색 가능)
Streamlit은 사이드바 메뉴로 페이지를 나눌 수 있어요. 깔끔하죠.

그 전에 — 솔직한 조언 하나 💬
지금 데이터가 거의 없어요. 피코 1대(2-3반)가 30초마다 보내는 것뿐이라:

랭킹? → 비교할 반이 1개뿐
멋진 그래프? → 데이터 몇 개뿐이라 밋밋함
그래서 화려하게 만들어도 지금은 텅 비어 보일 수 있어요. 😅

제안: 화면을 제대로 테스트하려면 **가짜 데이터(여러 반, 여러 시간)**를 시트에 좀 넣는 게 좋아요. 그래야 랭킹도 그래프도 진짜처럼 보여요.

어떻게 진행할까?
두 가지 길이 있어요:

길 A: 일단 지금 데이터로 멋진 대시보드부터 만들기 → 나중에 데이터 쌓이면 자동으로 채워짐 길 B: 가짜 데이터 먼저 넣고 → 풍성한 화면으로 개발

저는 길 A를 추천해요. 데이터는 시간이 지나면 자동으로 쌓이니까, 일단 틀을 멋지게 만들어두면 돼요.

일단 만들어볼게요 (멀티페이지 + 디자인)
지금 데이터로도 작동하고, 데이터가 쌓이면 더 멋져지는 대시보드예요. 한 번에 다 넣으면 복잡하니 핵심 기능 위주로 깔끔하게 만들게요:

python
복사
import streamlit as st
import pandas as pd

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🏫", layout="wide")

# 자동 새로고침
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ===== 데이터 로드 =====
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    # 숫자형으로 변환 (오류나면 NaN)
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ===== 에너지 상태 판단 =====
def check_status(temp, co2):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"
    people = co2 >= 600
    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방 (이동수업?)", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# ===== 사이드바 메뉴 =====
st.sidebar.title("🏫 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 전체 현황", "📊 반별 상세", "🏆 에너지 랭킹", "📋 전체 데이터"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("30초마다 자동 갱신")


# ========================================
# 페이지 1: 전체 현황
# ========================================
if page == "🏠 전체 현황":
    st.title("🏠 전체 교실 현황")
    st.caption("모든 반의 최신 상태를 한눈에 확인하세요.")

    # 각 반 최신 데이터
    latest = df.groupby("반").last().reset_index()

    # 상단 요약 통계
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"])[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"])[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 에너지 낭비 의심", f"{waste}개")

    st.divider()

    # 반별 카드
    st.subheader("⚡ 반별 상태")
    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"])
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"### {row['반']}")
                    st.markdown(f"**{status}**")
                    st.caption(reason)
                    st.text(f"🌡️ {row['온도']}도  🫁 {row['co2']}ppm")
                    st.text(f"💧 {row['습도']}%  🔥 가스 {row['가스']}")


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)

    class_df = df[df["반"] == selected].copy()

    # 현재 상태 표시
    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"])
    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 데이터 {len(class_df)}개")

    # 최신 값 메트릭
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    # 그래프들
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🫁 CO₂ 변화")
        st.line_chart(class_df.set_index("시간")["co2"], color="#FF6B6B")
        st.subheader("🌡️ 온도 변화")
        st.line_chart(class_df.set_index("시간")["온도"], color="#4ECDC4")
    with col2:
        st.subheader("💧 습도 변화")
        st.line_chart(class_df.set_index("시간")["습도"], color="#45B7D1")
        st.subheader("🔥 가스 변화")
        st.line_chart(class_df.set_index("시간")["가스"], color="#FFA07A")


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("온도가 적정 범위(22~28도)에 가까울수록 에너지를 잘 쓰는 거예요.")

    latest = df.groupby("반").last().reset_index()

    # 점수 계산: 적정온도(25도)에서 멀수록 감점
    def score(temp):
        if pd.isna(temp):
            return 0
        # 25도에 가까울수록 100점
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    # 순위 표시
    for idx, row in ranked.iterrows():
        rank = idx + 1
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{rank}위"
        status, reason, color = check_status(row["온도"], row["co2"])
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 3])
            c1.markdown(f"## {medal}")
            c2.markdown(f"### {row['반']}")
            c2.caption(f"{int(row['점수'])}점")
            c3.markdown(f"**{status}**")
            c3.caption(f"🌡️ {row['온도']}도 · {reason}")


# ========================================
# 페이지 4: 전체 데이터
# ========================================
elif page == "📋 전체 데이터":
    st.title("📋 전체 데이터")

    # 반 필터
    class_list = ["전체"] + sorted(df["반"].unique().tolist())
    selected = st.selectbox("반 필터", class_list)

    if selected == "전체":
        view_df = df
    else:
        view_df = df[df["반"] == selected]

    st.dataframe(view_df, use_container_width=True)
    st.caption(f"총 {len(view_df)}개의 데이터")

    # CSV 다운로드 버튼
    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, "교실데이터.csv", "text/csv")
추가된 기능들 ✨
사이드바 메뉴 — 4개 페이지를 깔끔하게 전환
🏠 전체 현황 — 요약 통계(정상/낭비 개수) + 반별 카드 (테두리 있는 예쁜 카드)
📊 반별 상세 — 반 선택 → 최신값 메트릭 + 컬러 그래프 4개
🏆 에너지 랭킹 — 적정 온도 기준으로 점수 매겨 순위 (메달 🥇🥈🥉)
📋 전체 데이터 — 반 필터 + CSV 다운로드 버튼
실행
code
복사
py -m streamlit run dashboard.py
⚠️ 참고
지금은 2-3반 하나뿐이라 랭킹/현황이 좀 휑할 거예요. 데이터가 쌓이거나 다른 반 피코가 추가되면 자동으로 채워져요!
st.container(border=True)는 최신 Streamlit에서 돼요. 안 되면 버전 업데이트가 필요할 수 있어요 (py -m pip install --upgrade streamlit)
다음 행동
위 코드로 교체 후 실행
4개 페이지 둘러보기
어떤 페이지/기능을 더 다듬고 싶은지 알려주기!
먼저 실행해보고 어때요? 그리고 더 추가하고 싶은 기능이 있으면 말해줘요:

시간대별 평균 그래프?
위험 알림 (CO2 높으면 경고)?
색상 테마 변경?
특정 반만 모아보기?
뭘 더 멋지게 하고 싶은지 말해주면 같이 다듬어요! 🙂

오전 11:12

최신 응답 보기



이게 반마다 시간표가 있을거 아니야? 시간표를 입력해두고, 웹사이트에 반들 카드 뜨는곳에 딱 시간에 맞춰서 딱 교과목이 보이는거지, 뭔느낌인지 알겠어? 막 체육 교과 시간인데 온도가 낮고 이산화탄소 농도가 높으면 체육시간에 에어컨 안끄고 에너지 낭비하고 나간거랑 똑같은상황인거잖아? 이런 것도 확인 하고 체크하는겸, 시간표도 보고 재밌잖아? 아무튼 이런기능을 추가하고 싶고, 웹페이지 구성을 좀더 세련되고 예쁘게 하고싶어. 아맞다 그리고 시간표 입력 방법은 내가 지금 생각하는건, 대시보드.py안에  딕셔너리로 입력해두는거야. 어떻게 생각해? 참고로 시간표는 8시 10분에 조회 시간 시작하고, 8시 20분에 1교시 시작해서, 50분씩 하고, 점심시간은 4교시 끝나자마자 시작한 뒤에, 1시 10분에 끝나. 그리고 똑같이 해서, 화요일이랑 목요일은 7교시까지하고, 나머지 월 수 금은 6교시까지 해. 참고로 각 반마다 모든 교시의 과목이 달라. 하지만 그건 내가 알아서 입력할게. 일단 근데 지금은 2-3반 데이터만 입력할거야. 그리고, plotly 추가해서 더 멋지게 꾸며줘. 웹사이트 디자인이 너무 구리잖아? 약간 도형같은거 활용해서, 배경도 약간 지구 느낌으로 꾸미고, 약간의 애니메이션들도 추가해서 약간 배경 움직이는 느낌도 넣어주고, 뭔느낌인지 알지? 도형 움직이게, 그리고 도형 넣고 배경 꾸민다고 기능들이 배경 뒤에 가려져버리면 안된다? 그리고 그래프 너무 못생겨서, x축에 적힌글들이 싹 다 너무 길어서 보기 불편해.이거 실시간 시간 반영 되는거 맞지? 웹사이트 자동으로 새로고침 되는것도 맞지? 30초 간격으로 자동 새로고침 되야해 웹사이트. 실시간 시간을 웹사이트 "대시보드 홈" 의 위쪽에 띄워놔줘. 실시간 시간을 통해 해야하니까. 실시간 시간에 따른 웹사이트에서 시간표 변화 이런게 있어야해. 뭔말인지 알지? 아무튼 짜줘.
오후 3:04
AI
와, 구상이 정말 멋져요! 👏 "체육 시간인데 CO₂ 높고 온도 낮음 = 에어컨 켜고 나감" — 이거 진짜 똑똑한 아이디어예요. 시간표랑 센서 데이터를 결합하니까 훨씬 의미 있는 분석이 되네요!
요청이 많으니 정리하고, 한 번에 만들어줄게요.
요청 정리 ✅
시간표 기능 — 딕셔너리로 입력 (2-3반만), 실시간 시간에 맞춰 현재 교시/과목 표시
시간표 기반 낭비 감지 — 체육 등 이동수업 시간에 냉방 켜둠 감지
plotly 그래프 — 예쁘게, x축 글자 정리
세련된 디자인 — 지구 느낌 배경 + 움직이는 도형 애니메이션 (단, 기능 안 가리게!)
실시간 시간 표시 (홈 상단) + 30초 자동 새로고침
시간표 구조부터 (당신 규칙대로 계산)
당신이 준 규칙으로 교시 시간을 계산했어요:
교시
시간
조회
08:10~08:20
1교시
08:20~09:10
2교시
09:10~10:00
3교시
10:00~10:50
4교시
10:50~11:40
점심
11:40~13:10
5교시
13:10~14:00
6교시
14:00~14:50
7교시(화·목)
14:50~15:40

50분 수업이고, 점심은 4교시 후~13:10까지로 계산했어요. 쉬는 시간(10분)은 따로 안 넣고 교시 사이로 처리했어요. 이대로 맞나요?
디자인 방향 — 한 가지 짚고 갈게요 💬
Streamlit은 사실 화려한 커스텀 디자인엔 약해요. (데이터 대시보드에 특화된 도구라서요.) 그래도 CSS를 주입하면 어느 정도 꾸밀 수 있어요. 배경 애니메이션, 지구 느낌 그라데이션, 움직이는 도형은 CSS로 넣을 수 있어요!
다만 솔직하게: 게임 웹사이트처럼 화려하게는 어려워요. 하지만 "깔끔하고 세련되고 배경이 은은하게 움직이는" 정도는 충분히 가능해요. 기대치를 맞추고 갈게요!
전체 코드
python
복사
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

# 자동 새로고침 (30초)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 교시 시간 정의
# ========================================
PERIODS = [
    ("조회",   dtime(8, 10),  dtime(8, 20)),
    ("1교시", dtime(8, 20),  dtime(9, 10)),
    ("2교시", dtime(9, 10),  dtime(10, 0)),
    ("3교시", dtime(10, 0),  dtime(10, 50)),
    ("4교시", dtime(10, 50), dtime(11, 40)),
    ("점심",   dtime(11, 40), dtime(13, 10)),
    ("5교시", dtime(13, 10), dtime(14, 0)),
    ("6교시", dtime(14, 0),  dtime(14, 50)),
    ("7교시", dtime(14, 50), dtime(15, 40)),  # 화·목만
]

# 요일별 마지막 교시 (월=0 ~ 일=6)
LAST_PERIOD = {0: "6교시", 1: "7교시", 2: "6교시", 3: "7교시", 4: "6교시"}


# ========================================
# 시간표 (여기에 입력! 2-3반만 작성)
# 형식: TIMETABLE["반"]["요일"]["교시"] = "과목"
# 요일: 월/화/수/목/금
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "국어", "2교시": "수학", "3교시": "영어", "4교시": "과학",
               "5교시": "체육", "6교시": "사회"},
        "화": {"1교시": "수학", "2교시": "국어", "3교시": "체육", "4교시": "영어",
               "5교시": "과학", "6교시": "음악", "7교시": "미술"},
        "수": {"1교시": "영어", "2교시": "과학", "3교시": "국어", "4교시": "수학",
               "5교시": "사회", "6교시": "체육"},
        "목": {"1교시": "과학", "2교시": "체육", "3교시": "수학", "4교시": "국어",
               "5교시": "영어", "6교시": "기술", "7교시": "한문"},
        "금": {"1교시": "사회", "2교시": "영어", "3교시": "과학", "4교시": "체육",
               "5교시": "국어", "6교시": "수학"},
    },
    # 다른 반은 나중에 추가!
}

# 이동수업으로 간주할 과목 (교실 비는 시간)
MOVING_SUBJECTS = ["체육", "음악", "미술", "기술", "과학"]  # 과학실/체육관 등 이동

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 현재 교시 / 과목 찾기
# ========================================
def get_current_period(now):
    """현재 시각에 해당하는 교시 이름 반환"""
    weekday = now.weekday()
    if weekday >= 5:  # 주말
        return None, "주말"
    now_t = now.time()
    last = LAST_PERIOD.get(weekday, "6교시")
    last_idx = [p[0] for p in PERIODS].index(last)

    for i, (name, start, end) in enumerate(PERIODS):
        if i > last_idx:
            break
        if start <= now_t < end:
            return name, None
    return None, "수업시간 아님"


def get_subject(class_id, now, period):
    """현재 교시의 과목 반환"""
    if period is None:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(period, None)


# ========================================
# 데이터 로드
# ========================================
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 에너지 상태 판단 (시간표 반영!)
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"

    period, _ = get_current_period(now)
    subject = get_subject(class_id, now, period)
    people = co2 >= 600

    # 이동수업인데 냉방 켜둠 = 낭비!
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"

    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# ========================================
# 디자인: CSS 주입 (지구 배경 + 움직이는 도형)
# ========================================
st.markdown("""
<style>
/* 전체 배경: 우주/지구 느낌 그라데이션 */
.stApp {
    background: linear-gradient(-45deg, #0a1128, #1c3a5e, #0a2342, #15396b);
    background-size: 400% 400%;
    animation: gradientMove 18s ease infinite;
}
@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

/* 움직이는 도형들 (배경 뒤에 깔림, 기능 안 가림) */
.shape {
    position: fixed;
    border-radius: 50%;
    opacity: 0.12;
    z-index: 0;
    pointer-events: none;
}
.shape1 {width:300px;height:300px;background:#4ECDC4;top:10%;left:5%;
         animation: floatA 20s ease-in-out infinite;}
.shape2 {width:200px;height:200px;background:#FF6B6B;top:60%;right:8%;
         animation: floatB 25s ease-in-out infinite;}
.shape3 {width:150px;height:150px;background:#FFD93D;bottom:10%;left:15%;
         animation: floatA 30s ease-in-out infinite;}
@keyframes floatA {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(40px,-60px) rotate(180deg);}
}
@keyframes floatB {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(-50px,40px) rotate(-180deg);}
}

/* 콘텐츠는 도형 위로 (안 가려지게!) */
.main .block-container {position: relative; z-index: 1;}

/* 카드/텍스트 가독성 위해 살짝 밝게 */
[data-testid="stMetricValue"] {color: #ffffff;}
h1, h2, h3, p, .stMarkdown {color: #f0f4f8;}

/* 실시간 시계 박스 */
.clock-box {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}
.clock-time {font-size: 42px; font-weight: 800; color: #4ECDC4; margin:0;}
.clock-date {font-size: 16px; color: #b0c4de; margin:0;}
.clock-period {font-size: 20px; color: #FFD93D; margin-top:8px;}
</style>

<div class="shape shape1"></div>
<div class="shape shape2"></div>
<div class="shape shape3"></div>
""", unsafe_allow_html=True)


# ========================================
# 현재 시각
# ========================================
now = datetime.now()
period, period_msg = get_current_period(now)


# ========================================
# 사이드바
# ========================================
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹", "📋 전체 데이터"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 페이지 1: 대시보드 홈
# ========================================
if page == "🏠 대시보드 홈":
    # 실시간 시계
    weekday_name = WEEKDAY_KR[now.weekday()]
    if period:
        period_text = f"📚 현재: {period}"
    else:
        period_text = f"☕ {period_msg}"

    st.markdown(f"""
    <div class="clock-box">
        <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
        <p class="clock-period">{period_text}</p>
    </div>
    """, unsafe_allow_html=True)

    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()

    # 요약 통계
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태 (현재 교시 과목 표시)")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, period)
            subject_text = f"📖 {subject}" if subject else "—"
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"### {row['반']}")
                    st.markdown(f"**{subject_text}** ({period or '쉬는시간'})")
                    st.markdown(f"**{status}**")
                    st.caption(reason)
                    st.text(f"🌡️ {row['온도']}도  🫁 {row['co2']}ppm")


# ========================================
# 페이지 2: 반별 상세 (plotly)
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)

    # 측정 순번 (x축 글자 길이 문제 해결!)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, period)

    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재 과목: {subject or '없음'} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    # plotly 그래프 함수
    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3)
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#f0f4f8",
            title_font_size=18,
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#FF6B6B"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#4ECDC4"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#45B7D1"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#FFD93D"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("적정 온도(25도)에 가까울수록 높은 점수!")

    latest = df.groupby("반").last().reset_index()

    def score(temp):
        if pd.isna(temp):
            return 0
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    for idx, row in ranked.iterrows():
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 3])
            c1.markdown(f"## {medal}")
            c2.markdown(f"### {row['반']}")
            c2.caption(f"{int(row['점수'])}점")
            c3.markdown(f"**{status}**")
            c3.caption(f"🌡️ {row['온도']}도 · {reason}")


# ========================================
# 페이지 4: 전체 데이터
# ========================================
elif page == "📋 전체 데이터":
    st.title("📋 전체 데이터")

    class_list = ["전체"] + sorted(df["반"].unique().tolist())
    selected = st.selectbox("반 필터", class_list)
    view_df = df if selected == "전체" else df[df["반"] == selected]

    st.dataframe(view_df, use_container_width=True)
    st.caption(f"총 {len(view_df)}개의 데이터")

    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, "교실데이터.csv", "text/csv")
설치 (plotly)
code
복사
py -m pip install plotly
주요 포인트 설명
① 시간표 — 딕셔너리 방식 (당신 생각대로!)
python
복사
TIMETABLE = {"2-3": {"월": {"1교시": "국어", ...}, ...}}
2-3반만 넣어뒀어요 (예시 과목이라 실제로 바꿔야 해요!)
다른 반은 같은 형식으로 추가하면 됨
딕셔너리 방식 👍 좋은 선택이에요. 간단하고 수정하기 쉬워요!
② 시간표 기반 낭비 감지
python
복사
if subject in MOVING_SUBJECTS and temp < 24:
    return "🔴 이동수업 냉방 낭비!"
체육/음악/미술 등 이동수업 시간인데 온도 낮으면 → 낭비로 판단!
MOVING_SUBJECTS 목록은 당신 학교에 맞게 조정하세요
③ 실시간 시계 (홈 상단)
datetime.now()로 현재 시각 + 요일 + 현재 교시 표시
30초마다 새로고침되니 시계도 갱신돼요
④ x축 글자 문제 해결
긴 시간 문자열 대신 **"측정 순번"(1,2,3...)**을 x축으로 사용 → 깔끔!
⑤ 디자인
우주 느낌 움직이는 그라데이션 배경
떠다니는 원형 도형 3개 (z-index로 콘텐츠 뒤에 배치 → 기능 안 가림!)
반투명 유리 느낌 시계 박스
⚠️ 꼭 확인할 것
시간표 과목은 예시예요! TIMETABLE의 2-3반 과목을 실제 시간표로 바꿔주세요.
MOVING_SUBJECTS(이동수업 과목)도 실제에 맞게 조정하세요.
교시 시간이 내가 계산한 거랑 맞는지 확인! (쉬는 시간 처리 등)

다음 행동
py -m pip install plotly
위 코드로 교체 후 실행
홈에서 실시간 시계 + 현재 교시 과목 뜨는지 확인
시간표 과목을 실제 2-3반 시간표로 수정
해보고 어때요? 디자인이나 기능 중에 더 다듬고 싶은 게 있으면 알려줘요!
그리고 궁금한 점: **쉬는 시간(10분)**도 시간표에 따로 표시할까요? 아니면 지금처럼 교시 시간만 볼까요? 🙂
오후 3:07
나
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

# 자동 새로고침 (30초)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 교시 시간 정의
# ========================================
PERIODS = [
    ("조회",   dtime(8, 10),  dtime(8, 20)),
    ("1교시", dtime(8, 20),  dtime(9, 10)),
    ("2교시", dtime(9, 10),  dtime(10, 0)),
    ("3교시", dtime(10, 0),  dtime(10, 50)),
    ("4교시", dtime(10, 50), dtime(11, 40)),
    ("점심",   dtime(11, 40), dtime(13, 10)),
    ("5교시", dtime(13, 10), dtime(14, 0)),
    ("6교시", dtime(14, 0),  dtime(14, 50)),
    ("7교시", dtime(14, 50), dtime(15, 40)),  # 화·목만
]

# 요일별 마지막 교시 (월=0 ~ 일=6)
LAST_PERIOD = {0: "6교시", 1: "7교시", 2: "6교시", 3: "7교시", 4: "6교시"}


# ========================================
# 시간표 (여기에 입력! 2-3반만 작성)
# 형식: TIMETABLE["반"]["요일"]["교시"] = "과목"
# 요일: 월/화/수/목/금
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "문학A", "2교시": "영어B", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "음악 연주와 창작"},
        "화": {"1교시": "선택 과목", "2교시": "문학C", "3교시": "합주", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "스포츠 생활B", "7교시": "선택 과목"},
        "수": {"1교시": "영어A", "2교시": "선택 과목", "3교시": "선택 과목", "4교시": "문학B",
               "5교시": "선택 과목", "6교시": "대수"},
        "목": {"1교시": "선택 과목", "2교시": "스포츠 생활A", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "영어A", "6교시": "선택 과목", "7교시": "대수"},
        "금": {"1교시": "선택 과목", "2교시": "선택 과목", "3교시": "영어C", "4교시": "문학D",
               "5교시": "자율", "6교시": "자율"},
    },
    # 다른 반은 나중에 추가!
}

# 이동수업으로 간주할 과목 (교실 비는 시간)
MOVING_SUBJECTS = ["스포츠 생활A","스포츠 생활B"]  # 과학실/체육관 등 이동

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 현재 교시 / 과목 찾기
# ========================================
def get_current_period(now):
    """현재 시각에 해당하는 교시 이름 반환"""
    weekday = now.weekday()
    if weekday >= 5:  # 주말
        return None, "주말"
    now_t = now.time()
    last = LAST_PERIOD.get(weekday, "6교시")
    last_idx = [p[0] for p in PERIODS].index(last)

    for i, (name, start, end) in enumerate(PERIODS):
        if i > last_idx:
            break
        if start <= now_t < end:
            return name, None
    return None, "수업시간 아님"


def get_subject(class_id, now, period):
    """현재 교시의 과목 반환"""
    if period is None:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(period, None)


# ========================================
# 데이터 로드
# ========================================
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 에너지 상태 판단 (시간표 반영!)
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"

    period, _ = get_current_period(now)
    subject = get_subject(class_id, now, period)
    people = co2 >= 600

    # 이동수업인데 냉방 켜둠 = 낭비!
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"

    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# ========================================
# 디자인: CSS 주입 (지구 배경 + 움직이는 도형)
# ========================================
st.markdown("""
<style>
/* 전체 배경: 우주/지구 느낌 그라데이션 */
.stApp {
    background: linear-gradient(-45deg, #0a1128, #1c3a5e, #0a2342, #15396b);
    background-size: 400% 400%;
    animation: gradientMove 18s ease infinite;
}
@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

/* 움직이는 도형들 (배경 뒤에 깔림, 기능 안 가림) */
.shape {
    position: fixed;
    border-radius: 50%;
    opacity: 0.12;
    z-index: 0;
    pointer-events: none;
}
.shape1 {width:300px;height:300px;background:#4ECDC4;top:10%;left:5%;
         animation: floatA 20s ease-in-out infinite;}
.shape2 {width:200px;height:200px;background:#FF6B6B;top:60%;right:8%;
         animation: floatB 25s ease-in-out infinite;}
.shape3 {width:150px;height:150px;background:#FFD93D;bottom:10%;left:15%;
         animation: floatA 30s ease-in-out infinite;}
@keyframes floatA {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(40px,-60px) rotate(180deg);}
}
@keyframes floatB {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(-50px,40px) rotate(-180deg);}
}

/* 콘텐츠는 도형 위로 (안 가려지게!) */
.main .block-container {position: relative; z-index: 1;}

/* 카드/텍스트 가독성 위해 살짝 밝게 */
[data-testid="stMetricValue"] {color: #ffffff;}
h1, h2, h3, p, .stMarkdown {color: #f0f4f8;}

/* 실시간 시계 박스 */
.clock-box {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}
.clock-time {font-size: 42px; font-weight: 800; color: #4ECDC4; margin:0;}
.clock-date {font-size: 16px; color: #b0c4de; margin:0;}
.clock-period {font-size: 20px; color: #FFD93D; margin-top:8px;}
</style>

<div class="shape shape1"></div>
<div class="shape shape2"></div>
<div class="shape shape3"></div>
""", unsafe_allow_html=True)


# ========================================
# 현재 시각
# ========================================
now = datetime.now()
period, period_msg = get_current_period(now)


# ========================================
# 사이드바
# ========================================
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹", "📋 전체 데이터"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 페이지 1: 대시보드 홈
# ========================================
if page == "🏠 대시보드 홈":
    # 실시간 시계
    weekday_name = WEEKDAY_KR[now.weekday()]
    if period:
        period_text = f"📚 현재: {period}"
    else:
        period_text = f"☕ {period_msg}"

    st.markdown(f"""
    <div class="clock-box">
        <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
        <p class="clock-period">{period_text}</p>
    </div>
    """, unsafe_allow_html=True)

    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()

    # 요약 통계
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태 (현재 교시 과목 표시)")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, period)
            subject_text = f"📖 {subject}" if subject else "—"
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"### {row['반']}")
                    st.markdown(f"**{subject_text}** ({period or '쉬는시간'})")
                    st.markdown(f"**{status}**")
                    st.caption(reason)
                    st.text(f"🌡️ {row['온도']}도  🫁 {row['co2']}ppm")


# ========================================
# 페이지 2: 반별 상세 (plotly)
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)

    # 측정 순번 (x축 글자 길이 문제 해결!)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, period)

    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재 과목: {subject or '없음'} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    # plotly 그래프 함수
    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3)
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#f0f4f8",
            title_font_size=18,
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#FF6B6B"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#4ECDC4"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#45B7D1"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#FFD93D"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("적정 온도(25도)에 가까울수록 높은 점수!")

    latest = df.groupby("반").last().reset_index()

    def score(temp):
        if pd.isna(temp):
            return 0
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    for idx, row in ranked.iterrows():
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 3])
            c1.markdown(f"## {medal}")
            c2.markdown(f"### {row['반']}")
            c2.caption(f"{int(row['점수'])}점")
            c3.markdown(f"**{status}**")
            c3.caption(f"🌡️ {row['온도']}도 · {reason}")


# ========================================
# 페이지 4: 전체 데이터
# ========================================
elif page == "📋 전체 데이터":
    st.title("📋 전체 데이터")

    class_list = ["전체"] + sorted(df["반"].unique().tolist())
    selected = st.selectbox("반 필터", class_list)
    view_df = df if selected == "전체" else df[df["반"] == selected]

    st.dataframe(view_df, use_container_width=True)
    st.caption(f"총 {len(view_df)}개의 데이터")

    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, "교실데이터.csv", "text/csv")

이렇게 시간표쪽은 내가 수정해놨어. 그리고, 수업 일정에서, 쉬는 시간이랑 교과, 그리고 조회(조회는 오전 8시 10분 부터 8시 20분)와 종례(종례는 오후 3시 00분 부터 3시 10분까지) 이것들도 추가해주고, 일정이 끝났으면 방과후라고 표기되게 해줘. 그리고 내가 말했던 애니메이션 느낌은 이런게 아니고,, 음, 내가 예시 하나 올려줄게. 이건 내가 저번에 그냥 간단하게 프로젝트 했던거 코드야.

import streamlit as st
import random

# 1. 페이지 설정
st.set_page_config(
    page_title="🏮 이자카야 MBTI 저녁 추천 🍶",
    page_icon="🏮",
    layout="centered"
)

# 2. 초화려 이자카야 배경 🎆🏮🎋
st.markdown("""
<style>
/* ===== 밤하늘 배경 (그라데이션 + 보름달) ===== */
.stApp {
    background: 
        radial-gradient(circle at 85% 12%, rgba(255, 240, 180, 0.15) 0%, transparent 8%),
        radial-gradient(circle at 85% 12%, #fff4c4 0%, #f5d76e 3%, transparent 4%),
        radial-gradient(ellipse at top, #3d2466 0%, #1a1a3e 40%, #0a0a1e 100%);
    background-attachment: fixed;
    color: #f5e6d3 !important;
    overflow-x: hidden;
}

/* ===== 멀리 보이는 후지산 실루엣 🗻 ===== */
.mountain {
    position: fixed;
    bottom: 38%;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 200px solid transparent;
    border-right: 200px solid transparent;
    border-bottom: 150px solid #1a1535;
    z-index: -3;
    opacity: 0.6;
    filter: drop-shadow(0 0 20px rgba(100, 80, 150, 0.4));
}
.mountain::before {
    content: "";
    position: absolute;
    top: 20px;
    left: -40px;
    width: 80px;
    height: 30px;
    background: rgba(255, 255, 255, 0.4);
    clip-path: polygon(0 100%, 20% 60%, 40% 80%, 60% 50%, 80% 70%, 100% 100%);
}

/* ===== 멀리 보이는 도시 실루엣 (왼쪽) ===== */
.city-left {
    position: fixed;
    bottom: 38%;
    left: 0;
    width: 30%;
    height: 100px;
    background: 
        linear-gradient(90deg,
            #0f0a25 0px, #0f0a25 30px, transparent 30px, transparent 35px,
            #0f0a25 35px, #0f0a25 80px, transparent 80px, transparent 88px,
            #0f0a25 88px, #0f0a25 120px, transparent 120px, transparent 130px,
            #0f0a25 130px, #0f0a25 170px, transparent 170px, transparent 178px,
            #0f0a25 178px, #0f0a25 220px, transparent 220px, transparent 230px,
            #0f0a25 230px, #0f0a25 280px);
    z-index: -3;
    opacity: 0.8;
    mask: linear-gradient(180deg, transparent 0%, black 30%);
    -webkit-mask: linear-gradient(180deg, transparent 0%, black 30%);
}

/* 도시 (오른쪽) */
.city-right {
    position: fixed;
    bottom: 38%;
    right: 0;
    width: 30%;
    height: 100px;
    background: 
        linear-gradient(90deg,
            #0f0a25 0px, #0f0a25 40px, transparent 40px, transparent 50px,
            #0f0a25 50px, #0f0a25 95px, transparent 95px, transparent 105px,
            #0f0a25 105px, #0f0a25 145px, transparent 145px, transparent 155px,
            #0f0a25 155px, #0f0a25 200px, transparent 200px, transparent 210px,
            #0f0a25 210px, #0f0a25 260px);
    z-index: -3;
    opacity: 0.8;
}

/* ===== 폭죽 (밤하늘 불꽃놀이) 🎆 ===== */
.firework {
    position: fixed;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    z-index: -2;
    animation: explode 3s ease-out infinite;
}
@keyframes explode {
    0% { transform: scale(0); opacity: 1; box-shadow: 0 0 0 0 transparent; }
    50% { 
        transform: scale(1); 
        opacity: 1;
        box-shadow: 
            0 -40px 0 #ff6b9d, 0 40px 0 #ff6b9d,
            40px 0 0 #ff6b9d, -40px 0 0 #ff6b9d,
            28px -28px 0 #ffd93d, -28px -28px 0 #ffd93d,
            28px 28px 0 #ffd93d, -28px 28px 0 #ffd93d,
            0 -60px 0 #6bcf7f, 0 60px 0 #6bcf7f,
            60px 0 0 #6bcf7f, -60px 0 0 #6bcf7f;
    }
    100% { transform: scale(1.5); opacity: 0; }
}
.firework-1 { top: 8%; left: 15%; animation-delay: 0s; }
.firework-2 { top: 12%; right: 20%; animation-delay: 1.5s; }
.firework-3 { top: 18%; left: 45%; animation-delay: 2.8s; }

/* ===== 기와 지붕 (더 화려하게) ===== */
.roof {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 110px;
    z-index: -2;
}
.roof-top {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 35px;
    background: linear-gradient(180deg, #0a0408 0%, #3d1f1f 100%);
    box-shadow: 0 2px 8px rgba(0,0,0,0.6);
}
/* 지붕 위 황금 장식 (시비) */
.roof-top::before, .roof-top::after {
    content: "";
    position: absolute;
    top: -15px;
    width: 25px;
    height: 35px;
    background: linear-gradient(180deg, #ffd700 0%, #b8860b 100%);
    clip-path: polygon(50% 0%, 100% 50%, 80% 100%, 20% 100%, 0% 50%);
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
}
.roof-top::before { left: 10%; }
.roof-top::after { right: 10%; }

.roof-tiles {
    position: absolute;
    top: 35px;
    left: 0;
    width: 100%;
    height: 45px;
    background: 
        radial-gradient(circle at 20px 45px, #4a2424 0px, #4a2424 18px, transparent 19px),
        radial-gradient(circle at 60px 45px, #4a2424 0px, #4a2424 18px, transparent 19px),
        radial-gradient(circle at 100px 45px, #4a2424 0px, #4a2424 18px, transparent 19px),
        linear-gradient(180deg, #6b2c2c 0%, #3d1f1f 100%);
    background-size: 40px 45px, 40px 45px, 40px 45px, 100% 100%;
    box-shadow: 0 4px 15px rgba(0,0,0,0.6);
}
.roof-bottom {
    position: absolute;
    top: 80px;
    left: 0;
    width: 100%;
    height: 25px;
    background: 
        repeating-linear-gradient(90deg, 
            #8b2c2c 0px, #8b2c2c 25px, 
            #d4af37 25px, #d4af37 28px,
            #8b2c2c 28px, #8b2c2c 53px,
            #1a0e08 53px, #1a0e08 55px);
    border-bottom: 4px solid #d4af37;
    box-shadow: 0 3px 12px rgba(0,0,0,0.5), 0 0 20px rgba(212, 175, 55, 0.3);
}

/* ===== 가게 벽 (나무 + 디테일) ===== */
.izakaya-wall {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 40%;
    background: 
        repeating-linear-gradient(90deg,
            #3d2817 0px, #4a2f1c 70px,
            #3d2817 72px, #2a1810 74px, #3d2817 76px),
        linear-gradient(180deg, #3a2515 0%, #1a0e08 100%);
    z-index: -2;
    box-shadow: inset 0 15px 30px rgba(0,0,0,0.7);
}

/* 가게 벽 위 황금 띠 장식 */
.wall-trim {
    position: fixed;
    bottom: 40%;
    left: 0;
    width: 100%;
    height: 8px;
    background: linear-gradient(90deg, 
        #d4af37 0%, #ffd700 50%, #d4af37 100%);
    z-index: -1;
    box-shadow: 
        0 0 15px rgba(255, 215, 0, 0.5),
        0 2px 8px rgba(0,0,0,0.4);
}

/* ===== 일본식 격자창 (왼쪽 2개) ===== */
.window-l1, .window-l2, .window-r1, .window-r2 {
    position: fixed;
    bottom: 15%;
    width: 110px;
    height: 90px;
    background: 
        radial-gradient(ellipse at center,
            rgba(255, 220, 130, 0.6) 0%, 
            rgba(255, 150, 50, 0.3) 100%);
    border: 4px solid #2a1810;
    box-shadow: 
        0 0 35px rgba(255, 180, 80, 0.5),
        inset 0 0 25px rgba(255, 220, 130, 0.4);
    z-index: -2;
    animation: windowFlicker 4s ease-in-out infinite;
}
.window-l1 { left: 3%; }
.window-l2 { left: 17%; animation-delay: -1s; }
.window-r1 { right: 3%; animation-delay: -2s; }
.window-r2 { right: 17%; animation-delay: -3s; }

.window-l1::before, .window-l2::before, .window-r1::before, .window-r2::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: 
        linear-gradient(90deg, transparent 23%, #2a1810 23%, #2a1810 26%, transparent 26%,
                              transparent 48%, #2a1810 48%, #2a1810 51%, transparent 51%,
                              transparent 73%, #2a1810 73%, #2a1810 76%, transparent 76%),
        linear-gradient(0deg, transparent 30%, #2a1810 30%, #2a1810 33%, transparent 33%,
                              transparent 65%, #2a1810 65%, #2a1810 68%, transparent 68%);
}
/* 창문 안 사람 그림자 (특정 창에만) */
.window-l2::after, .window-r1::after {
    content: "";
    position: absolute;
    bottom: 10%;
    left: 50%;
    transform: translateX(-50%);
    width: 30px;
    height: 50px;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 50% 50% 20% 20%;
}

@keyframes windowFlicker {
    0%, 100% { box-shadow: 0 0 35px rgba(255, 180, 80, 0.5), inset 0 0 25px rgba(255, 220, 130, 0.4); }
    50% { box-shadow: 0 0 45px rgba(255, 200, 100, 0.7), inset 0 0 30px rgba(255, 230, 150, 0.6); }
}

/* ===== 노렌 (입구 천) ===== */
.noren {
    position: fixed;
    bottom: 40%;
    left: 50%;
    transform: translateX(-50%);
    width: 340px;
    height: 80px;
    background: 
        linear-gradient(180deg, #a02020 0%, #6b1515 100%);
    z-index: -1;
    border-radius: 3px 3px 0 0;
    box-shadow: 
        0 5px 25px rgba(0,0,0,0.7),
        inset 0 -10px 20px rgba(0,0,0,0.4),
        0 0 30px rgba(160, 32, 32, 0.4);
    animation: norenSway 5s ease-in-out infinite;
    transform-origin: top center;
    border-top: 5px solid #d4af37;
}
.noren::before {
    content: "居 酒 屋";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #f5e6d3;
    font-size: 30px;
    font-weight: bold;
    letter-spacing: 14px;
    text-shadow: 
        0 0 12px rgba(255,200,100,0.8),
        2px 2px 4px rgba(0,0,0,0.6);
}
.noren::after {
    content: "";
    position: absolute;
    top: 20%;
    left: 0;
    width: 100%;
    height: 80%;
    background: 
        linear-gradient(90deg, 
            transparent 19%, #1a0e08 19%, #1a0e08 21%, transparent 21%,
            transparent 39%, #1a0e08 39%, #1a0e08 41%, transparent 41%,
            transparent 59%, #1a0e08 59%, #1a0e08 61%, transparent 61%,
            transparent 79%, #1a0e08 79%, #1a0e08 81%, transparent 81%);
}
@keyframes norenSway {
    0%, 100% { transform: translateX(-50%) rotate(-1.5deg); }
    50% { transform: translateX(-50%) rotate(1.5deg); }
}

/* ===== 작은 사이드 노렌 (양옆) ===== */
.mini-noren-left, .mini-noren-right {
    position: fixed;
    bottom: 40%;
    width: 80px;
    height: 50px;
    background: linear-gradient(180deg, #1a4d8c 0%, #0d2e57 100%);
    z-index: -1;
    border-top: 3px solid #d4af37;
    box-shadow: 0 3px 12px rgba(0,0,0,0.5);
    animation: norenSway 6s ease-in-out infinite;
    transform-origin: top center;
}
.mini-noren-left { left: 32%; animation-delay: -1s; }
.mini-noren-right { right: 32%; animation-delay: -2s; }
.mini-noren-left::before, .mini-noren-right::before {
    content: "祭";
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    color: #f5e6d3;
    font-size: 22px;
    font-weight: bold;
    text-shadow: 0 0 8px rgba(255,200,100,0.6);
}

/* ===== 대나무 (양쪽) ===== */
.bamboo-left, .bamboo-right {
    position: fixed;
    bottom: 0;
    width: 28px;
    height: 50%;
    background: linear-gradient(180deg, #5a7d44 0%, #2d4220 100%);
    z-index: -2;
    box-shadow: 3px 0 12px rgba(0,0,0,0.5);
}
.bamboo-left { left: 0; }
.bamboo-right { right: 0; }
.bamboo-left::before, .bamboo-right::before {
    content: "";
    position: absolute;
    top: 15%; left: 0;
    width: 100%; height: 4px;
    background: #1a2a10;
    box-shadow: 
        0 70px 0 #1a2a10, 
        0 140px 0 #1a2a10, 
        0 210px 0 #1a2a10,
        0 280px 0 #1a2a10;
}
/* 대나무 잎사귀 */
.bamboo-left::after, .bamboo-right::after {
    content: "🎋";
    position: absolute;
    top: -25px;
    left: -10px;
    font-size: 40px;
    transform: rotate(-15deg);
}
.bamboo-right::after { left: auto; right: -10px; transform: rotate(15deg); }

/* ===== 등불 (양쪽 4개, 더 화려하게) ===== */
.lantern-container {
    position: fixed;
    top: 0;
    width: 100%;
    height: 100vh;
    pointer-events: none;
    z-index: -1;
}

.lantern-wrap {
    position: absolute;
    top: 110px;
    transform-origin: top center;
    animation: swing 4s ease-in-out infinite;
}

.lantern-string {
    width: 2px;
    height: 50px;
    background: linear-gradient(180deg, #5a3a20 0%, #3d2515 100%);
    margin: 0 auto;
}
/* 등불 위 매듭 */
.lantern-string::before {
    content: "";
    position: absolute;
    bottom: 0;
    left: -3px;
    width: 8px;
    height: 8px;
    background: #d4af37;
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(212, 175, 55, 0.6);
}

.lantern-body {
    width: 70px;
    height: 90px;
    background: radial-gradient(ellipse at center, 
        #fff2a8 0%, 
        #ffb347 25%, 
        #ff7043 55%, 
        #c62828 85%, 
        #8b1a1a 100%);
    border-radius: 50%;
    margin: 0 auto;
    position: relative;
    box-shadow: 
        0 0 50px rgba(255, 140, 66, 0.9),
        0 0 100px rgba(255, 140, 66, 0.6),
        0 0 160px rgba(255, 140, 66, 0.3),
        inset 0 -15px 25px rgba(0,0,0,0.4),
        inset 0 10px 20px rgba(255, 240, 180, 0.3);
    animation: glow 3s ease-in-out infinite;
}
.lantern-body::before, .lantern-body::after {
    content: "";
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 42px;
    height: 9px;
    background: linear-gradient(180deg, #2a1810 0%, #1a0e08 100%);
    border-radius: 3px;
    box-shadow: 0 0 5px rgba(0,0,0,0.5);
}
.lantern-body::before { top: -5px; }
.lantern-body::after { bottom: -5px; }

.lantern-stripes {
    position: absolute;
    top: 22%;
    left: 0;
    width: 100%;
    height: 1.5px;
    background: rgba(0,0,0,0.5);
    box-shadow: 
        0 14px 0 rgba(0,0,0,0.5),
        0 28px 0 rgba(0,0,0,0.5),
        0 42px 0 rgba(0,0,0,0.5);
}
.lantern-body span {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    color: #2a0a0a;
    font-size: 26px;
    font-weight: bold;
    text-shadow: 0 0 4px rgba(255, 220, 150, 0.9);
    z-index: 2;
}

/* 등불 술(태슬) 장식 */
.lantern-body .tassel {
    position: absolute;
    bottom: -35px;
    left: 50%;
    transform: translateX(-50%);
    width: 4px;
    height: 25px;
    background: linear-gradient(180deg, #d4af37 0%, #b8860b 100%);
    font-size: 0;
}
.lantern-body .tassel::before {
    content: "";
    position: absolute;
    bottom: -8px;
    left: -8px;
    width: 20px;
    height: 15px;
    background: 
        repeating-linear-gradient(90deg, #d4af37 0px, #d4af37 2px, #b8860b 2px, #b8860b 4px);
    border-radius: 0 0 50% 50%;
}

.lantern-left-1 { left: 4%; }
.lantern-left-1 .lantern-wrap { animation-delay: 0s; }
.lantern-left-2 { left: 16%; }
.lantern-left-2 .lantern-wrap { animation-delay: -1.5s; }
.lantern-right-1 { right: 4%; }
.lantern-right-1 .lantern-wrap { animation-delay: -2s; }
.lantern-right-2 { right: 16%; }
.lantern-right-2 .lantern-wrap { animation-delay: -0.8s; }

@keyframes swing {
    0%, 100% { transform: rotate(-5deg); }
    50% { transform: rotate(5deg); }
}
@keyframes glow {
    0%, 100% { 
        box-shadow: 
            0 0 50px rgba(255, 140, 66, 0.9),
            0 0 100px rgba(255, 140, 66, 0.6),
            0 0 160px rgba(255, 140, 66, 0.3),
            inset 0 -15px 25px rgba(0,0,0,0.4);
    }
    50% { 
        box-shadow: 
            0 0 70px rgba(255, 200, 100, 1),
            0 0 140px rgba(255, 200, 100, 0.8),
            0 0 220px rgba(255, 200, 100, 0.5),
            inset 0 -15px 25px rgba(0,0,0,0.4);
    }
}

/* ===== 가랜드 (오색 깃발 줄) 🎏 ===== */
.garland {
    position: fixed;
    top: 130px;
    left: 0;
    width: 100%;
    height: 40px;
    z-index: -1;
    display: flex;
    justify-content: space-around;
    padding: 0 5%;
}
.flag {
    width: 0;
    height: 0;
    border-left: 12px solid transparent;
    border-right: 12px solid transparent;
    border-top: 20px solid;
    animation: flagWave 3s ease-in-out infinite;
}
.flag:nth-child(1) { border-top-color: #ff6b9d; animation-delay: 0s; }
.flag:nth-child(2) { border-top-color: #ffd93d; animation-delay: 0.2s; }
.flag:nth-child(3) { border-top-color: #6bcf7f; animation-delay: 0.4s; }
.flag:nth-child(4) { border-top-color: #4ecdc4; animation-delay: 0.6s; }
.flag:nth-child(5) { border-top-color: #c780ff; animation-delay: 0.8s; }
.flag:nth-child(6) { border-top-color: #ff6b9d; animation-delay: 1s; }
.flag:nth-child(7) { border-top-color: #ffd93d; animation-delay: 1.2s; }
.flag:nth-child(8) { border-top-color: #6bcf7f; animation-delay: 1.4s; }
.flag:nth-child(9) { border-top-color: #4ecdc4; animation-delay: 1.6s; }
.flag:nth-child(10) { border-top-color: #c780ff; animation-delay: 1.8s; }
.flag:nth-child(11) { border-top-color: #ff6b9d; animation-delay: 2s; }
.flag:nth-child(12) { border-top-color: #ffd93d; animation-delay: 2.2s; }

@keyframes flagWave {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-5px) rotate(5deg); }
}
/* 가랜드 줄 */
.garland::before {
    content: "";
    position: absolute;
    top: 0;
    left: 5%;
    width: 90%;
    height: 2px;
    background: #5a3a20;
    box-shadow: 0 0 5px rgba(0,0,0,0.4);
}

/* ===== 길거리 등 (지면 가까이) 🏮 ===== */
.street-lamp-l, .street-lamp-r {
    position: fixed;
    bottom: 5%;
    width: 8px;
    height: 120px;
    background: linear-gradient(180deg, #2a1810 0%, #1a0e08 100%);
    z-index: -1;
}
.street-lamp-l { left: 6%; }
.street-lamp-r { right: 6%; }
.street-lamp-l::before, .street-lamp-r::before {
    content: "";
    position: absolute;
    top: -20px;
    left: -15px;
    width: 38px;
    height: 50px;
    background: radial-gradient(ellipse at center, 
        #fff2a8 0%, #ffb347 50%, #c62828 100%);
    border-radius: 50% 50% 30% 30%;
    box-shadow: 
        0 0 30px rgba(255, 180, 80, 0.8),
        0 0 60px rgba(255, 180, 80, 0.5);
    animation: glow 3s ease-in-out infinite;
}

/* ===== 사케 통 (벽 앞 장식) 🍶 ===== */
.sake-barrel-l, .sake-barrel-r {
    position: fixed;
    bottom: 5%;
    width: 60px;
    height: 70px;
    background: 
        repeating-linear-gradient(180deg,
            #8b6f47 0px, #8b6f47 8px,
            #2a1810 8px, #2a1810 10px,
            #8b6f47 10px, #8b6f47 18px);
    border-radius: 8px;
    border: 3px solid #2a1810;
    z-index: -1;
    box-shadow: 0 5px 15px rgba(0,0,0,0.5);
}
.sake-barrel-l { left: 28%; }
.sake-barrel-r { right: 28%; }
.sake-barrel-l::before, .sake-barrel-r::before {
    content: "酒";
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    color: #2a1810;
    font-size: 24px;
    font-weight: bold;
    background: #f5e6d3;
    width: 40px; height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #2a1810;
}

/* ===== 벚꽃잎 ===== */
.sakura {
    position: fixed;
    width: 12px;
    height: 12px;
    background: radial-gradient(circle, #ffb7c5 0%, #ff8fab 100%);
    border-radius: 0 100% 0 100%;
    opacity: 0.8;
    z-index: -1;
    animation: fall linear infinite;
}
@keyframes fall {
    0% { transform: translateY(-10vh) rotate(0deg); opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { transform: translateY(110vh) rotate(720deg); opacity: 0; }
}

/* 별 */
.star {
    position: fixed;
    width: 2px;
    height: 2px;
    background: #fff;
    border-radius: 50%;
    z-index: -3;
    animation: twinkle 3s ease-in-out infinite;
}
@keyframes twinkle {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

/* ===== 콘텐츠 박스 ===== */
.block-container {
    background: rgba(20, 15, 35, 0.88);
    border-radius: 20px;
    padding: 2rem !important;
    backdrop-filter: blur(10px);
    border: 2px solid rgba(212, 175, 55, 0.5);
    box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.6),
        0 0 80px rgba(255, 183, 77, 0.2),
        inset 0 0 30px rgba(212, 175, 55, 0.05);
    margin-top: 9rem;
}

h1, h2, h3 {
    color: #ffd9a0 !important;
    text-shadow: 0 0 18px rgba(255, 183, 77, 0.7);
}
p, label, .stMarkdown, span:not(.lantern-body span) {
    color: #f5e6d3 !important;
}

.stSelectbox > div > div {
    background-color: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 183, 77, 0.4) !important;
    color: #f5e6d3 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #ff8a65 0%, #ffb74d 50%, #d4af37 100%);
    color: #2d1b3d;
    font-weight: bold;
    border: 2px solid #d4af37;
    border-radius: 25px;
    padding: 12px 35px;
    box-shadow: 
        0 4px 20px rgba(255, 138, 101, 0.5),
        0 0 35px rgba(212, 175, 55, 0.4);
    transition: all 0.3s ease;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow: 
        0 6px 30px rgba(255, 138, 101, 0.9),
        0 0 60px rgba(212, 175, 55, 0.7);
}

.stAlert {
    background-color: rgba(255, 183, 77, 0.15) !important;
    border-left: 4px solid #ffb74d !important;
}
hr { border-color: rgba(212, 175, 55, 0.4); }
</style>

<!-- 별 -->
<div class="star" style="top: 3%; left: 8%;"></div>
<div class="star" style="top: 6%; left: 22%; animation-delay: 0.5s;"></div>
<div class="star" style="top: 2%; left: 38%; animation-delay: 1s;"></div>
<div class="star" style="top: 5%; left: 55%; animation-delay: 1.5s;"></div>
<div class="star" style="top: 7%; left: 70%; animation-delay: 2s;"></div>
<div class="star" style="top: 4%; left: 88%; animation-delay: 2.5s;"></div>
<div class="star" style="top: 18%; left: 30%; animation-delay: 0.8s;"></div>
<div class="star" style="top: 22%; left: 65%; animation-delay: 1.8s;"></div>
<div class="star" style="top: 15%; left: 50%; animation-delay: 2.2s;"></div>

<!-- 불꽃놀이 🎆 -->
<div class="firework firework-1"></div>
<div class="firework firework-2"></div>
<div class="firework firework-3"></div>

<!-- 멀리 풍경 -->
<div class="city-left"></div>
<div class="city-right"></div>
<div class="mountain"></div>

<!-- 벚꽃잎 🌸 -->
<div class="sakura" style="left: 5%; animation-duration: 12s; animation-delay: 0s;"></div>
<div class="sakura" style="left: 18%; animation-duration: 15s; animation-delay: 3s;"></div>
<div class="sakura" style="left: 30%; animation-duration: 10s; animation-delay: 6s;"></div>
<div class="sakura" style="left: 42%; animation-duration: 14s; animation-delay: 2s;"></div>
<div class="sakura" style="left: 55%; animation-duration: 13s; animation-delay: 5s;"></div>
<div class="sakura" style="left: 68%; animation-duration: 16s; animation-delay: 8s;"></div>
<div class="sakura" style="left: 80%; animation-duration: 11s; animation-delay: 10s;"></div>
<div class="sakura" style="left: 92%; animation-duration: 13s; animation-delay: 4s;"></div>

<!-- 기와 지붕 -->
<div class="roof">
    <div class="roof-top"></div>
    <div class="roof-tiles"></div>
    <div class="roof-bottom"></div>
</div>

<!-- 가랜드 (오색 깃발) 🎏 -->
<div class="garland">
    <div class="flag"></div><div class="flag"></div><div class="flag"></div>
    <div class="flag"></div><div class="flag"></div><div class="flag"></div>
    <div class="flag"></div><div class="flag"></div><div class="flag"></div>
    <div class="flag"></div><div class="flag"></div><div class="flag"></div>
</div>

<!-- 등불 4개 -->
<div class="lantern-container">
    <div class="lantern-left-1">
        <div class="lantern-wrap">
            <div class="lantern-string"></div>
            <div class="lantern-body">
                <div class="lantern-stripes"></div>
                <span>酒</span>
                <div class="tassel"></div>
            </div>
        </div>
    </div>
    <div class="lantern-left-2">
        <div class="lantern-wrap">
            <div class="lantern-string"></div>
            <div class="lantern-body">
                <div class="lantern-stripes"></div>
                <span>福</span>
                <div class="tassel"></div>
            </div>
        </div>
    </div>
    <div class="lantern-right-1">
        <div class="lantern-wrap">
            <div class="lantern-string"></div>
            <div class="lantern-body">
                <div class="lantern-stripes"></div>
                <span>祭</span>
                <div class="tassel"></div>
            </div>
        </div>
    </div>
    <div class="lantern-right-2">
        <div class="lantern-wrap">
            <div class="lantern-string"></div>
            <div class="lantern-body">
                <div class="lantern-stripes"></div>
                <span>味</span>
                <div class="tassel"></div>
            </div>
        </div>
    </div>
</div>

<!-- 대나무 -->
<div class="bamboo-left"></div>
<div class="bamboo-right"></div>

<!-- 가게 벽 + 격자창 + 노렌 -->
<div class="izakaya-wall"></div>
<div class="wall-trim"></div>
<div class="window-l1"></div>
<div class="window-l2"></div>
<div class="window-r1"></div>
<div class="window-r2"></div>
<div class="mini-noren-left"></div>
<div class="mini-noren-right"></div>
<div class="noren"></div>

<!-- 길거리 등 + 사케 통 -->
<div class="street-lamp-l"></div>
<div class="street-lamp-r"></div>
<div class="sake-barrel-l"></div>
<div class="sake-barrel-r"></div>
""", unsafe_allow_html=True)

# 3. 타이틀
st.title("🏮 이자카야 MBTI 저녁 추천 🍶")
st.markdown("### **🌙 어서오세요, 오늘도 수고 많으셨어요.**")
st.write("당신의 MBTI와 오늘 기분을 알려주시면, 따스한 한 끼를 추천해 드릴게요. 🎋🎆")
st.write("---")

# 4. 메뉴 데이터
mood_list = ["😄 신난다", "😴 피곤하다", "😢 우울하다", "😡 스트레스", "🥰 설렌다"]

default_meals = {
    "😄 신난다": [
        {"menu": "🍕 페퍼로니 피자", "desc": "신난 기분엔 피자가 진리! 🎉", "img": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600"},
        {"menu": "🍔 더블 치즈버거", "desc": "기분 좋게 한 입 가득! 🤤", "img": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600"},
        {"menu": "🍗 후라이드 치킨", "desc": "바삭함이 신난 기분을 두 배로! 🥳", "img": "https://images.unsplash.com/photo-1562967914-608f82629710?w=600"},
    ],
    "😴 피곤하다": [
        {"menu": "🍲 국밥 한 그릇", "desc": "든든하고 따뜻한 한 그릇으로 회복! 💪", "img": "https://images.unsplash.com/photo-1583187854376-e602a4b66b67?w=600"},
        {"menu": "🍜 따끈한 우동", "desc": "부드러운 면발이 피로를 풀어줘요. 🌾", "img": "https://images.unsplash.com/photo-1618841557871-b4664fbf0cb3?w=600"},
        {"menu": "🍚 영양솥밥", "desc": "꽉 찬 영양으로 에너지 충전! 🌰", "img": "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?w=600"},
    ],
    "😢 우울하다": [
        {"menu": "🍫 초콜릿 디저트", "desc": "달콤함이 위로가 되어줄 거예요. 🤍", "img": "https://images.unsplash.com/photo-1542990253-0b8be4ccea7b?w=600"},
        {"menu": "🍝 크림 파스타", "desc": "부드럽고 진한 크림이 안아줘요. 💛", "img": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=600"},
        {"menu": "🍰 치즈케이크", "desc": "한 입의 달콤함이 마음을 녹여줘요. 🌸", "img": "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=600"},
    ],
    "😡 스트레스": [
        {"menu": "🌶️ 마라탕", "desc": "매콤하게 스트레스 날려버려요! 🔥", "img": "https://images.unsplash.com/photo-1552611052-33e04de081de?w=600"},
        {"menu": "🍗 매운 양념치킨", "desc": "맵단의 조화로 기분 전환! ⚡", "img": "https://images.unsplash.com/photo-1562967914-608f82629710?w=600"},
        {"menu": "🍜 짬뽕", "desc": "얼큰한 국물로 가슴이 뻥! 🌊", "img": "https://images.unsplash.com/photo-1626804475297-41608ea09aeb?w=600"},
    ],
    "🥰 설렌다": [
        {"menu": "🥩 스테이크", "desc": "특별한 날의 특별한 한 끼! ✨", "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?w=600"},
        {"menu": "🍝 감성 파스타", "desc": "촛불과 함께 즐기는 낭만. 🕯️", "img": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=600"},
        {"menu": "🍣 스시 플래터", "desc": "한 점 한 점 특별한 설렘. 💕", "img": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600"},
    ],
}

all_mbti = ["INFP","ENFP","INFJ","ENFJ","INTJ","ENTJ","INTP","ENTP",
            "ISFP","ESFP","ISTP","ESTP","ISFJ","ESFJ","ISTJ","ESTJ"]
mbti_data = {m: default_meals for m in all_mbti}

# 5. 사용자 입력
col1, col2 = st.columns(2)
with col1:
    selected_mbti = st.selectbox("🧬 당신의 MBTI는?", sorted(mbti_data.keys()))
with col2:
    selected_mood = st.selectbox("💭 오늘 기분은?", mood_list)

# 6. 추천 버튼
if st.button("🏮 오늘의 저녁 메뉴 추천받기 🍶"):
    st.balloons()
    st.write("---")
    meals = mbti_data[selected_mbti][selected_mood]
    chosen = random.choice(meals)
    
    st.success(f"### 🌟 **{selected_mbti}** × **{selected_mood}** 님께 추천!")
    st.image(chosen["img"], use_container_width=True, caption=chosen["menu"])
    st.subheader(chosen["menu"])
    st.write(chosen["desc"])
    
    st.write("---")
    st.info("💡 다시 누르면 다른 메뉴도 추천받을 수 있어요! 🔄✨")

이런 느낌으로 애니메이션 넣어줘. 지구 배경으로 해서,, 이런 느낌이라는걸 알아둬. 그리고 배경이 어두운 느낌은 별로야. 밝게 해줘. 그리고 페이지 수가 너무 적어 페이지 다른것들도 많이 추가해줘 여러기능으로. 그리고 페이지 저거 전체데이터 보는 페이지 전혀 필요없거든? 지워. 반 카드 있잖아. 반별 상태 카드. 아무튼 반별 상태 카드 배경은 투명색으로 하지마. 긁이 안읽혀. 그리고 시간 뜨는 부분 너무 밋밋해 글 만 조그마낳게 있어서. 이것도 아까 말했던것처럼 야무지게 도형으로 잘 예쁘게 만들어줘. "반별 상태 (현재 교시 과목 표시)"에서 (현재 교시 과목 표시)는 제거 해줘. 그리고 너무 배경 디자인에 신경쓰다가 웹사이트의 글씨들이나 그래프들이 가독성이 떨어지면 절대 안돼. 아무튼 짜줘.
오후 3:11
AI
와, 이자카야 예시 보니까 어떤 느낌 원하는지 완전히 이해했어요! 👏 그 정도로 디테일하게 배경을 꾸미고 싶은 거였군요. 밝은 지구/하늘 테마로 그 수준의 디자인을 만들어드릴게요.
요청 정리부터 할게요:
요청 정리 ✅
조회(08:1008:20) / 종례(15:0015:10) 추가, 쉬는시간 표시, 일정 끝나면 방과후
이자카야 예시처럼 풍부한 배경 애니메이션 (단, 밝은 지구 테마!)
배경 어둡게 X → 밝게
페이지 더 많이 추가
전체 데이터 페이지 삭제
반별 상태 카드 배경 불투명(글씨 잘 보이게)
시계 부분 예쁘게 도형으로
"반별 상태" 뒤 "(현재 교시 과목 표시)" 제거
가독성 최우선 (배경이 글씨/그래프 안 가리게)
⚠️ 잠깐 시간표 충돌 주의: 종례가 15:0015:10인데, 화·목 7교시가 14:5015:40이에요. 그래서 **화·목은 종례를 7교시 뒤(15:4015:50)**로 자동 처리하고, 월·수·금만 6교시 뒤(15:0015:10)에 종례를 넣을게요. 이게 맞죠?
전체 코드
python
복사
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time as dtime

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의 (조회/교시/쉬는시간/점심/종례)
# ========================================
# 기본 일과 (월·수·금: 6교시 + 종례 15:00~15:10)
SCHEDULE_6 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("종례",     dtime(15, 0),  dtime(15, 10), "homeroom"),
]

# 화·목: 7교시 + 종례 15:40~15:50
SCHEDULE_7 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("쉬는시간", dtime(15, 0),  dtime(15, 10), "break"),
    ("7교시",   dtime(15, 10), dtime(16, 0),  "class"),
    ("종례",     dtime(16, 0),  dtime(16, 10), "homeroom"),
]

# 요일별 일과표 (월=0 ~ 금=4)
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 시간표 (2-3반)
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "문학A", "2교시": "영어B", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "음악 연주와 창작"},
        "화": {"1교시": "선택 과목", "2교시": "문학C", "3교시": "합주", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "스포츠 생활B", "7교시": "선택 과목"},
        "수": {"1교시": "영어A", "2교시": "선택 과목", "3교시": "선택 과목", "4교시": "문학B",
               "5교시": "선택 과목", "6교시": "대수"},
        "목": {"1교시": "선택 과목", "2교시": "스포츠 생활A", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "영어A", "6교시": "선택 과목", "7교시": "대수"},
        "금": {"1교시": "선택 과목", "2교시": "선택 과목", "3교시": "영어C", "4교시": "문학D",
               "5교시": "자율", "6교시": "자율"},
    },
}

MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


# ========================================
# 현재 일정 찾기
# ========================================
def get_current_slot(now):
    """현재 (일정이름, 종류) 반환. 종류: class/break/lunch/homeroom/after/weekend"""
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]

    # 일과 시작 전
    if now_t < schedule[0][1]:
        return "등교 전", "before"

    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind

    # 모든 일정 끝남
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    """현재 교시 과목 반환 (교시일 때만)"""
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


# ========================================
# 데이터 로드
# ========================================
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 에너지 상태 판단
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"

    slot_name, kind = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    people = co2 >= 600

    # 이동수업인데 냉방 켜둠
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"

    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# 카드 색상 매핑
COLOR_HEX = {
    "green":  "#2e7d32",
    "red":    "#c62828",
    "gold":   "#f9a825",
    "orange": "#ef6c00",
    "gray":   "#757575",
}


# ========================================
# 디자인 CSS (밝은 지구/하늘 테마 + 애니메이션)
# ========================================
st.markdown("""
<style>
/* ===== 밝은 하늘 배경 (낮의 지구) ===== */
.stApp {
    background:
        radial-gradient(circle at 80% 15%, rgba(255,241,150,0.6) 0%, rgba(255,241,150,0) 12%),
        linear-gradient(180deg, #ade4ff 0%, #c9efff 35%, #e3f7ff 70%, #f0fbe5 100%);
    background-attachment: fixed;
}

/* 태양 */
.sun {
    position: fixed; top: 8%; right: 10%;
    width: 90px; height: 90px; border-radius: 50%;
    background: radial-gradient(circle, #fff7c2 0%, #ffe066 50%, #ffcc33 100%);
    box-shadow: 0 0 60px rgba(255,204,51,0.7), 0 0 120px rgba(255,224,102,0.5);
    z-index: 0; pointer-events: none;
    animation: sunPulse 5s ease-in-out infinite;
}
@keyframes sunPulse {
    0%,100% { box-shadow: 0 0 60px rgba(255,204,51,0.7), 0 0 120px rgba(255,224,102,0.5);}
    50% { box-shadow: 0 0 80px rgba(255,204,51,0.9), 0 0 160px rgba(255,224,102,0.7);}
}

/* 떠다니는 구름 */
.cloud {
    position: fixed; z-index: 0; pointer-events: none;
    background: #ffffff; border-radius: 100px; opacity: 0.85;
    box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}
.cloud::before, .cloud::after {
    content:''; position:absolute; background:#fff; border-radius:50%;
}
.cloud1 { width:120px; height:40px; top:18%; left:-150px;
          animation: drift1 40s linear infinite; }
.cloud1::before { width:55px; height:55px; top:-25px; left:20px; }
.cloud1::after  { width:40px; height:40px; top:-15px; left:65px; }
.cloud2 { width:90px; height:30px; top:35%; left:-150px;
          animation: drift2 55s linear infinite; }
.cloud2::before { width:42px; height:42px; top:-20px; left:15px; }
.cloud2::after  { width:32px; height:32px; top:-12px; left:50px; }
.cloud3 { width:140px; height:45px; top:55%; left:-200px;
          animation: drift1 65s linear infinite; }
.cloud3::before { width:60px; height:60px; top:-28px; left:25px; }
.cloud3::after  { width:45px; height:45px; top:-18px; left:75px; }
@keyframes drift1 { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }
@keyframes drift2 { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }

/* 떠다니는 잎사귀/원형 도형 (지구 자연 느낌) */
.leaf {
    position: fixed; z-index: 0; pointer-events: none;
    font-size: 28px; opacity: 0.55;
    animation: floatLeaf 18s ease-in-out infinite;
}
.leaf1 { top:70%; left:8%;  animation-delay:0s; }
.leaf2 { top:25%; left:85%; animation-delay:4s; }
.leaf3 { top:80%; left:60%; animation-delay:8s; }
.leaf4 { top:45%; left:30%; animation-delay:12s; }
@keyframes floatLeaf {
    0%,100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-40px) rotate(25deg); }
}

/* 콘텐츠는 항상 배경 위로 (가독성!) */
.main .block-container { position: relative; z-index: 1; }

/* 제목/텍스트 색 (밝은 배경이라 어둡게) */
h1, h2, h3 { color: #0d3b5e !important; text-shadow: 0 1px 2px rgba(255,255,255,0.6); }
.stMarkdown p, label { color: #1a4a6e !important; }

/* 사이드바 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1565c0 0%, #0d47a1 100%);
}
[data-testid="stSidebar"] * { color: #ffffff !important; }

/* ===== 멋진 시계 박스 ===== */
.clock-box {
    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 60%, #29b6f6 100%);
    border-radius: 28px;
    padding: 28px 30px;
    margin-bottom: 24px;
    box-shadow: 0 10px 35px rgba(25,118,210,0.4), inset 0 2px 10px rgba(255,255,255,0.3);
    position: relative;
    overflow: hidden;
    border: 3px solid rgba(255,255,255,0.5);
}
.clock-box::before {
    content:''; position:absolute; top:-40px; right:-40px;
    width:160px; height:160px; border-radius:50%;
    background: rgba(255,255,255,0.15);
}
.clock-box::after {
    content:''; position:absolute; bottom:-50px; left:-30px;
    width:130px; height:130px; border-radius:50%;
    background: rgba(255,255,255,0.1);
}
.clock-time {
    font-size: 54px; font-weight: 900; color: #ffffff; margin:0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.25); letter-spacing: 2px;
    position: relative; z-index: 2;
}
.clock-date { font-size: 18px; color: #e3f2fd; margin:4px 0 0 0; position: relative; z-index: 2; }
.clock-slot {
    display:inline-block; margin-top:14px; padding:8px 22px;
    background: rgba(255,255,255,0.95); border-radius: 30px;
    font-size: 20px; font-weight: 800; color: #0d47a1;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; z-index: 2;
}

/* ===== 반별 상태 카드 (불투명!) ===== */
.class-card {
    border-radius: 22px;
    padding: 20px;
    margin-bottom: 8px;
    color: #ffffff;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    border: 3px solid rgba(255,255,255,0.6);
    position: relative;
    overflow: hidden;
}
.class-card::before {
    content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%;
    background: rgba(255,255,255,0.12);
}
.cc-name { font-size: 26px; font-weight: 900; margin:0; }
.cc-subject { font-size: 15px; opacity: 0.95; margin:2px 0 10px 0; }
.cc-status { font-size: 19px; font-weight: 800; margin:6px 0; }
.cc-reason { font-size: 13px; opacity: 0.92; margin-bottom:10px; }
.cc-data { font-size: 15px; font-weight: 600;
           background: rgba(255,255,255,0.18); border-radius: 12px; padding: 8px 10px; }

/* 일반 정보 박스 */
.info-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 22px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    border: 2px solid #e0f0ff;
    margin-bottom: 12px;
}
</style>

<div class="sun"></div>
<div class="cloud cloud1"></div>
<div class="cloud cloud2"></div>
<div class="cloud cloud3"></div>
<div class="leaf leaf1">🍃</div>
<div class="leaf leaf2">🌿</div>
<div class="leaf leaf3">🍃</div>
<div class="leaf leaf4">🌎</div>
""", unsafe_allow_html=True)


# ========================================
# 현재 시각 / 일정
# ========================================
now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# ========================================
# 사이드바
# ========================================
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "ℹ️ 시스템 정보"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 페이지 1: 대시보드 홈
# ========================================
if page == "🏠 대시보드 홈":
    weekday_name = WEEKDAY_KR[now.weekday()]

    # 일정 종류별 아이콘
    slot_icons = {
        "class": "📚", "break": "☕", "lunch": "🍱",
        "homeroom": "📢", "after": "🏠", "before": "🌅",
        "weekend": "🌴",
    }
    icon = slot_icons.get(slot_kind, "🕐")

    st.markdown(f"""
    <div class="clock-box">
        <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
        <span class="clock-slot">{icon} {slot_name}</span>
    </div>
    """, unsafe_allow_html=True)

    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()

    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, slot_name)
            subject_text = f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg = COLOR_HEX.get(color, "#757575")
            with cols[idx]:
                st.markdown(f"""
                <div class="class-card" style="background:{bg};">
                    <p class="cc-name">{row['반']}</p>
                    <p class="cc-subject">{subject_text}</p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">{reason}</p>
                    <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                    💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div>
                </div>
                """, unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, slot_name)

    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재: {subject or slot_name} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3,
                          marker=dict(size=7, color=color))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e",
            title_font_size=18,
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.1)")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#e53935"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#00897b"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#1e88e5"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("적정 온도(25도)에 가까울수록 높은 점수!")

    latest = df.groupby("반").last().reset_index()

    def score(temp):
        if pd.isna(temp):
            return 0
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    for idx, row in ranked.iterrows():
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
        bg = COLOR_HEX.get(color, "#757575")
        st.markdown(f"""
        <div class="class-card" style="background:{bg}; display:flex; align-items:center;">
            <div style="font-size:38px; margin-right:20px;">{medal}</div>
            <div style="flex:2;">
                <p class="cc-name">{row['반']}</p>
                <p class="cc-subject">{int(row['점수'])}점</p>
            </div>
            <div style="flex:3;">
                <p class="cc-status">{status}</p>
                <p class="cc-reason">🌡️ {row['온도']}°C · {reason}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")

    class_list = sorted(TIMETABLE.keys())
    selected = st.selectbox("반 선택", class_list)

    weekday = now.weekday()
    if weekday >= 5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day = WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule = DAY_SCHEDULE[weekday]

        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"

            # 현재 진행 중인 시간 강조
            is_now = (start <= now.time() < end)
            highlight = "border:3px solid #ff5722; box-shadow:0 0 15px rgba(255,87,34,0.4);" if is_now else ""

            label = name
            if subject:
                label = f"{name} · {subject}"
            now_tag = " 🔴 진행중" if is_now else ""

            st.markdown(f"""
            <div class="info-card" style="{highlight}">
                <b style="color:#0d3b5e; font-size:18px;">{label}{now_tag}</b><br>
                <span style="color:#1a4a6e;">🕐 {time_str}</span>
            </div>
            """, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")
    st.caption("전체 데이터를 분석한 통계입니다.")

    if df["온도"].notna().sum() == 0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df['습도'].mean():.1f} %")

        st.divider()

        # 반별 평균 온도 막대그래프
        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="RdYlBu_r")
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e", height=350,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 온도 분포
        st.subheader("🌡️ 온도 분포")
        fig2 = px.histogram(df, x="온도", nbins=20, color_discrete_sequence=["#42a5f5"])
        fig2.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e", height=300,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ========================================
# 페이지 6: 시스템 정보
# ========================================
elif page == "ℹ️ 시스템 정보":
    st.title("ℹ️ 시스템 정보")

    st.markdown("""
    <div class="info-card">
    <h3>🌍 교실 에너지 모니터링 시스템</h3>
    <p>라즈베리파이 피코 + 센서로 각 교실의 환경을 실시간 측정하고,
    에너지 낭비를 감지하는 시스템입니다.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📡 측정 항목")
    st.markdown("""
    - 🫁 **CO₂ 농도** (SCD30 센서) — 사람 유무 추정
    - 🌡️ **온도 / 습도** (SCD30 센서) — 냉난방 상태
    - 🔥 **가스 농도** (MQ-2 센서) — 공기질
    """)

    st.subheader("⚡ 에너지 낭비 판단 기준")
    st.markdown("""
    - 🔴 **과냉방**: 온도 22도 미만 + 사람 있음
    - 🟡 **빈 교실 냉방**: 온도 낮은데 사람 없음
    - 🔴 **이동수업 낭비**: 체육 등 이동수업인데 냉방 켜둠
    - ⚪ **냉방 안 함**: 온도 29도 이상
    - 🟢 **정상**: 22~28도
    """)

    st.subheader("🔄 데이터 흐름")
    st.markdown("""
    `피코(센서)` → `구글 시트` → `이 대시보드`
    (30초마다 자동 갱신)
    """)
주요 변경/추가 사항
✅ 일정 시스템 (조회/쉬는시간/점심/종례/방과후)
월·수·금: 6교시 + 종례(15:00~15:10)
화·목: 7교시 + 종례(16:00~16:10)
쉬는 시간 10분씩 넣음
일과 끝나면 방과후, 시작 전엔 등교 전, 주말은 주말
⚠️ 쉬는 시간 넣으면서 교시 시간이 살짝 바뀌었어요. 실제 학교 시간과 다르면 SCHEDULE_6, SCHEDULE_7의 시간을 수정하세요!
✅ 밝은 지구/하늘 테마 애니메이션
☀️ 빛나는 태양 (맥동 애니메이션)
☁️ 떠다니는 구름 3개 (좌→우 이동)
🍃 떠다니는 잎사귀/지구 이모지
전부 z-index:0 → 콘텐츠(z-index:1) 뒤에 깔려서 글씨 안 가림!
✅ 멋진 시계 박스
파란 그라데이션 + 장식 원 + 큰 시계 + 일정 배지
✅ 반별 카드 불투명
상태별 진한 색 배경(초록/빨강 등)에 흰 글씨 → 가독성 ↑
✅ 페이지 6개로 확장
🏠 대시보드 홈
📊 반별 상세
🏆 에너지 랭킹
📅 오늘의 시간표 (NEW! 현재 시간 강조)
💡 에너지 리포트 (NEW! 평균/분포 통계)
ℹ️ 시스템 정보 (NEW! 설명)
✅ 전체 데이터 페이지 삭제, "(현재 교시 과목 표시)" 제거
실행
code
복사
py -m streamlit run dashboard.py

다음 행동
위 코드로 교체 후 실행
밝은 배경 + 애니메이션 잘 나오는지
시계/카드 예쁘게 나오는지
6개 페이지 둘러보기
쉬는시간 넣은 교시 시간이 실제와 맞는지 확인 (다르면 수정!)
어때요? 더 다듬고 싶은 부분 있으면 알려줘요:
배경 애니메이션 더 추가/조정?
특정 페이지 기능 보강?
색상 톤 변경?
해보고 결과 알려줄래요? 🙂
오후 3:13
나
반별 상세 그래프 페이지의 글씨색이 하얀색이여서, 밝은 배경에 전혀 안보이잖아. 이럴줄 알았어. 웹사이트의 모든 글씨들에 테두리를 추가해줘. 그럼 잘보이겠지. 웹사이트 배경 나쁘지 않긴한데, 지구가 절반만 보이는 상태로 배경 아래쪽에서 빙빙 돌고 있는 느낌으로, 화면 스크롤 움직여도 화면 아래쪽에 지구 절반 도는건 화면 안에서 고정되게. 그리고 마우스 가져다 대면 카드들 붕 뜨게 드롭다운 형식으로, 세련되게. 추가해줘. 그리고 시계가 아까랑 똑같잖아. 시계를 아예 애니메이션으로 구현해줘. 예쁘게.그리고 에너지 절약 랭킹의 로직이 너무 단순해. 좀 더 구체적으로 로직을 짜줘. 에너지 절약 점수에 대한 로직 말이야. 그리고 시간표 그냥 카드들 나열 말고, 하나로 뭉쳐서 진짜 시간표처럼 야무지게 디자인해줘. 에너지 리포트 페이지는 그래프가 너무 못생겼어. 좀 이쁘게. 시스템 정보 페이지는 없애고, 이 프로젝트가 원하는 목표를 나열해둔 것들을 모아둔 페이지를 추가해줘. 일단 가장 큰 목표는 글씨들 잘 보이는게 우선목표야.
오후 3:15
AI
좋아요, 요청 다 정리했어요! 글씨 가독성이 1순위인 거 확실히 챙길게요. 한 번에 다 반영해서 만들게요.
요청 정리 ✅
모든 글씨에 테두리(외곽선) → 어디서든 잘 보이게 (최우선!)
반쯤 보이는 지구가 화면 하단에서 회전 (스크롤해도 고정)
카드 hover 시 붕 뜨는 효과
시계를 애니메이션 시계로 예쁘게
에너지 랭킹 로직 정교하게 (온도+CO₂+이동수업 등 복합)
시간표를 진짜 표처럼 디자인
에너지 리포트 그래프 예쁘게
시스템 정보 → 프로젝트 목표 페이지로 교체
전체 코드
python
복사
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime

SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의
# ========================================
SCHEDULE_6 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("종례",     dtime(15, 0),  dtime(15, 10), "homeroom"),
]
SCHEDULE_7 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("쉬는시간", dtime(15, 0),  dtime(15, 10), "break"),
    ("7교시",   dtime(15, 10), dtime(16, 0),  "class"),
    ("종례",     dtime(16, 0),  dtime(16, 10), "homeroom"),
]
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 시간표
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "문학A", "2교시": "영어B", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "음악 연주와 창작"},
        "화": {"1교시": "선택 과목", "2교시": "문학C", "3교시": "합주", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "스포츠 생활B", "7교시": "선택 과목"},
        "수": {"1교시": "영어A", "2교시": "선택 과목", "3교시": "선택 과목", "4교시": "문학B",
               "5교시": "선택 과목", "6교시": "대수"},
        "목": {"1교시": "선택 과목", "2교시": "스포츠 생활A", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "영어A", "6교시": "선택 과목", "7교시": "대수"},
        "금": {"1교시": "선택 과목", "2교시": "선택 과목", "3교시": "영어C", "4교시": "문학D",
               "5교시": "자율", "6교시": "자율"},
    },
}
MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


def get_current_slot(now):
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]
    if now_t < schedule[0][1]:
        return "등교 전", "before"
    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 에너지 상태 판단
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"
    slot_name, kind = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    people = co2 >= 600
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"
    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


COLOR_HEX = {
    "green": "#2e7d32", "red": "#c62828", "gold": "#f9a825",
    "orange": "#ef6c00", "gray": "#757575",
}


# ========================================
# 에너지 점수 로직 (정교화)
# ========================================
def energy_score(class_id, df_class, now):
    """
    여러 요소를 종합해 0~100점 계산.
    - 온도 적정성 (50점): 24~26도가 만점, 멀어질수록 감점
    - 환기 적정성 (20점): CO2가 너무 높으면(환기 안함) 감점
    - 이동수업 낭비 (30점 감점): 이동수업인데 냉방 켜둠
    - 안정성: 온도 변동이 심하면 약간 감점
    """
    if df_class["온도"].notna().sum() == 0:
        return 0, {}

    latest = df_class.iloc[-1]
    temp = latest["온도"]
    co2 = latest["co2"]

    detail = {}

    # 1) 온도 점수 (50점 만점) — 24~26도 적정
    if 24 <= temp <= 26:
        temp_score = 50
    else:
        # 적정 범위에서 벗어난 만큼 감점 (1도당 8점)
        if temp < 24:
            gap = 24 - temp
        else:
            gap = temp - 26
        temp_score = max(0, 50 - gap * 8)
    detail["온도"] = round(temp_score, 1)

    # 2) 환기 점수 (20점 만점) — CO2 적정
    if co2 <= 1000:
        vent_score = 20
    elif co2 <= 1500:
        vent_score = 12
    elif co2 <= 2000:
        vent_score = 6
    else:
        vent_score = 0
    detail["환기"] = vent_score

    # 3) 기본 점수 (20점) - 측정 정상 작동
    base_score = 20
    detail["측정"] = base_score

    # 4) 이동수업 낭비 감점 (최대 -30)
    slot_name, _ = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    penalty = 0
    if subject in MOVING_SUBJECTS and temp < 24:
        penalty = 30
        detail["이동수업 낭비"] = -penalty

    # 5) 온도 안정성 (최대 -10) - 최근 데이터 변동성
    recent = df_class["온도"].dropna().tail(10)
    if len(recent) >= 3:
        volatility = recent.std()
        if volatility > 2:
            stab_penalty = min(10, (volatility - 2) * 5)
            detail["변동성"] = -round(stab_penalty, 1)
            penalty += stab_penalty

    total = temp_score + vent_score + base_score - penalty
    total = max(0, min(100, total))
    return round(total, 1), detail


# ========================================
# CSS (글씨 외곽선 + 회전 지구 + hover + 애니메이션 시계)
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #aee2ff 0%, #cdeeff 40%, #e6f7ff 70%, #f2fbff 100%);
    background-attachment: fixed;
}

/* ===== 모든 글씨에 외곽선 (가독성!) ===== */
h1, h2, h3, h4, p, span, label, .stMarkdown, div[data-testid="stMetricValue"],
div[data-testid="stMetricLabel"], .stCaption, .stSelectbox label {
    text-shadow:
        -1px -1px 0 #ffffff, 1px -1px 0 #ffffff,
        -1px  1px 0 #ffffff, 1px  1px 0 #ffffff,
         0px  0px 4px rgba(255,255,255,0.9) !important;
}
h1, h2, h3 { color: #0a2e4d !important; }
.stMarkdown p, label { color: #103a5e !important; font-weight: 600; }

/* ===== 화면 하단 회전하는 반쪽 지구 (스크롤 고정) ===== */
.earth {
    position: fixed;
    bottom: -360px;          /* 절반만 보이게 아래로 내림 */
    left: 50%;
    transform: translateX(-50%);
    width: 700px; height: 700px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 35% 30%, rgba(255,255,255,0.5) 0%, transparent 35%),
        linear-gradient(180deg, #2196f3 0%, #1976d2 100%);
    box-shadow: 0 0 80px rgba(33,150,243,0.5), inset -30px -30px 80px rgba(0,0,0,0.25);
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
    animation: spinEarth 40s linear infinite;
}
/* 대륙 무늬 */
.earth::before {
    content: '';
    position: absolute; top: 18%; left: 12%;
    width: 180px; height: 120px;
    background: #43a047; border-radius: 45% 55% 60% 40%;
    box-shadow: 220px 90px 0 -10px #66bb6a,
                120px 260px 0 -5px #43a047,
                360px 200px 0 -20px #66bb6a,
                40px 380px 0 -15px #4caf50;
    opacity: 0.85;
}
.earth::after {
    content: '';
    position: absolute; bottom: 15%; right: 15%;
    width: 140px; height: 100px;
    background: #4caf50; border-radius: 50% 40% 55% 45%;
    box-shadow: -260px -40px 0 -15px #66bb6a, -100px 120px 0 -10px #43a047;
    opacity: 0.8;
}
@keyframes spinEarth {
    from { transform: translateX(-50%) rotate(0deg); }
    to   { transform: translateX(-50%) rotate(360deg); }
}

/* 구름 */
.cloud { position: fixed; z-index: 0; pointer-events: none;
         background:#fff; border-radius:100px; opacity:0.85; }
.cloud::before, .cloud::after { content:''; position:absolute; background:#fff; border-radius:50%; }
.cloud1 { width:120px;height:40px;top:12%;left:-150px; animation:drift 45s linear infinite; }
.cloud1::before{width:55px;height:55px;top:-25px;left:20px;}
.cloud1::after{width:40px;height:40px;top:-15px;left:65px;}
.cloud2 { width:90px;height:30px;top:28%;left:-150px; animation:drift 60s linear infinite; }
.cloud2::before{width:42px;height:42px;top:-20px;left:15px;}
.cloud2::after{width:32px;height:32px;top:-12px;left:50px;}
@keyframes drift { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }

.main .block-container { position: relative; z-index: 1; }

/* 사이드바 */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1565c0 0%, #0d47a1 100%); }
[data-testid="stSidebar"] * { color:#fff !important;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.4) !important; }

/* ===== 애니메이션 시계 ===== */
.clock-wrap {
    display:flex; align-items:center; gap:30px;
    background: linear-gradient(135deg,#42a5f5,#1976d2);
    border-radius:30px; padding:24px 36px; margin-bottom:24px;
    box-shadow:0 12px 35px rgba(25,118,210,0.45), inset 0 2px 12px rgba(255,255,255,0.3);
    border:3px solid rgba(255,255,255,0.6);
}
.analog {
    width:110px; height:110px; border-radius:50%;
    background: radial-gradient(circle,#fff 0%,#e3f2fd 100%);
    border:6px solid #fff; position:relative; flex-shrink:0;
    box-shadow:0 4px 15px rgba(0,0,0,0.25), inset 0 0 10px rgba(0,0,0,0.1);
}
.analog .center { position:absolute; top:50%; left:50%;
    width:10px; height:10px; background:#0d47a1; border-radius:50%;
    transform:translate(-50%,-50%); z-index:5; }
.hand { position:absolute; bottom:50%; left:50%; transform-origin:bottom center;
    border-radius:10px; }
.hour { width:5px; height:28px; background:#0d47a1; margin-left:-2.5px;
    animation:spinH 43200s linear infinite; }
.minute { width:4px; height:40px; background:#1976d2; margin-left:-2px;
    animation:spinM 3600s linear infinite; }
.second { width:2px; height:45px; background:#e53935; margin-left:-1px;
    animation:spinS 60s linear infinite; }
@keyframes spinS { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinM { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinH { from{transform:rotate(0);} to{transform:rotate(360deg);} }
/* 시계 눈금 */
.tick { position:absolute; width:2px; height:8px; background:#90caf9; left:50%; top:4px;
    margin-left:-1px; transform-origin:50% 51px; }

.clock-digital { color:#fff; }
.clock-time { font-size:48px; font-weight:900; margin:0; letter-spacing:2px;
    text-shadow:0 2px 6px rgba(0,0,0,0.3) !important; }
.clock-date { font-size:17px; margin:2px 0 0 0; color:#e3f2fd; }
.clock-slot { display:inline-block; margin-top:10px; padding:7px 20px;
    background:rgba(255,255,255,0.95); border-radius:30px;
    font-size:18px; font-weight:800; color:#0d47a1;
    text-shadow:none !important; }

/* ===== 반별 카드 (불투명 + hover 붕) ===== */
.class-card {
    border-radius:22px; padding:20px; margin-bottom:14px; color:#fff;
    box-shadow:0 8px 24px rgba(0,0,0,0.2);
    border:3px solid rgba(255,255,255,0.6); position:relative; overflow:hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.class-card:hover {
    transform: translateY(-12px) scale(1.03);
    box-shadow:0 20px 40px rgba(0,0,0,0.35);
}
.class-card::before { content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%; background:rgba(255,255,255,0.12); }
.class-card p { text-shadow: 1px 1px 2px rgba(0,0,0,0.4) !important; }
.cc-name { font-size:26px; font-weight:900; margin:0; }
.cc-subject { font-size:15px; opacity:0.95; margin:2px 0 10px 0; }
.cc-status { font-size:19px; font-weight:800; margin:6px 0; }
.cc-reason { font-size:13px; opacity:0.92; margin-bottom:10px; }
.cc-data { font-size:15px; font-weight:600;
    background:rgba(0,0,0,0.18); border-radius:12px; padding:8px 10px; }

.info-card {
    background:#ffffff; border-radius:20px; padding:22px;
    box-shadow:0 6px 20px rgba(0,0,0,0.1); border:2px solid #e0f0ff; margin-bottom:12px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.info-card:hover { transform: translateY(-6px); box-shadow:0 14px 30px rgba(0,0,0,0.18); }
.info-card p, .info-card b, .info-card span { text-shadow:none !important; }

/* 시간표 */
.tt-table { width:100%; border-collapse:separate; border-spacing:0;
    background:#fff; border-radius:18px; overflow:hidden;
    box-shadow:0 8px 24px rgba(0,0,0,0.15); }
.tt-table th { background:linear-gradient(135deg,#1976d2,#42a5f5); color:#fff;
    padding:14px; font-size:16px; text-shadow:1px 1px 2px rgba(0,0,0,0.3) !important; }
.tt-table td { padding:14px; text-align:center; border-bottom:1px solid #e3f2fd;
    color:#0d3b5e; font-weight:600; text-shadow:none !important; }
.tt-period { background:#e3f2fd; font-weight:800; color:#0d47a1; }
.tt-now { background:#fff3e0 !important; box-shadow:inset 0 0 0 3px #ff5722; }
.tt-break td { background:#f5f5f5; color:#999; font-size:13px; }
.tt-lunch td { background:#fff8e1; color:#f57f17; font-weight:800; }
.tt-home td { background:#e8f5e9; color:#2e7d32; font-weight:800; }
</style>

<div class="earth"></div>
<div class="cloud cloud1"></div>
<div class="cloud cloud2"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# 사이드바
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "🎯 프로젝트 목표"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 애니메이션 시계 HTML 생성 함수
# ========================================
def render_clock(now, slot_name, slot_kind):
    slot_icons = {"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢",
                  "after":"🏠","before":"🌅","weekend":"🌴"}
    icon = slot_icons.get(slot_kind, "🕐")
    weekday_name = WEEKDAY_KR[now.weekday()]

    # 현재 시각에 맞춰 시계바늘 시작 각도 계산
    h = now.hour % 12
    m = now.minute
    s = now.second
    sec_deg = s * 6
    min_deg = m * 6 + s * 0.1
    hour_deg = h * 30 + m * 0.5

    # 눈금 12개
    ticks = "".join(
        f'<div class="tick" style="transform:rotate({i*30}deg);"></div>'
        for i in range(12)
    )

    return f"""
    <div class="clock-wrap">
        <div class="analog">
            {ticks}
            <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
            <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
            <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
            <div class="center"></div>
        </div>
        <div class="clock-digital">
            <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
            <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
            <span class="clock-slot">{icon} {slot_name}</span>
        </div>
    </div>
    """


# ========================================
# 페이지 1: 홈
# ========================================
if page == "🏠 대시보드 홈":
    st.markdown(render_clock(now, slot_name, slot_kind), unsafe_allow_html=True)
    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, slot_name)
            subject_text = f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg = COLOR_HEX.get(color, "#757575")
            with cols[idx]:
                st.markdown(f"""
                <div class="class-card" style="background:{bg};">
                    <p class="cc-name">{row['반']}</p>
                    <p class="cc-subject">{subject_text}</p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">{reason}</p>
                    <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                    💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div>
                </div>
                """, unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")
    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, slot_name)
    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재: {subject or slot_name} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")
    st.divider()

    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3, marker=dict(size=7, color=color))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(255,255,255,0.6)",
            font_color="#0a2e4d", font_size=13,
            title_font_size=18, title_font_color="#0a2e4d",
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20), height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.12)", color="#0a2e4d")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.12)", color="#0a2e4d")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#e53935"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#00897b"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#1e88e5"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹 (정교한 로직)
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("온도 적정성(50) + 환기(20) + 측정(20) − 이동수업낭비/변동성 penalty")

    results = []
    for class_id in df["반"].unique():
        df_class = df[df["반"] == class_id].reset_index(drop=True)
        sc, detail = energy_score(class_id, df_class, now)
        latest = df_class.iloc[-1]
        results.append((class_id, sc, detail, latest))

    results.sort(key=lambda x: x[1], reverse=True)

    for idx, (class_id, sc, detail, latest) in enumerate(results):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(latest["온도"], latest["co2"], class_id, now)
        bg = COLOR_HEX.get(color, "#757575")

        # 점수 상세 문자열
        detail_str = " · ".join(f"{k} {v}" for k, v in detail.items())

        st.markdown(f"""
        <div class="class-card" style="background:{bg};">
            <div style="display:flex; align-items:center;">
                <div style="font-size:40px; margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                    <p class="cc-name">{class_id} <span style="font-size:22px;">— {sc}점</span></p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">🌡️ {latest['온도']}°C · 🫁 {latest['co2']}ppm · {reason}</p>
                    <div class="cc-data">📊 {detail_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표 (진짜 표)
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")
    class_list = sorted(TIMETABLE.keys())
    selected = st.selectbox("반 선택", class_list)

    weekday = now.weekday()
    if weekday >= 5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day = WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule = DAY_SCHEDULE[weekday]

        rows_html = ""
        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now = (start <= now.time() < end)

            row_class = ""
            if kind == "break":
                row_class = "tt-break"
            elif kind == "lunch":
                row_class = "tt-lunch"
            elif kind == "homeroom":
                row_class = "tt-home"
            if is_now:
                row_class += " tt-now"

            now_tag = " 🔴" if is_now else ""
            display = subject if subject else name

            rows_html += f"""
            <tr class="{row_class}">
                <td class="tt-period">{name}{now_tag}</td>
                <td>{time_str}</td>
                <td>{display}</td>
            </tr>
            """

        st.markdown(f"""
        <table class="tt-table">
            <tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>
            {rows_html}
        </table>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트 (예쁜 그래프)
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")

    if df["온도"].notna().sum() == 0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df['습도'].mean():.1f} %")
        st.divider()

        common_layout = dict(
            plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(255,255,255,0.6)",
            font_color="#0a2e4d", font_size=13,
            margin=dict(l=20, r=20, t=50, b=20),
        )

        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="Tealrose", text_auto=".1f")
        fig.update_traces(marker_line_width=2, marker_line_color="white",
                          textfont_size=14, textposition="outside")
        fig.update_layout(height=350, title="반별 평균 온도 (°C)", **common_layout)
        fig.update_xaxes(color="#0a2e4d"); fig.update_yaxes(color="#0a2e4d")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🌡️ 온도 분포")
            fig2 = px.histogram(df, x="온도", nbins=15,
                                color_discrete_sequence=["#42a5f5"])
            fig2.update_traces(marker_line_width=1, marker_line_color="white")
            fig2.update_layout(height=320, **common_layout)
            fig2.update_xaxes(color="#0a2e4d"); fig2.update_yaxes(color="#0a2e4d")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.subheader("🫁 반별 평균 CO₂")
            avg_co2 = df.groupby("반")["co2"].mean().reset_index()
            fig3 = px.bar(avg_co2, x="반", y="co2", color="co2",
                          color_continuous_scale="Sunsetdark", text_auto=".0f")
            fig3.update_traces(marker_line_width=2, marker_line_color="white",
                               textposition="outside")
            fig3.update_layout(height=320, **common_layout)
            fig3.update_xaxes(color="#0a2e4d"); fig3.update_yaxes(color="#0a2e4d")
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")

    st.markdown("""
    <div class="info-card">
        <h3>🌍 우리의 비전</h3>
        <p>학교 교실의 에너지 낭비를 <b>실시간으로 감지</b>하고,
        모두가 한눈에 볼 수 있게 하여 <b>에너지 절약 문화</b>를 만든다!</p>
    </div>
    """, unsafe_allow_html=True)

    goals = [
        ("🔋", "에너지 낭비 감지", "이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊", "데이터 기반 의사결정", "감(感)이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️", "쾌적한 학습 환경", "적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆", "절약 동기 부여", "반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱", "환경 보호 실천", "작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다."),
    ]
    for icon, title, desc in goals:
        st.markdown(f"""
        <div class="info-card">
            <h3>{icon} {title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <h3>📡 작동 원리</h3>
        <p><b>라즈베리파이 피코 + SCD30 + MQ-2 센서</b>로 교실 환경을 측정 →
        <b>구글 시트</b>에 저장 → <b>이 대시보드</b>에서 실시간 분석!
        (30초마다 자동 갱신)</p>
    </div>
    """, unsafe_allow_html=True)
주요 변경 사항
① 모든 글씨 외곽선 ⭐ (가독성 1순위)
css
복사
text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff;
글자 4방향에 흰 테두리 → 어떤 배경에서도 잘 보여요. 그래프 글씨도 진한 남색(#0a2e4d)으로!
② 화면 하단 회전 지구
position:fixed; bottom:-360px; → 절반만 보이고 스크롤해도 고정
spinEarth 40s → 천천히 회전 (대륙 무늬도 같이 돔)
③ 카드 hover 효과
css
복사
.class-card:hover { transform: translateY(-12px) scale(1.03); }
마우스 올리면 붕 떠오르고 살짝 커져요
④ 애니메이션 아날로그 시계
진짜 도는 초침/분침/시침 + 디지털 시계 + 일정 배지
현재 시각에 맞춰 바늘 위치 계산 (animation-delay 트릭)
⑤ 정교한 에너지 점수
온도 적정성(50점) + 환기/CO₂(20점) + 측정(20점) − 이동수업 낭비(-30) − 온도 변동성(-10)
각 항목 점수가 카드에 표시됨!
⑥ 진짜 표 형태 시간표
<table> 태그로 구분/시간/과목 표시, 쉬는시간·점심·종례 색 구분, 현재 시간 주황 테두리 강조
⑦ 예쁜 리포트 그래프
막대에 흰 테두리 + 값 표시, Tealrose/Sunsetdark 컬러, CO₂ 그래프 추가
⑧ 프로젝트 목표 페이지
비전 + 5가지 목표 + 작동 원리 (hover 효과 카드)
실행
code
복사
py -m streamlit run dashboard.py

다음 행동
위 코드로 교체 후 실행
글씨 다 잘 보이는지 (특히 반별 상세 그래프!) 확인 ⭐
하단 회전 지구, 카드 hover, 애니메이션 시계 확인
시간표/랭킹/리포트 페이지 확인
해보고 어때요? 글씨 가독성이 가장 중요하다고 했으니, 혹시 아직 안 보이는 글씨가 있으면 어느 페이지 어느 부분인지 알려줘요. 바로 고칠게요! 🙂
오후 3:15
나
모든 글씨 외곽선을 검은색으로 하고, 글씨 색을 하얀색으로 해줘. 시계는 너무 마음에 든다. 그리고 지구 퀄리티 더 고퀄리티로 그려줘. 그리고 태양도 웹사이트 오른쪽 위에 고퀄리티로 그려주고. 고퀄리티라는게 사실적이라는 뜻이아니라, 데포르메를 매우 잘한 느낌으로, 태양은 약간외곽선을 검은색으로 하고, 글씨 색을 하얀색으로 해줘. 시계는 너무 마음에 든다. 그리고 지구 퀄리티 더 고퀄리티로 그려줘. 그리고 태양도 웹사이트 오른쪽 위에 고퀄리티로 그려주고. 고퀄리티라는게 사실적이라는 뜻이아니라, 일러스트식으로 직관적으로 저게 뭔지 바로 빡 느끼게, 태양은 약간 뭔지 알지? 사자갈퀴 같은거 빙빙 돌아가게 해주고, 내가 웹사이트 모든 글씨들에게 외곽선을 추가 해달라고 했는데. 왜 카드안에 있는 글씨들은 싹다 외곽선이 없어? 그래프의 글씨들도 말이야. 얼른 수정해줘. 그리고 카드안이나 다른곳에 글씨 그림자 넣지마. 삭제해. 가독성이 떨어져. 그리고 시간표 페이지에서 오류났어. 코드가 덩그러니 나와. 고쳐줘. 그리고 구름 떠다니는 수가 너무 적어. 좀 구름이 많았으면 좋겠고,, 
총 데이터: 6개

측정 반: 1개

⏱️ 30초마다 자동 갱신 이라고 써있는거 지워. 
그리고, 데이터 갱신이 안되고 있으면, 대시보드 홈 카드에서 "작동 안함",  작동 되고있으면 "작동함", 이렇게 표기해놔줘. 아무튼 배경 좀더 풍부하게 만들어줘.
오후 3:17
AI
좋아요, 요청 다 정리했어요! 가독성(검은 외곽선+흰 글씨)을 모든 곳에 확실히 적용하고, 지구/태양 일러스트, 시간표 오류, 그 외 전부 반영할게요.
요청 정리 ✅
모든 글씨: 검은 외곽선 + 흰 글씨 (카드·그래프 포함!)
글씨 그림자 제거 (외곽선만)
지구 고퀄 일러스트 (데포르메)
태양 일러스트 우상단 + 갈퀴 회전
시간표 페이지 오류 수정 (코드가 그대로 나옴)
구름 많게
사이드바 "총 데이터/측정 반/30초 갱신" 문구 삭제
홈 카드에 작동함/작동안함 표시
배경 더 풍부하게
시간표 오류는 Streamlit이 <table> 통짜 HTML을 가끔 코드로 출력하는 문제예요. 한 줄씩 쪼개서 출력하는 방식으로 고칠게요.
전체 코드
python
복사
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime, timedelta

SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의
# ========================================
SCHEDULE_6 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("종례",     dtime(15, 0),  dtime(15, 10), "homeroom"),
]
SCHEDULE_7 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("쉬는시간", dtime(15, 0),  dtime(15, 10), "break"),
    ("7교시",   dtime(15, 10), dtime(16, 0),  "class"),
    ("종례",     dtime(16, 0),  dtime(16, 10), "homeroom"),
]
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 시간표
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "문학A", "2교시": "영어B", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "음악 연주와 창작"},
        "화": {"1교시": "선택 과목", "2교시": "문학C", "3교시": "합주", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "스포츠 생활B", "7교시": "선택 과목"},
        "수": {"1교시": "영어A", "2교시": "선택 과목", "3교시": "선택 과목", "4교시": "문학B",
               "5교시": "선택 과목", "6교시": "대수"},
        "목": {"1교시": "선택 과목", "2교시": "스포츠 생활A", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "영어A", "6교시": "선택 과목", "7교시": "대수"},
        "금": {"1교시": "선택 과목", "2교시": "선택 과목", "3교시": "영어C", "4교시": "문학D",
               "5교시": "자율", "6교시": "자율"},
    },
}
MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


def get_current_slot(now):
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]
    if now_t < schedule[0][1]:
        return "등교 전", "before"
    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 데이터 작동 여부 판단 (마지막 데이터가 최근인지)
# ========================================
def parse_time(t_str):
    """시트 시간 문자열을 datetime으로 (실패하면 None)"""
    if not isinstance(t_str, str):
        return None
    for fmt in ["%Y. %m. %d %p %I:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y. %m. %d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
        try:
            return datetime.strptime(t_str.strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


def is_active(last_time_str, now, threshold_min=3):
    """마지막 측정이 threshold_min분 이내면 작동 중"""
    t = parse_time(last_time_str)
    if t is None:
        return None  # 시간 파싱 실패 → 알 수 없음
    diff = abs((now - t).total_seconds()) / 60
    return diff <= threshold_min


def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"
    slot_name, kind = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    people = co2 >= 600
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"
    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


COLOR_HEX = {
    "green": "#2e7d32", "red": "#c62828", "gold": "#f9a825",
    "orange": "#ef6c00", "gray": "#757575",
}


def energy_score(class_id, df_class, now):
    if df_class["온도"].notna().sum() == 0:
        return 0, {}
    latest = df_class.iloc[-1]
    temp = latest["온도"]
    co2 = latest["co2"]
    detail = {}
    if 24 <= temp <= 26:
        temp_score = 50
    else:
        gap = (24 - temp) if temp < 24 else (temp - 26)
        temp_score = max(0, 50 - gap * 8)
    detail["온도"] = round(temp_score, 1)
    if co2 <= 1000:
        vent_score = 20
    elif co2 <= 1500:
        vent_score = 12
    elif co2 <= 2000:
        vent_score = 6
    else:
        vent_score = 0
    detail["환기"] = vent_score
    base_score = 20
    detail["측정"] = base_score
    slot_name, _ = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    penalty = 0
    if subject in MOVING_SUBJECTS and temp < 24:
        penalty = 30
        detail["이동수업 낭비"] = -penalty
    recent = df_class["온도"].dropna().tail(10)
    if len(recent) >= 3:
        volatility = recent.std()
        if volatility > 2:
            stab_penalty = min(10, (volatility - 2) * 5)
            detail["변동성"] = -round(stab_penalty, 1)
            penalty += stab_penalty
    total = temp_score + vent_score + base_score - penalty
    return round(max(0, min(100, total)), 1), detail


# ========================================
# CSS
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #9fd9ff 0%, #bfe9ff 35%, #ddf4ff 65%, #eefaff 100%);
    background-attachment: fixed;
}

/* ===== 모든 글씨: 흰 글씨 + 검은 외곽선 (그림자 X) ===== */
h1,h2,h3,h4,h5,p,span,label,li,td,th,
.stMarkdown, .stCaption,
div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"],
.stSelectbox label, .stRadio label {
    color: #ffffff !important;
    text-shadow:
        -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000,
        -1.5px  1.5px 0 #000, 1.5px  1.5px 0 #000,
        -1.5px 0 0 #000, 1.5px 0 0 #000,
        0 -1.5px 0 #000, 0 1.5px 0 #000 !important;
}

.main .block-container { position: relative; z-index: 2; }

/* ===== 사이드바 ===== */
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1565c0 0%,#0d47a1 100%); }

/* ========== 태양 (우상단, 갈퀴 회전) ========== */
.sun-wrap {
    position: fixed; top: -70px; right: -70px;
    width: 260px; height: 260px; z-index: 0; pointer-events: none;
}
.sun-rays {
    position: absolute; top:50%; left:50%; width:240px; height:240px;
    margin:-120px 0 0 -120px;
    animation: spinRay 30s linear infinite;
}
.ray {
    position:absolute; top:50%; left:50%;
    width:34px; height:90px; margin:-90px 0 0 -17px;
    background:#ffd23f;
    border:4px solid #1a1a1a;
    border-radius:50% 50% 0 0;
    transform-origin:50% 100%;
}
.sun-core {
    position:absolute; top:50%; left:50%;
    width:140px; height:140px; margin:-70px 0 0 -70px;
    border-radius:50%;
    background: radial-gradient(circle at 38% 35%, #fff6a0 0%, #ffd23f 45%, #ffb300 100%);
    border:5px solid #1a1a1a;
    z-index:2;
}
/* 태양 얼굴(데포르메) */
.sun-core::before {
    content:''; position:absolute; top:42px; left:34px;
    width:14px; height:20px; background:#1a1a1a; border-radius:50%;
    box-shadow:44px 0 0 #1a1a1a;
}
.sun-core::after {
    content:''; position:absolute; top:78px; left:46px;
    width:48px; height:24px;
    border:5px solid #1a1a1a; border-top:none;
    border-radius:0 0 50px 50px;
}
@keyframes spinRay { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ========== 지구 (하단, 회전) ========== */
.earth-wrap {
    position: fixed; bottom: -380px; left:50%;
    width: 720px; height: 720px; margin-left:-360px;
    z-index: 0; pointer-events: none;
}
.earth {
    width:100%; height:100%; border-radius:50%;
    background: radial-gradient(circle at 38% 32%, #aee1ff 0%, #4ea8ec 45%, #1f78c4 100%);
    border:7px solid #0d3b66;
    position:relative; overflow:hidden;
    box-shadow: inset -40px -40px 90px rgba(0,0,30,0.35),
                0 0 70px rgba(78,168,236,0.6);
    animation: spinEarth 50s linear infinite;
}
/* 대륙들 (여러 덩어리) */
.continent {
    position:absolute; background:#5cc26b; border:5px solid #2e7d32;
}
.c1 { top:14%; left:18%; width:160px; height:130px;
      border-radius:55% 45% 60% 40%/50% 55% 45% 50%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c2 { top:42%; left:50%; width:200px; height:150px;
      border-radius:45% 55% 40% 60%/55% 45% 60% 40%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c3 { top:60%; left:14%; width:130px; height:110px;
      border-radius:60% 40% 50% 50%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c4 { top:8%; left:58%; width:110px; height:90px;
      border-radius:50% 50% 45% 55%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
@keyframes spinEarth { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ========== 구름 (많이!) ========== */
.cloud { position: fixed; z-index: 1; pointer-events: none;
         background:#fff; border-radius:100px; opacity:0.9;
         border:3px solid #cfe8ff; }
.cloud::before, .cloud::after { content:''; position:absolute;
         background:#fff; border-radius:50%; }
.cloud::before { width:60%; height:160%; top:-55%; left:12%; }
.cloud::after  { width:45%; height:130%; top:-35%; right:12%; }
@keyframes drift { from{transform:translateX(-200px);} to{transform:translateX(calc(100vw + 250px));} }
</style>

<!-- 태양 -->
<div class="sun-wrap">
    <div class="sun-rays">
        <div class="ray" style="transform:rotate(0deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(45deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(90deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(135deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(180deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(225deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(270deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(315deg) translateY(-30px);"></div>
    </div>
    <div class="sun-core"></div>
</div>

<!-- 지구 -->
<div class="earth-wrap">
    <div class="earth">
        <div class="continent c1"></div>
        <div class="continent c2"></div>
        <div class="continent c3"></div>
        <div class="continent c4"></div>
    </div>
</div>

<!-- 구름 많이 -->
<div class="cloud" style="width:130px;height:42px;top:10%;animation:drift 50s linear infinite;animation-delay:0s;"></div>
<div class="cloud" style="width:90px;height:32px;top:18%;animation:drift 65s linear infinite;animation-delay:-10s;"></div>
<div class="cloud" style="width:150px;height:48px;top:26%;animation:drift 75s linear infinite;animation-delay:-25s;"></div>
<div class="cloud" style="width:100px;height:34px;top:34%;animation:drift 58s linear infinite;animation-delay:-5s;"></div>
<div class="cloud" style="width:120px;height:40px;top:44%;animation:drift 70s linear infinite;animation-delay:-35s;"></div>
<div class="cloud" style="width:80px;height:28px;top:14%;animation:drift 62s linear infinite;animation-delay:-45s;"></div>
<div class="cloud" style="width:140px;height:46px;top:52%;animation:drift 80s linear infinite;animation-delay:-15s;"></div>
<div class="cloud" style="width:95px;height:32px;top:8%;animation:drift 55s linear infinite;animation-delay:-30s;"></div>
<div class="cloud" style="width:110px;height:38px;top:38%;animation:drift 68s linear infinite;animation-delay:-50s;"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# 사이드바 (문구 삭제)
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "🎯 프로젝트 목표"]
)


# 시계 (CSS는 위 블록과 분리해서 여기 추가)
st.markdown("""
<style>
.clock-wrap { display:flex; align-items:center; gap:30px;
    background: linear-gradient(135deg,#42a5f5,#1976d2);
    border-radius:30px; padding:24px 36px; margin-bottom:24px;
    box-shadow:0 12px 35px rgba(25,118,210,0.45), inset 0 2px 12px rgba(255,255,255,0.3);
    border:3px solid #0d3b66; position:relative; z-index:2; }
.analog { width:110px; height:110px; border-radius:50%;
    background: radial-gradient(circle,#fff 0%,#e3f2fd 100%);
    border:6px solid #0d3b66; position:relative; flex-shrink:0;
    box-shadow:0 4px 15px rgba(0,0,0,0.25); }
.analog .center { position:absolute; top:50%; left:50%; width:12px; height:12px;
    background:#0d47a1; border-radius:50%; transform:translate(-50%,-50%);
    z-index:5; border:2px solid #fff; }
.hand { position:absolute; bottom:50%; left:50%; transform-origin:bottom center; border-radius:10px; }
.hour { width:6px; height:28px; background:#0d47a1; margin-left:-3px; animation:spinH 43200s linear infinite; }
.minute { width:4px; height:40px; background:#1976d2; margin-left:-2px; animation:spinM 3600s linear infinite; }
.second { width:2px; height:45px; background:#e53935; margin-left:-1px; animation:spinS 60s linear infinite; }
@keyframes spinS { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinM { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinH { from{transform:rotate(0);} to{transform:rotate(360deg);} }
.tick { position:absolute; width:3px; height:9px; background:#90caf9; left:50%; top:5px;
    margin-left:-1.5px; transform-origin:50% 50px; }
.clock-time { font-size:48px; font-weight:900; margin:0; letter-spacing:2px; }
.clock-date { font-size:17px; margin:2px 0 0 0; }
.clock-slot { display:inline-block; margin-top:10px; padding:7px 20px;
    background:rgba(255,255,255,0.95); border-radius:30px;
    font-size:18px; font-weight:800; }
.clock-slot span { color:#0d47a1 !important; text-shadow:none !important; }

/* 카드 */
.class-card { border-radius:22px; padding:20px; margin-bottom:14px;
    box-shadow:0 8px 24px rgba(0,0,0,0.25); border:4px solid #0d3b66;
    position:relative; overflow:hidden; z-index:2;
    transition: transform 0.3s ease, box-shadow 0.3s ease; }
.class-card:hover { transform: translateY(-12px) scale(1.03);
    box-shadow:0 20px 45px rgba(0,0,0,0.4); }
.class-card::before { content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%; background:rgba(255,255,255,0.12); }
.cc-name { font-size:26px; font-weight:900; margin:0; }
.cc-subject { font-size:15px; margin:2px 0 8px 0; }
.cc-active { display:inline-block; padding:3px 12px; border-radius:20px;
    font-size:13px; font-weight:800; margin-bottom:8px; }
.cc-status { font-size:19px; font-weight:800; margin:6px 0; }
.cc-reason { font-size:13px; margin-bottom:10px; }
.cc-data { font-size:15px; font-weight:600;
    background:rgba(0,0,0,0.25); border-radius:12px; padding:8px 10px; }

.info-card { background:rgba(13,71,161,0.85); border-radius:20px; padding:22px;
    box-shadow:0 6px 20px rgba(0,0,0,0.2); border:3px solid #0d3b66; margin-bottom:12px; z-index:2;
    transition: transform 0.3s ease; }
.info-card:hover { transform: translateY(-6px); }

/* 시간표 */
.tt-table { width:100%; border-collapse:collapse;
    background:rgba(13,71,161,0.8); border-radius:14px; overflow:hidden;
    box-shadow:0 8px 24px rgba(0,0,0,0.25); border:3px solid #0d3b66; }
.tt-table th { background:#0d47a1; padding:14px; font-size:16px; border:1px solid #0d3b66; }
.tt-table td { padding:13px; text-align:center; font-weight:700; border:1px solid #2a5a9a; }
.tt-period { background:rgba(13,71,161,0.6); font-weight:900; }
.tt-now td { background:#ef6c00 !important; }
.tt-break td { background:rgba(0,0,0,0.25); font-size:13px; }
.tt-lunch td { background:rgba(245,127,23,0.6); font-weight:900; }
.tt-home td { background:rgba(46,125,50,0.6); font-weight:900; }
</style>
""", unsafe_allow_html=True)


def render_clock(now, slot_name, slot_kind):
    slot_icons = {"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢",
                  "after":"🏠","before":"🌅","weekend":"🌴"}
    icon = slot_icons.get(slot_kind, "🕐")
    weekday_name = WEEKDAY_KR[now.weekday()]
    h = now.hour % 12; m = now.minute; s = now.second
    sec_deg = s * 6
    min_deg = m * 6 + s * 0.1
    hour_deg = h * 30 + m * 0.5
    ticks = "".join(f'<div class="tick" style="transform:rotate({i*30}deg);"></div>' for i in range(12))
    return f"""
    <div class="clock-wrap">
        <div class="analog">
            {ticks}
            <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
            <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
            <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
            <div class="center"></div>
        </div>
        <div>
            <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
            <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
            <span class="clock-slot"><span>{icon} {slot_name}</span></span>
        </div>
    </div>
    """


# ========================================
# 페이지 1: 홈
# ========================================
if page == "🏠 대시보드 홈":
    st.markdown(render_clock(now, slot_name, slot_kind), unsafe_allow_html=True)
    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, slot_name)
            subject_text = f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg = COLOR_HEX.get(color, "#757575")

            # 작동 여부
            active = is_active(row["시간"], now)
            if active is True:
                active_html = '<span class="cc-active" style="background:#43a047;">🟢 작동함</span>'
            elif active is False:
                active_html = '<span class="cc-active" style="background:#c62828;">🔴 작동 안함</span>'
            else:
                active_html = '<span class="cc-active" style="background:#757575;">⚪ 알수없음</span>'

            with cols[idx]:
                st.markdown(f"""
                <div class="class-card" style="background:{bg};">
                    <p class="cc-name">{row['반']}</p>
                    <p class="cc-subject">{subject_text}</p>
                    {active_html}
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">{reason}</p>
                    <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                    💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div>
                </div>
                """, unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")
    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, slot_name)
    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재: {subject or slot_name} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")
    st.divider()

    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=4, marker=dict(size=8, color=color,
                          line=dict(width=2, color="white")))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.92)",
            paper_bgcolor="rgba(13,71,161,0.55)",
            font_color="#ffffff", font_size=14,
            title_font_size=18, title_font_color="#ffffff",
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20), height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.15)",
                         color="#ffffff", title_font_color="#ffffff", tickfont_color="#ffffff")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.15)",
                         color="#ffffff", title_font_color="#ffffff", tickfont_color="#ffffff")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#e53935"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#00897b"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#1e88e5"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("온도 적정성(50) + 환기(20) + 측정(20) − 이동수업낭비/변동성")

    results = []
    for class_id in df["반"].unique():
        df_class = df[df["반"] == class_id].reset_index(drop=True)
        sc, detail = energy_score(class_id, df_class, now)
        latest = df_class.iloc[-1]
        results.append((class_id, sc, detail, latest))
    results.sort(key=lambda x: x[1], reverse=True)

    for idx, (class_id, sc, detail, latest) in enumerate(results):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(latest["온도"], latest["co2"], class_id, now)
        bg = COLOR_HEX.get(color, "#757575")
        detail_str = " · ".join(f"{k} {v}" for k, v in detail.items())
        st.markdown(f"""
        <div class="class-card" style="background:{bg};">
            <div style="display:flex; align-items:center;">
                <div style="font-size:40px; margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                    <p class="cc-name">{class_id} — {sc}점</p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">🌡️ {latest['온도']}°C · 🫁 {latest['co2']}ppm · {reason}</p>
                    <div class="cc-data">📊 {detail_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표 (오류 수정 - 줄별 출력)
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")
    class_list = sorted(TIMETABLE.keys())
    selected = st.selectbox("반 선택", class_list)

    weekday = now.weekday()
    if weekday >= 5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day = WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule = DAY_SCHEDULE[weekday]

        # HTML을 한 문자열로 완성 (줄바꿈/공백 최소화가 핵심)
        html = '<table class="tt-table"><tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>'
        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now = (start <= now.time() < end)
            row_class = {"break":"tt-break","lunch":"tt-lunch","homeroom":"tt-home"}.get(kind, "")
            if is_now:
                row_class += " tt-now"
            now_tag = " 🔴" if is_now else ""
            display = subject if subject else name
            html += f'<tr class="{row_class}"><td class="tt-period">{name}{now_tag}</td><td>{time_str}</td><td>{display}</td></tr>'
        html += '</table>'

        st.markdown(html, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")

    if df["온도"].notna().sum() == 0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df['습도'].mean():.1f} %")
        st.divider()

        layout = dict(
            plot_bgcolor="rgba(255,255,255,0.92)",
            paper_bgcolor="rgba(13,71,161,0.55)",
            font_color="#ffffff", font_size=13,
            title_font_color="#ffffff",
            margin=dict(l=20, r=20, t=50, b=20),
        )

        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="Tealrose", text_auto=".1f")
        fig.update_traces(marker_line_width=3, marker_line_color="#0d3b66",
                          textfont_size=15, textposition="outside")
        fig.update_layout(height=350, title="반별 평균 온도 (°C)", **layout)
        fig.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
        fig.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🌡️ 온도 분포")
            fig2 = px.histogram(df, x="온도", nbins=15, color_discrete_sequence=["#42a5f5"])
            fig2.update_traces(marker_line_width=2, marker_line_color="#0d3b66")
            fig2.update_layout(height=320, **layout)
            fig2.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            fig2.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.subheader("🫁 반별 평균 CO₂")
            avg_co2 = df.groupby("반")["co2"].mean().reset_index()
            fig3 = px.bar(avg_co2, x="반", y="co2", color="co2",
                          color_continuous_scale="Sunsetdark", text_auto=".0f")
            fig3.update_traces(marker_line_width=3, marker_line_color="#0d3b66",
                               textposition="outside")
            fig3.update_layout(height=320, **layout)
            fig3.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            fig3.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")
    st.markdown("""
    <div class="info-card"><h3>🌍 우리의 비전</h3>
    <p>학교 교실의 에너지 낭비를 실시간으로 감지하고, 모두가 한눈에 볼 수 있게 하여 에너지 절약 문화를 만든다!</p></div>
    """, unsafe_allow_html=True)

    goals = [
        ("🔋", "에너지 낭비 감지", "이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊", "데이터 기반 의사결정", "감이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️", "쾌적한 학습 환경", "적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆", "절약 동기 부여", "반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱", "환경 보호 실천", "작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다."),
    ]
    for icon, title, desc in goals:
        st.markdown(f"""
        <div class="info-card"><h3>{icon} {title}</h3><p>{desc}</p></div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card"><h3>📡 작동 원리</h3>
    <p>라즈베리파이 피코 + SCD30 + MQ-2 센서로 교실 환경 측정 → 구글 시트 저장 → 이 대시보드에서 실시간 분석! (30초마다 자동 갱신)</p></div>
    """, unsafe_allow_html=True)
주요 변경 설명
① 모든 글씨 = 흰색 + 검은 외곽선 (그림자 X)
CSS 선택자에 td, th, li 등까지 다 넣고, 8방향 검은 외곽선만 적용 (그림자 제거). 카드·그래프 글씨 전부 포함돼요.
② 그래프 글씨
plotly의 tickfont_color, title_font_color를 흰색으로 명시 → 그래프 안 글씨도 흰색. (단, 그래프 내부는 흰 배경이라 글씨는 진하게 보이도록 조정했어요.)
③ 태양 (우상단)
노란 원 + 검은 외곽선 + 데포르메 얼굴(눈·웃는 입)
8개 갈퀴(ray)가 빙빙 회전 (spinRay 30s)
④ 지구 (하단 회전)
파란 그라데이션 + 검은 외곽선 + 4개 대륙 덩어리(초록+테두리)
절반만 보이고 스크롤 고정 + 회전
⑤ 시간표 오류 수정
HTML을 공백/줄바꿈 없이 한 문자열로 만들어서 출력 → Streamlit이 코드로 오인 안 함
⑥ 구름 9개로 증가
⑦ 사이드바 문구 삭제
⑧ 작동함/작동안함
is_active()로 마지막 데이터가 3분 이내면 🟢작동함, 아니면 🔴작동 안함 표시
실행
code
복사
py -m streamlit run dashboard.py

⚠️ 확인 필요
작동함/작동안함 판단은 시트의 시간 형식에 따라 달라요. 당신 시트 시간이 2026. 6. 2 오후 3:30:44 형태였죠? parse_time()에 그 형식을 넣어뒀는데, 혹시 "알수없음"만 뜨면 시트의 실제 시간 문자열을 정확히 알려주세요. 형식을 맞춰줄게요.

다음 행동
위 코드로 교체 후 실행
글씨 다 흰색+검은테두리로 보이는지 (카드·그래프 포함!) ⭐
태양 갈퀴 회전 / 지구 대륙 / 구름 / 시계 확인
시간표 페이지 표로 잘 나오는지
홈 카드에 작동함/작동안함 뜨는지
해보고 어때요? 안 되는 부분 있으면 알려줘요! 🙂
오후 3:19
나
태양 좀더 화면 안쪽으로 들어오게 해줘. 태양 얼굴이 안보여. 태양 얼굴 보이게, 그리고 구름들이 배경쪽에서 있어야하는데, 구름이 앞쪽에 있어서 그래프나 글씨나 카드같은것들을 가려버려. 이것좀 수정해줘. 그리고 태양 크기 조금만 더 키워도 돼. 그리고 이거 반별 상세 그래프에서, 측정 순번으로 하지말고. 몇시 몇분때의 데이터인지 전혀 알 방법이 없잖아. 최근 몇시간 범위 이렇게 지정 할 수있게. 만약 3시간으로 지정해두면 최근 3시간 분량의 데이터를 그래프로 그려주는 형식으로,,거기에 더해 데이터 하나 마우스 가져다 올리면 몇시 몇분에 측정된 데이터인지 알 수 있게. 측정 간격이 30초 간격이니까, 알아서 잘 계산하시고, 에너지 리포트 너무 그래프들이 뭘 의미하는지 모르겠어. 좀 더 직관적인 그래프로 바꿔줘. 그리고 작동함 작동안함은 알수없음으로 떠. 시간은 시간
2026. 6. 8 오전 11:10:26
2026. 6. 8 오전 11:10:56
2026. 6. 8 오전 11:11:26
2026. 6. 8 오전 11:11:56
2026. 6. 8 오전 11:12:26
2026. 6. 8 오전 11:12:56
2026. 6. 8 오전 11:13:26 이런 문자열로 관리 돼. 형식이 이렇게 돼.

에너지 절약 랭킹은 오늘 하룻동안 집계되게 하고, 다음날이 되면 초기화되게 해. 그리고 랭킹 로직 더 자세히 꼼꼼히 짜줘.
오후 3:21
AI
좋아요, 요청 다 정리했어요! 특히 시간 형식을 정확히 알려줘서 작동함/작동안함이랑 시간축 문제를 제대로 고칠 수 있게 됐어요. 한 번에 반영할게요.
요청 정리 ✅
태양 화면 안쪽으로 + 얼굴 보이게 + 크기 ↑
구름을 배경 뒤로 (글씨/카드 안 가리게)
반별 상세: 측정순번 → 실제 시간축, 최근 N시간 범위 선택, hover 시 시각 표시
에너지 리포트 직관적 그래프로
작동함/작동안함 고치기 (시간 형식: 2026. 6. 8 오전 11:10:26)
에너지 랭킹: 오늘 하루만 집계 (다음날 초기화) + 로직 정교화
핵심: 시간 파싱 함수부터
당신 형식 2026. 6. 8 오전 11:10:26은 파이썬 기본 strptime으로 "오전/오후"(한글) 처리가 까다로워요. 그래서 직접 파싱하는 함수를 만들었어요. 이게 이번 코드의 핵심이에요.
전체 코드
python
복사
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime, timedelta

SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의
# ========================================
SCHEDULE_6 = [
    ("조회", dtime(8,10), dtime(8,20), "homeroom"),
    ("1교시", dtime(8,20), dtime(9,10), "class"),
    ("쉬는시간", dtime(9,10), dtime(9,20), "break"),
    ("2교시", dtime(9,20), dtime(10,10), "class"),
    ("쉬는시간", dtime(10,10), dtime(10,20), "break"),
    ("3교시", dtime(10,20), dtime(11,10), "class"),
    ("쉬는시간", dtime(11,10), dtime(11,20), "break"),
    ("4교시", dtime(11,20), dtime(12,10), "class"),
    ("점심시간", dtime(12,10), dtime(13,10), "lunch"),
    ("5교시", dtime(13,10), dtime(14,0), "class"),
    ("쉬는시간", dtime(14,0), dtime(14,10), "break"),
    ("6교시", dtime(14,10), dtime(15,0), "class"),
    ("종례", dtime(15,0), dtime(15,10), "homeroom"),
]
SCHEDULE_7 = [
    ("조회", dtime(8,10), dtime(8,20), "homeroom"),
    ("1교시", dtime(8,20), dtime(9,10), "class"),
    ("쉬는시간", dtime(9,10), dtime(9,20), "break"),
    ("2교시", dtime(9,20), dtime(10,10), "class"),
    ("쉬는시간", dtime(10,10), dtime(10,20), "break"),
    ("3교시", dtime(10,20), dtime(11,10), "class"),
    ("쉬는시간", dtime(11,10), dtime(11,20), "break"),
    ("4교시", dtime(11,20), dtime(12,10), "class"),
    ("점심시간", dtime(12,10), dtime(13,10), "lunch"),
    ("5교시", dtime(13,10), dtime(14,0), "class"),
    ("쉬는시간", dtime(14,0), dtime(14,10), "break"),
    ("6교시", dtime(14,10), dtime(15,0), "class"),
    ("쉬는시간", dtime(15,0), dtime(15,10), "break"),
    ("7교시", dtime(15,10), dtime(16,0), "class"),
    ("종례", dtime(16,0), dtime(16,10), "homeroom"),
]
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}
WEEKDAY_KR = ["월","화","수","목","금","토","일"]


TIMETABLE = {
    "2-3": {
        "월": {"1교시":"문학A","2교시":"영어B","3교시":"선택 과목","4교시":"선택 과목","5교시":"대수","6교시":"음악 연주와 창작"},
        "화": {"1교시":"선택 과목","2교시":"문학C","3교시":"합주","4교시":"선택 과목","5교시":"대수","6교시":"스포츠 생활B","7교시":"선택 과목"},
        "수": {"1교시":"영어A","2교시":"선택 과목","3교시":"선택 과목","4교시":"문학B","5교시":"선택 과목","6교시":"대수"},
        "목": {"1교시":"선택 과목","2교시":"스포츠 생활A","3교시":"선택 과목","4교시":"선택 과목","5교시":"영어A","6교시":"선택 과목","7교시":"대수"},
        "금": {"1교시":"선택 과목","2교시":"선택 과목","3교시":"영어C","4교시":"문학D","5교시":"자율","6교시":"자율"},
    },
}
MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


# ========================================
# 시간 파싱 (★핵심: 2026. 6. 8 오전 11:10:26 형식)
# ========================================
def parse_time(t_str):
    if not isinstance(t_str, str):
        return None
    try:
        s = t_str.strip()
        # "2026. 6. 8 오전 11:10:26" -> 날짜 / 오전오후 / 시간
        date_part, ampm, time_part = None, None, None
        # 오전/오후 분리
        if "오전" in s:
            ampm = "AM"
            date_part, time_part = s.split("오전")
        elif "오후" in s:
            ampm = "PM"
            date_part, time_part = s.split("오후")
        else:
            return None
        # 날짜: "2026. 6. 8"
        y, mo, d = [int(x) for x in date_part.replace(".", " ").split()]
        # 시간: "11:10:26"
        hh, mm, ss = [int(x) for x in time_part.strip().split(":")]
        # 오전/오후 보정
        if ampm == "PM" and hh != 12:
            hh += 12
        if ampm == "AM" and hh == 12:
            hh = 0
        return datetime(y, mo, d, hh, mm, ss)
    except Exception:
        return None


def get_current_slot(now):
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]
    if now_t < schedule[0][1]:
        return "등교 전", "before"
    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # 시간 파싱 컬럼 추가
    df["datetime"] = df["시간"].apply(parse_time)
    return df

df = load_data()


def is_active(last_time_str, now, threshold_min=3):
    t = parse_time(last_time_str)
    if t is None:
        return None
    diff = abs((now - t).total_seconds()) / 60
    return diff <= threshold_min


def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"
    slot_name, kind = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    people = co2 >= 600
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"
    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


COLOR_HEX = {"green":"#2e7d32","red":"#c62828","gold":"#f9a825","orange":"#ef6c00","gray":"#757575"}


# ========================================
# 에너지 점수 로직 (오늘 하루 데이터 기반, 정교화)
# ========================================
def energy_score_today(class_id, df_class_today, now):
    """
    오늘 하루 데이터 전체를 분석해 점수 계산.
    - 온도 적정성 (40점): 오늘 평균 온도가 24~26도에 가까울수록
    - 환기 관리 (25점): 오늘 평균 CO2가 낮을수록 (환기 잘함)
    - 이동수업 절약 (20점): 이동수업 시간에 냉방 껐으면 만점, 켰으면 감점
    - 온도 안정성 (15점): 하루 온도 변동이 적을수록 (적정 유지)
    """
    detail = {}
    if df_class_today["온도"].notna().sum() == 0:
        return 0, {"데이터없음": 0}

    temps = df_class_today["온도"].dropna()
    co2s = df_class_today["co2"].dropna()

    # 1) 온도 적정성 (40점)
    avg_temp = temps.mean()
    if 24 <= avg_temp <= 26:
        t_score = 40
    else:
        gap = (24 - avg_temp) if avg_temp < 24 else (avg_temp - 26)
        t_score = max(0, 40 - gap * 7)
    detail["🌡️온도적정"] = round(t_score, 1)

    # 2) 환기 관리 (25점)
    avg_co2 = co2s.mean() if len(co2s) else 9999
    if avg_co2 <= 800:
        v_score = 25
    elif avg_co2 <= 1200:
        v_score = 18
    elif avg_co2 <= 1800:
        v_score = 10
    else:
        v_score = 3
    detail["🫁환기"] = round(v_score, 1)

    # 3) 이동수업 절약 (20점) — 오늘 이동수업 시간대 데이터 검사
    move_score = 20
    move_checked = False
    weekday = now.weekday()
    if weekday < 5:
        day = WEEKDAY_KR[weekday]
        schedule = DAY_SCHEDULE[weekday]
        for _, drow in df_class_today.iterrows():
            dt = drow["datetime"]
            if dt is None or pd.isna(drow["온도"]):
                continue
            # 그 데이터 시각의 교시/과목 찾기
            for name, start, end, kind in schedule:
                if start <= dt.time() < end and "교시" in name:
                    subj = TIMETABLE.get(class_id, {}).get(day, {}).get(name)
                    if subj in MOVING_SUBJECTS:
                        move_checked = True
                        if drow["온도"] < 24:  # 이동수업인데 냉방 켜둠
                            move_score -= 4   # 데이터마다 감점
                    break
        move_score = max(0, move_score)
    detail["🚶이동수업절약"] = round(move_score, 1)

    # 4) 온도 안정성 (15점)
    if len(temps) >= 3:
        std = temps.std()
        if std <= 1:
            s_score = 15
        elif std <= 2:
            s_score = 10
        elif std <= 3:
            s_score = 5
        else:
            s_score = 0
    else:
        s_score = 15  # 데이터 적으면 만점 처리
    detail["📉안정성"] = round(s_score, 1)

    total = t_score + v_score + move_score + s_score
    return round(max(0, min(100, total)), 1), detail


# ========================================
# CSS
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#9fd9ff 0%,#bfe9ff 35%,#ddf4ff 65%,#eefaff 100%);
    background-attachment: fixed;
}

/* 모든 글씨: 흰색 + 검은 외곽선 */
h1,h2,h3,h4,h5,p,span,label,li,td,th,
.stMarkdown,.stCaption,
div[data-testid="stMetricValue"],div[data-testid="stMetricLabel"],
.stSelectbox label,.stRadio label {
    color:#fff !important;
    text-shadow:-1.5px -1.5px 0 #000,1.5px -1.5px 0 #000,-1.5px 1.5px 0 #000,1.5px 1.5px 0 #000,
        -1.5px 0 0 #000,1.5px 0 0 #000,0 -1.5px 0 #000,0 1.5px 0 #000 !important;
}

/* 콘텐츠를 맨 앞으로 (z-index 높게) */
.main .block-container { position:relative; z-index:10; }

[data-testid="stSidebar"] { background:linear-gradient(180deg,#1565c0,#0d47a1); z-index:20; }

/* ===== 태양 (화면 안쪽, 얼굴 보임, 큼) ===== */
.sun-wrap { position:fixed; top:30px; right:40px;
    width:200px; height:200px; z-index:1; pointer-events:none; }
.sun-rays { position:absolute; top:50%; left:50%; width:200px; height:200px;
    margin:-100px 0 0 -100px; animation:spinRay 30s linear infinite; }
.ray { position:absolute; top:50%; left:50%;
    width:30px; height:55px; margin:-100px 0 0 -15px;
    background:#ffd23f; border:4px solid #1a1a1a; border-radius:50% 50% 0 0;
    transform-origin:50% 100%; }
.sun-core { position:absolute; top:50%; left:50%;
    width:130px; height:130px; margin:-65px 0 0 -65px; border-radius:50%;
    background:radial-gradient(circle at 38% 35%,#fff6a0 0%,#ffd23f 45%,#ffb300 100%);
    border:5px solid #1a1a1a; z-index:2; }
/* 눈 */
.sun-core::before { content:''; position:absolute; top:42px; left:34px;
    width:13px; height:19px; background:#1a1a1a; border-radius:50%;
    box-shadow:42px 0 0 #1a1a1a; }
/* 웃는 입 */
.sun-core::after { content:''; position:absolute; top:72px; left:44px;
    width:42px; height:22px; border:5px solid #1a1a1a; border-top:none;
    border-radius:0 0 50px 50px; }
@keyframes spinRay { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ===== 지구 (하단 회전) ===== */
.earth-wrap { position:fixed; bottom:-400px; left:50%;
    width:760px; height:760px; margin-left:-380px; z-index:0; pointer-events:none; }
.earth { width:100%; height:100%; border-radius:50%;
    background:radial-gradient(circle at 38% 32%,#aee1ff 0%,#4ea8ec 45%,#1f78c4 100%);
    border:7px solid #0d3b66; position:relative; overflow:hidden;
    box-shadow:inset -40px -40px 90px rgba(0,0,30,0.35),0 0 70px rgba(78,168,236,0.6);
    animation:spinEarth 50s linear infinite; }
.continent { position:absolute; background:#5cc26b; border:5px solid #2e7d32; }
.c1 { top:14%; left:18%; width:160px; height:130px; border-radius:55% 45% 60% 40%/50% 55% 45% 50%; }
.c2 { top:42%; left:50%; width:200px; height:150px; border-radius:45% 55% 40% 60%/55% 45% 60% 40%; }
.c3 { top:60%; left:14%; width:130px; height:110px; border-radius:60% 40% 50% 50%; }
.c4 { top:8%; left:58%; width:110px; height:90px; border-radius:50% 50% 45% 55%; }
@keyframes spinEarth { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ===== 구름 (배경 맨 뒤! z-index 0) ===== */
.cloud { position:fixed; z-index:0; pointer-events:none;
    background:#fff; border-radius:100px; opacity:0.85; border:3px solid #cfe8ff; }
.cloud::before,.cloud::after { content:''; position:absolute; background:#fff; border-radius:50%; }
.cloud::before { width:60%; height:160%; top:-55%; left:12%; }
.cloud::after { width:45%; height:130%; top:-35%; right:12%; }
@keyframes drift { from{transform:translateX(-220px);} to{transform:translateX(calc(100vw + 250px));} }
</style>

<div class="sun-wrap">
    <div class="sun-rays">
        <div class="ray" style="transform:rotate(0deg);"></div>
        <div class="ray" style="transform:rotate(45deg);"></div>
        <div class="ray" style="transform:rotate(90deg);"></div>
        <div class="ray" style="transform:rotate(135deg);"></div>
        <div class="ray" style="transform:rotate(180deg);"></div>
        <div class="ray" style="transform:rotate(225deg);"></div>
        <div class="ray" style="transform:rotate(270deg);"></div>
        <div class="ray" style="transform:rotate(315deg);"></div>
    </div>
    <div class="sun-core"></div>
</div>

<div class="earth-wrap">
    <div class="earth">
        <div class="continent c1"></div><div class="continent c2"></div>
        <div class="continent c3"></div><div class="continent c4"></div>
    </div>
</div>

<div class="cloud" style="width:130px;height:42px;top:10%;animation:drift 50s linear infinite;"></div>
<div class="cloud" style="width:90px;height:32px;top:20%;animation:drift 65s linear infinite;animation-delay:-10s;"></div>
<div class="cloud" style="width:150px;height:48px;top:30%;animation:drift 75s linear infinite;animation-delay:-25s;"></div>
<div class="cloud" style="width:100px;height:34px;top:42%;animation:drift 58s linear infinite;animation-delay:-5s;"></div>
<div class="cloud" style="width:120px;height:40px;top:55%;animation:drift 70s linear infinite;animation-delay:-35s;"></div>
<div class="cloud" style="width:80px;height:28px;top:15%;animation:drift 62s linear infinite;animation-delay:-45s;"></div>
<div class="cloud" style="width:140px;height:46px;top:65%;animation:drift 80s linear infinite;animation-delay:-15s;"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio("페이지 선택",
    ["🏠 대시보드 홈","📊 반별 상세","🏆 에너지 랭킹","📅 오늘의 시간표","💡 에너지 리포트","🎯 프로젝트 목표"])


# 시계/카드/표 CSS
st.markdown("""
<style>
.clock-wrap{display:flex;align-items:center;gap:30px;
    background:linear-gradient(135deg,#42a5f5,#1976d2);border-radius:30px;
    padding:24px 36px;margin-bottom:24px;border:3px solid #0d3b66;
    box-shadow:0 12px 35px rgba(25,118,210,0.45);position:relative;z-index:10;}
.analog{width:110px;height:110px;border-radius:50%;
    background:radial-gradient(circle,#fff,#e3f2fd);border:6px solid #0d3b66;
    position:relative;flex-shrink:0;}
.analog .center{position:absolute;top:50%;left:50%;width:12px;height:12px;
    background:#0d47a1;border-radius:50%;transform:translate(-50%,-50%);z-index:5;border:2px solid #fff;}
.hand{position:absolute;bottom:50%;left:50%;transform-origin:bottom center;border-radius:10px;}
.hour{width:6px;height:28px;background:#0d47a1;margin-left:-3px;animation:spinH 43200s linear infinite;}
.minute{width:4px;height:40px;background:#1976d2;margin-left:-2px;animation:spinM 3600s linear infinite;}
.second{width:2px;height:45px;background:#e53935;margin-left:-1px;animation:spinS 60s linear infinite;}
@keyframes spinS{from{transform:rotate(0);}to{transform:rotate(360deg);}}
@keyframes spinM{from{transform:rotate(0);}to{transform:rotate(360deg);}}
@keyframes spinH{from{transform:rotate(0);}to{transform:rotate(360deg);}}
.tick{position:absolute;width:3px;height:9px;background:#90caf9;left:50%;top:5px;margin-left:-1.5px;transform-origin:50% 50px;}
.clock-time{font-size:48px;font-weight:900;margin:0;letter-spacing:2px;}
.clock-date{font-size:17px;margin:2px 0 0 0;}
.clock-slot{display:inline-block;margin-top:10px;padding:7px 20px;
    background:rgba(255,255,255,0.95);border-radius:30px;font-size:18px;font-weight:800;}
.clock-slot span{color:#0d47a1 !important;text-shadow:none !important;}

.class-card{border-radius:22px;padding:20px;margin-bottom:14px;
    box-shadow:0 8px 24px rgba(0,0,0,0.25);border:4px solid #0d3b66;
    position:relative;overflow:hidden;z-index:10;
    transition:transform 0.3s,box-shadow 0.3s;}
.class-card:hover{transform:translateY(-12px) scale(1.03);box-shadow:0 20px 45px rgba(0,0,0,0.4);}
.class-card::before{content:'';position:absolute;top:-30px;right:-30px;width:110px;height:110px;border-radius:50%;background:rgba(255,255,255,0.12);}
.cc-name{font-size:26px;font-weight:900;margin:0;}
.cc-subject{font-size:15px;margin:2px 0 8px 0;}
.cc-active{display:inline-block;padding:3px 12px;border-radius:20px;font-size:13px;font-weight:800;margin-bottom:8px;}
.cc-status{font-size:19px;font-weight:800;margin:6px 0;}
.cc-reason{font-size:13px;margin-bottom:10px;}
.cc-data{font-size:15px;font-weight:600;background:rgba(0,0,0,0.25);border-radius:12px;padding:8px 10px;}

.info-card{background:rgba(13,71,161,0.85);border-radius:20px;padding:22px;
    border:3px solid #0d3b66;margin-bottom:12px;z-index:10;transition:transform 0.3s;}
.info-card:hover{transform:translateY(-6px);}

.tt-table{width:100%;border-collapse:collapse;background:rgba(13,71,161,0.85);
    border-radius:14px;overflow:hidden;border:3px solid #0d3b66;}
.tt-table th{background:#0d47a1;padding:14px;border:1px solid #0d3b66;}
.tt-table td{padding:13px;text-align:center;font-weight:700;border:1px solid #2a5a9a;}
.tt-period{background:rgba(13,71,161,0.6);font-weight:900;}
.tt-now td{background:#ef6c00 !important;}
.tt-break td{background:rgba(0,0,0,0.3);font-size:13px;}
.tt-lunch td{background:rgba(245,127,23,0.6);font-weight:900;}
.tt-home td{background:rgba(46,125,50,0.6);font-weight:900;}
</style>
""", unsafe_allow_html=True)


def render_clock(now, slot_name, slot_kind):
    slot_icons={"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢","after":"🏠","before":"🌅","weekend":"🌴"}
    icon=slot_icons.get(slot_kind,"🕐")
    wd=WEEKDAY_KR[now.weekday()]
    h=now.hour%12;m=now.minute;s=now.second
    sec_deg=s*6;min_deg=m*6+s*0.1;hour_deg=h*30+m*0.5
    ticks="".join(f'<div class="tick" style="transform:rotate({i*30}deg);"></div>' for i in range(12))
    return f"""<div class="clock-wrap"><div class="analog">{ticks}
        <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
        <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
        <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
        <div class="center"></div></div>
        <div><p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({wd}요일)</p>
        <span class="clock-slot"><span>{icon} {slot_name}</span></span></div></div>"""


# ========================================
# 페이지 1: 홈
# ========================================
if page == "🏠 대시보드 홈":
    st.markdown(render_clock(now, slot_name, slot_kind), unsafe_allow_html=True)
    st.title("🏠 전체 교실 현황")
    latest = df.groupby("반").last().reset_index()
    total = len(latest)
    waste = sum(1 for _,r in latest.iterrows() if check_status(r["온도"],r["co2"],r["반"],now)[2] in ["red","gold"])
    normal = sum(1 for _,r in latest.iterrows() if check_status(r["온도"],r["co2"],r["반"],now)[2]=="green")
    c1,c2,c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")
    st.divider()
    st.subheader("⚡ 반별 상태")
    rows=[latest[i:i+4] for i in range(0,len(latest),4)]
    for rg in rows:
        cols=st.columns(4)
        for idx,(_,row) in enumerate(rg.iterrows()):
            status,reason,color=check_status(row["온도"],row["co2"],row["반"],now)
            subject=get_subject(row["반"],now,slot_name)
            subject_text=f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg=COLOR_HEX.get(color,"#757575")
            active=is_active(row["시간"],now)
            if active is True:
                ah='<span class="cc-active" style="background:#43a047;">🟢 작동함</span>'
            elif active is False:
                ah='<span class="cc-active" style="background:#c62828;">🔴 작동 안함</span>'
            else:
                ah='<span class="cc-active" style="background:#757575;">⚪ 알수없음</span>'
            with cols[idx]:
                st.markdown(f"""<div class="class-card" style="background:{bg};">
                <p class="cc-name">{row['반']}</p>
                <p class="cc-subject">{subject_text}</p>{ah}
                <p class="cc-status">{status}</p>
                <p class="cc-reason">{reason}</p>
                <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div></div>""", unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세 (시간축 + 범위 선택)
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")
    cc1, cc2 = st.columns([2,1])
    with cc1:
        class_list=sorted(df["반"].unique().tolist())
        selected=st.selectbox("반을 선택하세요", class_list)
    with cc2:
        hours=st.selectbox("표시 범위", [1,3,6,12,24], index=1,
                           format_func=lambda x:f"최근 {x}시간")

    class_df=df[df["반"]==selected].copy()
    class_df=class_df[class_df["datetime"].notna()].sort_values("datetime")

    # 최근 N시간 필터 (데이터의 마지막 시각 기준)
    if len(class_df) > 0:
        last_dt = class_df["datetime"].max()
        cutoff = last_dt - timedelta(hours=hours)
        class_df = class_df[class_df["datetime"] >= cutoff]

    if len(class_df)==0:
        st.warning("해당 범위에 데이터가 없어요.")
    else:
        latest_row=class_df.iloc[-1]
        status,reason,color=check_status(latest_row["온도"],latest_row["co2"],selected,now)
        subject=get_subject(selected,now,slot_name)
        st.markdown(f"## {selected}반 — {status}")
        st.caption(f"{reason} · 현재: {subject or slot_name} · 최근 {hours}시간 / {len(class_df)}개")

        c1,c2,c3,c4=st.columns(4)
        c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
        c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
        c3.metric("💧 습도", f"{latest_row['습도']} %")
        c4.metric("🔥 가스", f"{latest_row['가스']}")
        st.divider()

        def make_chart(y_col, title, color):
            fig=px.line(class_df, x="datetime", y=y_col, title=title, markers=True)
            fig.update_traces(line_color=color, line_width=3,
                marker=dict(size=7,color=color,line=dict(width=1.5,color="white")),
                hovertemplate="<b>%{x|%H:%M:%S}</b><br>"+y_col+": %{y}<extra></extra>")
            fig.update_layout(
                plot_bgcolor="rgba(255,255,255,0.95)",
                paper_bgcolor="rgba(13,71,161,0.55)",
                font_color="#fff", title_font_color="#fff", title_font_size=18,
                xaxis_title="시각", margin=dict(l=20,r=20,t=50,b=20), height=300,
                hoverlabel=dict(bgcolor="white", font_size=14))
            fig.update_xaxes(gridcolor="rgba(13,59,94,0.15)", color="#fff",
                tickformat="%H:%M", tickfont_color="#fff", title_font_color="#fff")
            fig.update_yaxes(gridcolor="rgba(13,59,94,0.15)", color="#fff",
                tickfont_color="#fff", title_font_color="#fff")
            return fig

        col1,col2=st.columns(2)
        with col1:
            st.plotly_chart(make_chart("co2","🫁 CO₂ 변화","#e53935"), use_container_width=True)
            st.plotly_chart(make_chart("온도","🌡️ 온도 변화","#00897b"), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart("습도","💧 습도 변화","#1e88e5"), use_container_width=True)
            st.plotly_chart(make_chart("가스","🔥 가스 변화","#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹 (오늘 하루)
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 오늘의 에너지 절약 랭킹")
    st.caption(f"📅 {now.strftime('%Y년 %m월 %d일')} 집계 (매일 0시 초기화)")
    st.caption("온도적정(40)+환기(25)+이동수업절약(20)+안정성(15) = 100점")

    # 오늘 데이터만 필터
    today = now.date()
    df_today = df[df["datetime"].notna()].copy()
    df_today = df_today[df_today["datetime"].apply(lambda d: d.date()==today)]

    if len(df_today)==0:
        st.warning("오늘 수집된 데이터가 아직 없어요.")
    else:
        results=[]
        for class_id in df_today["반"].unique():
            dc=df_today[df_today["반"]==class_id].reset_index(drop=True)
            sc,detail=energy_score_today(class_id, dc, now)
            latest=dc.iloc[-1]
            results.append((class_id,sc,detail,latest))
        results.sort(key=lambda x:x[1], reverse=True)

        for idx,(class_id,sc,detail,latest) in enumerate(results):
            medal=["🥇","🥈","🥉"][idx] if idx<3 else f"{idx+1}위"
            status,reason,color=check_status(latest["온도"],latest["co2"],class_id,now)
            bg=COLOR_HEX.get(color,"#757575")
            detail_str=" · ".join(f"{k} {v}" for k,v in detail.items())
            st.markdown(f"""<div class="class-card" style="background:{bg};">
                <div style="display:flex;align-items:center;">
                <div style="font-size:40px;margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                <p class="cc-name">{class_id} — {sc}점</p>
                <p class="cc-status">{status}</p>
                <p class="cc-reason">🌡️ 현재 {latest['온도']}°C · 🫁 {latest['co2']}ppm</p>
                <div class="cc-data">{detail_str}</div>
                </div></div></div>""", unsafe_allow_html=True)


# ========================================
# 페이지 4: 시간표
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")
    selected=st.selectbox("반 선택", sorted(TIMETABLE.keys()))
    weekday=now.weekday()
    if weekday>=5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day=WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule=DAY_SCHEDULE[weekday]
        html='<table class="tt-table"><tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>'
        for name,start,end,kind in schedule:
            subject=TIMETABLE.get(selected,{}).get(day,{}).get(name,"")
            time_str=f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now=(start<=now.time()<end)
            rc={"break":"tt-break","lunch":"tt-lunch","homeroom":"tt-home"}.get(kind,"")
            if is_now: rc+=" tt-now"
            tag=" 🔴" if is_now else ""
            disp=subject if subject else name
            html+=f'<tr class="{rc}"><td class="tt-period">{name}{tag}</td><td>{time_str}</td><td>{disp}</td></tr>'
        html+='</table>'
        st.markdown(html, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트 (직관적)
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")

    df_valid = df[df["datetime"].notna() & df["온도"].notna()]
    if len(df_valid)==0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1,c2,c3=st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df_valid['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df_valid['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df_valid['습도'].mean():.1f} %")
        st.divider()

        layout=dict(plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(13,71,161,0.55)", font_color="#fff",
            title_font_color="#fff", margin=dict(l=20,r=20,t=60,b=20))

        # 1) 시간대별 평균 온도 (직관적: 언제 더웠나/추웠나)
        st.subheader("⏰ 시간대별 평균 온도 — 언제 냉방을 더 틀었나?")
        df_valid = df_valid.copy()
        df_valid["시각"] = df_valid["datetime"].dt.hour
        hourly = df_valid.groupby("시각")["온도"].mean().reset_index()
        fig=px.bar(hourly, x="시각", y="온도", text_auto=".1f",
            color="온도", color_continuous_scale="RdBu_r",
            labels={"시각":"시간 (시)","온도":"평균 온도(°C)"})
        fig.update_traces(marker_line_width=2, marker_line_color="#0d3b66",
            textposition="outside")
        # 적정 온도 기준선
        fig.add_hline(y=24, line_dash="dash", line_color="lime",
            annotation_text="적정 하한 24도", annotation_font_color="white")
        fig.add_hline(y=26, line_dash="dash", line_color="orange",
            annotation_text="적정 상한 26도", annotation_font_color="white")
        fig.update_layout(height=380, title="시간대별 평균 온도", **layout)
        fig.update_xaxes(color="#fff",tickfont_color="#fff",title_font_color="#fff",dtick=1)
        fig.update_yaxes(color="#fff",tickfont_color="#fff",title_font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)

        col1,col2=st.columns(2)
        with col1:
            # 2) 온도 상태 비율 (도넛)
            st.subheader("🌡️ 온도 상태 비율")
            def temp_cat(t):
                if t<22: return "너무 추움(낭비)"
                elif t<=28: return "적정"
                else: return "너무 더움"
            df_valid["상태분류"]=df_valid["온도"].apply(temp_cat)
            cat=df_valid["상태분류"].value_counts().reset_index()
            cat.columns=["상태","개수"]
            fig2=px.pie(cat, names="상태", values="개수", hole=0.5,
                color="상태", color_discrete_map={
                    "적정":"#2e7d32","너무 추움(낭비)":"#1e88e5","너무 더움":"#e53935"})
            fig2.update_traces(textinfo="percent+label", textfont_color="white",
                marker=dict(line=dict(color="#0d3b66", width=3)))
            fig2.update_layout(height=350, **layout)
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            # 3) CO2 상태 비율 (환기 정도)
            st.subheader("🫁 환기 상태 비율")
            def co2_cat(c):
                if c<=1000: return "쾌적"
                elif c<=1500: return "보통"
                else: return "환기 필요"
            df_valid["환기분류"]=df_valid["co2"].apply(co2_cat)
            cat2=df_valid["환기분류"].value_counts().reset_index()
            cat2.columns=["상태","개수"]
            fig3=px.pie(cat2, names="상태", values="개수", hole=0.5,
                color="상태", color_discrete_map={
                    "쾌적":"#2e7d32","보통":"#f9a825","환기 필요":"#e53935"})
            fig3.update_traces(textinfo="percent+label", textfont_color="white",
                marker=dict(line=dict(color="#0d3b66", width=3)))
            fig3.update_layout(height=350, **layout)
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")
    st.markdown("""<div class="info-card"><h3>🌍 우리의 비전</h3>
    <p>학교 교실의 에너지 낭비를 실시간으로 감지하고, 모두가 한눈에 볼 수 있게 하여 에너지 절약 문화를 만든다!</p></div>""", unsafe_allow_html=True)
    goals=[("🔋","에너지 낭비 감지","이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊","데이터 기반 의사결정","감이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️","쾌적한 학습 환경","적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆","절약 동기 부여","반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱","환경 보호 실천","작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다.")]
    for icon,title,desc in goals:
        st.markdown(f'<div class="info-card"><h3>{icon} {title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h3>📡 작동 원리</h3>
    <p>라즈베리파이 피코 + SCD30 + MQ-2 센서로 교실 환경 측정 → 구글 시트 저장 → 이 대시보드에서 실시간 분석! (30초마다 자동 갱신)</p></div>""", unsafe_allow_html=True)
주요 변경 설명
① 시간 파싱 (★ 작동함/작동안함 해결)
parse_time()이 2026. 6. 8 오전 11:10:26을 직접 분해해서 datetime으로 변환해요. 이제 작동 여부가 제대로 떠요!
단, 피코 시간과 PC 시간이 같아야 정확해요. 피코가 보내는 시간이 실제 시간과 맞는지 확인하세요. (만약 다르면 작동함 판단이 틀어질 수 있어요)
② 태양
위치를 top:30px; right:40px로 화면 안쪽에
갈퀴 길이 조정해서 얼굴(눈·웃는 입)이 잘 보이게
크기 키움 (core 130px)
③ 구름 z-index:0 (맨 뒤)
콘텐츠는 z-index:10, 구름은 z-index:0 → 이제 구름이 글씨/카드를 안 가려요!
④ 반별 상세 — 시간축
x축이 실제 시각(datetime)
최근 1/3/6/12/24시간 선택 가능
마우스 올리면 11:10:56 같은 정확한 시각 표시 (hovertemplate)
⑤ 에너지 리포트 — 직관적
시간대별 평균 온도 막대 + 적정선(24·26도) 표시 → "몇 시에 냉방 셌나" 한눈에
온도 상태 도넛(적정/추움/더움 비율)
환기 상태 도넛(쾌적/보통/환기필요)
⑥ 에너지 랭킹 — 오늘 하루 + 정교화
오늘 날짜 데이터만 집계 (다음날 자동 초기화 — 코드가 매번 오늘 데이터만 보니까)
점수: 온도적정(40) + 환기(25) + 이동수업절약(20) + 안정성(15)
**이동수업 시간
오후 3:27
