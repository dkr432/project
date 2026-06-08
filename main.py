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
