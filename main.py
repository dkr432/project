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
