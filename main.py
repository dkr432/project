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
