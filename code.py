from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

import adafruit_max1704x
import adafruit_requests
import alarm
import board
import displayio
import os
import rtc
import socketpool
import ssl
import time
import wifi

spi = board.SPI()
i2c = board.I2C()
rtc = rtc.RTC()

if not wifi.radio.ipv4_address or not wifi.radio.connected:
    networks = {}
    for network in os.getenv("WIFI_NETWORKS").split("\n"):
        pieces = network.split("\t")
        networks[pieces[0]] = {
            "pass": pieces[1],
            "lat": pieces[2],
            "lng": pieces[3],
        }

    for scanned_network in wifi.radio.start_scanning_networks():
        network = networks.get(scanned_network.ssid)
        if network:
            wifi.radio.connect(scanned_network.ssid, network["pass"])
            wifi.radio.stop_scanning_networks()
            break
        
requests = adafruit_requests.Session(socketpool.SocketPool(wifi.radio), ssl.create_default_context())

tz = os.getenv('TIME_ZONE')
sync_time_response = requests.get(
    f"https://io.adafruit.com/api/v2/{os.getenv('ADAFRUIT_IO_USERNAME')}/integrations/time/struct?x-aio-key={os.getenv('ADAFRUIT_IO_KEY')}&tz={tz}"
)
sync_time = sync_time_response.json()
rtc.datetime = time.struct_time((
    sync_time["year"], 
    sync_time["mon"], 
    sync_time["mday"], 
    sync_time["hour"], 
    sync_time["min"], 
    sync_time["sec"], 
    sync_time["wday"], 
    sync_time["yday"], 
    sync_time["isdst"],
))

battery_monitor = adafruit_max1704x.MAX17048(i2c)

FONT_SMALL = bitmap_font.load_font("fonts/spleen-5x8.bdf")
FONT_REGULAR = bitmap_font.load_font("fonts/spleen-8x16.bdf")
COLOR_BG = 0xFFFFFF
COLOR_FG = 0x000000

display = board.DISPLAY
display.brightness = 0.5
display.auto_refresh = False
root = displayio.Group()
display.root_group = root

bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = COLOR_BG

bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)
root.append(bg_sprite)

status_bar = label.Label(FONT_SMALL, text="00:00:00 | 000%", color=COLOR_FG)
status_bar.x = display.width // 2 - status_bar.bounding_box[2] // 2
status_bar.y = status_bar.bounding_box[3] // 2
root.append(status_bar)

def temp(t: float | None):
    if t is None:
        return '--°'
    return f"{round((t * 1.8) + 32)}°"

def percent(p: float | None):
    if p is None:
        return '--%'
    return f"{round(p * 100)}%"

def condition(c: str | None):
    if c is None:
        return "?"
    return c

def speed(s: float | None):
    if s is None:
        return '--mph'
    return f"{round(s * 0.6213712)}mph"

class Forecast:
    temp: str
    feelsLike: str
    condition: str
    humidity: str
    uvIndex: str
    windSpeed: str

    def __init__(self, lat: str, lng: str):
        weather_response = requests.get(
            f"https://weatherkit.apple.com/api/v1/weather/en-US/{lat}/{lng}?dataSets=currentWeather&timezone={tz}",
            headers={"Authorization": f"Bearer {os.getenv('WEATHER_TOKEN')}"}
        )
        weather = weather_response.json()
        current_weather = weather.get('currentWeather', {})
        self.temp = temp(current_weather.get('temperature'))
        self.feelsLike = temp(current_weather.get('temperatureApparent'))
        self.condition = condition(current_weather.get('conditionCode'))
        self.humidity = percent(current_weather.get('humidity'))
        self.uvIndex = f"{current_weather.get('uvIndex', 0)}UV"
        self.windSpeed = speed(current_weather.get('windSpeed'))

forecast = Forecast('42.478', '-70.925')

def current_weather():
    group = displayio.Group()

    temp_label = label.Label(FONT_REGULAR, text=forecast.temp, color=COLOR_FG)
    temp_label.scale = 2
    temp_label.x = display.width // 2 - temp_label.bounding_box[2]
    temp_label.y = display.height // 2
    group.append(temp_label)

    feels_like_label = label.Label(FONT_REGULAR, text=f"Feels like {forecast.feelsLike}", color=COLOR_FG)
    feels_like_label.x = display.width // 2 - feels_like_label.bounding_box[2] // 2
    feels_like_label.y = (display.height // 2 + temp_label.bounding_box[3]) + 5
    group.append(feels_like_label)

    condition_label = label.Label(FONT_SMALL, text=forecast.condition, color=COLOR_FG)
    condition_label.x = display.width // 2 - condition_label.bounding_box[2] // 2
    condition_label.y = (display.height - condition_label.bounding_box[3] // 2) - 2
    group.append(condition_label)

    humidity_label = label.Label(FONT_REGULAR, text=forecast.humidity, color=COLOR_FG)
    humidity_label.x = 2
    humidity_label.y = display.height // 2 - humidity_label.bounding_box[3] // 2 - 2
    group.append(humidity_label)

    uv_label = label.Label(FONT_REGULAR, text=forecast.uvIndex, color=COLOR_FG)
    uv_label.x = 2
    uv_label.y = display.height // 2 + uv_label.bounding_box[3] // 2 + 2
    group.append(uv_label)

    wind_label = label.Label(FONT_REGULAR, text=forecast.windSpeed, color=COLOR_FG)
    wind_label.x = display.width - wind_label.bounding_box[2] - 2
    wind_label.y = display.height // 2
    group.append(wind_label)

    return group

last_interaction = time.monotonic()
current_scene = current_weather()
root.append(current_scene)
while True:
    now = rtc.datetime
    status_bar.text = f"{now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02} | {int(battery_monitor.cell_percent):03}%"
    display.refresh()

    if (time.monotonic() - last_interaction) <= 30:
        if display.brightness > 0 and (time.monotonic() - last_interaction) > 10:
            display.brightness = 0.0
        
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 1)
        wake_pin_alarm = alarm.pin.PinAlarm(pin=board.D1, value=True, pull=True)
        alarm.light_sleep_until_alarms(time_alarm, wake_pin_alarm)
        if alarm.wake_alarm != time_alarm:
            last_interaction = time.monotonic()
            display.brightness = 0.5
    else:
        wake_pin_alarm = alarm.pin.PinAlarm(pin=board.D1, value=True, pull=True)
        alarm.exit_and_deep_sleep_until_alarms(wake_pin_alarm)
