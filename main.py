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
