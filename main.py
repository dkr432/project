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
