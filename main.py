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
