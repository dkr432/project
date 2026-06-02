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
