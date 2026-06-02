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
