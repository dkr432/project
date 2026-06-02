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
