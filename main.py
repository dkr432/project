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
