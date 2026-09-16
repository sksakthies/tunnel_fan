from machine import ADC, Pin, PWM
import network
import urequests
import json
import time
import dht
import math
import gc

# ===========================
# CONSTANTS
# ===========================
VREF = 3.3
ADC_MAX = 4095

MIN_DUTY = 250
MAX_DUTY = 1023

# ===========================
# 1️⃣ VIBRATION SENSOR
# ===========================
adc_x = ADC(Pin(32))
adc_y = ADC(Pin(33))
adc_z = ADC(Pin(34))

for adc in (adc_x, adc_y, adc_z):
    adc.atten(ADC.ATTN_11DB)

def read_voltage(adc):
    return adc.read() * VREF / ADC_MAX

# ===========================
# 2️⃣ CURRENT SENSOR
# ===========================
adc_current = ADC(Pin(35))
adc_current.atten(ADC.ATTN_11DB)

SENSITIVITY = 0.185
ZERO_CURRENT_VOLTAGE = 1.487
NOISE_THRESHOLD = 0.05

def read_current():
    raw = adc_current.read()
    voltage = raw * VREF / ADC_MAX
    diff = voltage - ZERO_CURRENT_VOLTAGE
    current = abs(diff / SENSITIVITY)

    if current < NOISE_THRESHOLD:
        current = 0

    return round(current, 3)

# ===========================
# 3️⃣ POTENTIOMETER
# ===========================
adc_pot = ADC(Pin(36))
adc_pot.atten(ADC.ATTN_11DB)

# ===========================
# 4️⃣ FAN PWM
# ===========================
fan_pwm = PWM(Pin(26), freq=25000)
fan_pwm.duty(MIN_DUTY)

# ===========================
# 5️⃣ RPM SENSOR
# ===========================
rpm_pin = Pin(25, Pin.IN, Pin.PULL_UP)
pulse_count = 0

def count_pulse(pin):
    global pulse_count
    pulse_count += 1

rpm_pin.irq(trigger=Pin.IRQ_FALLING, handler=count_pulse)

def calculate_rpm(interval_sec):
    global pulse_count
    pulses = pulse_count
    pulse_count = 0
    rpm = (pulses / 2) * (60 / interval_sec)
    return round(rpm, 1)

# ===========================
# 6️⃣ DHT11
# ===========================
dht_sensor = dht.DHT11(Pin(27))

def read_dht():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except:
        return None, None

# ===========================
# 7️⃣ WIFI (Stable Version)
# ===========================
ssid = "password"
password = "password"

wifi = network.WLAN(network.STA_IF)

if wifi.isconnected():
    wifi.disconnect()
    time.sleep(1)

wifi.active(False)
time.sleep(1)
wifi.active(True)
time.sleep(1)

print("Connecting to WiFi...")
wifi.connect(ssid, password)

while not wifi.isconnected():
    time.sleep(1)

print("WiFi Connected:", wifi.ifconfig())

# ===========================
# 8️⃣ FIREBASE
# ===========================
FIREBASE_URL = ##
DEVICE_NAME = "Fan-1"

# ===========================
# MAIN LOOP
# ===========================
while True:

    # ---- Sensor Readings ----
    vx = read_voltage(adc_x)
    vy = read_voltage(adc_y)
    vz = read_voltage(adc_z)
    vibration = round(math.sqrt(vx*vx + vy*vy + vz*vz), 3)

    temperature, humidity = read_dht()
    current = read_current()

    # ---- Potentiometer → PWM ----
    pot_value = adc_pot.read()
    duty = int((pot_value / 4095) * (MAX_DUTY - MIN_DUTY) + MIN_DUTY)
    fan_pwm.duty(duty)

    time.sleep(2)
    rpm = calculate_rpm(2)

    # ---- Print Before Upload ----
    print("=================================")
    print("Pot Value :", pot_value)
    print("RPM       :", rpm)
    print("Vibration :", vibration)
    print("Current   :", current)
    print("Temp      :", temperature)
    print("Humidity  :", humidity)

    # ---- Prepare Firebase Data (NO POT VALUE) ----
    t = time.localtime()
    date = "{:02d}-{:02d}-{:04d}".format(t[2], t[1], t[0])
    time_key = "{:02d}-{:02d}-{:02d}".format(t[3], t[4], t[5])

    data = {
        "vibration": vibration,
        "current": current,
        "rpm": rpm,
        "temperature": temperature,
        "humidity": humidity
    }

    url = "{}/{}/{}/{}.json".format(
        FIREBASE_URL,
        DEVICE_NAME,
        date,
        time_key
    )

    gc.collect()

    # ---- Upload ----
    try:
        response = urequests.put(
            url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        print("Upload Success ✅")
        response.close()
    except Exception as e:
        print("Firebase error:", e)

    time.sleep(1)