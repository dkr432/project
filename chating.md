# 내가 지금 SCD30센서, MQ-2센서, LED 10개, 라즈베리파이 PICO 2 W H를 활용해서(아마도 SCD 30센서가 메인일것같아.) 기후행동을 위한 에너지 절약 캠페인 프로젝트를 할거거든? 이런 구성의 장치들을 여러 반에 배치해서, 반마다 데이터를 수집해 대시보드로 옮기고(대시보드는 가능하면 웬만해선 구글 스프레드시트 API를 활용할것같아.) 데이터를 관찰, 그리고 학생들이 에너지를 제대로 절약하고 있는지에 대해서 탐구해보는 프로젝트를 할거야.(학생들이 에너지를 제대로 절약하고 있는가에 대한 로직은 아마도 "교실의 불이 꺼져있는데, 온도가 낮다. 즉 에어컨이 켜져 있지만 교실 안에는 사람들이 없다. 이 뜻은 모두 밥을 먹으러 갔거나, 체육관으로 수업을 이동했는데 에어컨을 끄지 않았다." 이런 느낌으로 로직을 짜볼꺼야. 근데 이건 참고로 지금 짠 하나의 로직이지, 다른 로직도 더 생각할거야.) 일단 한번 기본 구성을 토대로 코드를 짜보자.

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

# 아, 맞다. 조도 센서도 활용할거야.
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

# 일단 지금은 여러 피코들로 하나의 스프레드시트에 전송하는게 일단 내 목표거든? 일단 코드부터 구성해보자.
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

# 어, 니 코드를 봤는데, 나는 피코에 wifi config.py를 따로 만들어서, WIFI_NETWORKS = {
    "U+Net1DFB": "8F9B6B21M!",
    "app": "20242024"
}
 이렇게 이미 코드를 넣어놨어. 와이파이를, 아무튼? 그리고, 내가 지금 생각하는건, 하나의 장치에서만 웹사이트를 열어서, 그 웹사이트를 통해, 구글 스프레드 시트로 입력받은 데이터들을 그래프나 다른 모양으로 볼 수 있게 하고 싶어. 그러니까, 총 파일은 main.py, wifi_config.py,web.py로 구성해서, 다른 장치들은main.py, wifi_config.py만 가지고 있고, 하나의 장치에서는 web.py까지 넣어서 웹앱을 열게 하는거지, 굳이 모든 장치에서 웹앱을 열필요는 없을 것같다고 판단했어.
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

# 일단은 A 대안으로 생각 해두고 있었어. 일단 스프레드시트와 연동을 할 메인 코드를 짜보자 이제
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
