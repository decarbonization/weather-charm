from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime, timedelta
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

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
wifi.radio.connect(ssid, password)

requests = adafruit_requests.Session(
    socketpool.SocketPool(wifi.radio), ssl.create_default_context()
)

tz = os.getenv("TIME_ZONE")
sync_time_response = requests.get(
    f"https://io.adafruit.com/api/v2/{os.getenv('ADAFRUIT_IO_USERNAME')}/integrations/time/struct?x-aio-key={os.getenv('ADAFRUIT_IO_KEY')}&tz={tz}"
)
sync_time = sync_time_response.json()
rtc.datetime = time.struct_time(
    (
        sync_time["year"],
        sync_time["mon"],
        sync_time["mday"],
        sync_time["hour"],
        sync_time["min"],
        sync_time["sec"],
        sync_time["wday"],
        sync_time["yday"],
        sync_time["isdst"],
    )
)

battery_monitor = adafruit_max1704x.MAX17048(i2c)

FONT_SMALL = bitmap_font.load_font("fonts/spleen-5x8.bdf")
FONT_REGULAR = bitmap_font.load_font("fonts/spleen-8x16.bdf")
COLOR_BG = 0x0066E4
COLOR_FG = 0xFFFFFF

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

status_bar = label.Label(FONT_SMALL, text="   Loading...  ", color=COLOR_FG)
status_bar.x = display.width // 2 - status_bar.bounding_box[2] // 2
status_bar.y = status_bar.bounding_box[3] // 2
root.append(status_bar)

status_bar_line_bitmap = displayio.Bitmap(display.width, 1, 1)
status_bar_line_palette = displayio.Palette(1)
status_bar_line_palette[0] = COLOR_FG

status_bar_line_sprite = displayio.TileGrid(
    status_bar_line_bitmap,
    pixel_shader=status_bar_line_palette,
    x=0,
    y=status_bar.bounding_box[3],
)
root.append(status_bar_line_sprite)

display.refresh()


def temp(t: float | None):
    if t is None:
        return "--°"
    return f"{round((t * 1.8) + 32)}°"


def percent(p: float | None):
    if p is None:
        return "--%"
    return f"{round(p * 100)}%"


def condition(c: str | None):
    if c is None:
        return "?"

    pretty_c = ""
    for i, ch in enumerate(c):
        if i > 0 and ch.isupper():
            pretty_c += " "
        pretty_c += ch

    return pretty_c


def speed(s: float | None):
    if s is None:
        return "--mph"
    return f"{round(s * 0.6213712)}mph"


class Forecast:
    temp: str
    feelsLike: str
    condition: str
    humidity: str
    uvIndex: str
    windSpeed: str
    hours: list[tuple[datetime, str, str, str]]

    def __init__(self, lat: str, lng: str):
        hourlyEnd = (datetime.now() + timedelta(hours=6)).isoformat()
        weather_response = requests.get(
            f"https://weatherkit.apple.com/api/v1/weather/en-US/{lat}/{lng}?dataSets=currentWeather%2CforecastHourly&hourlyEnd={hourlyEnd}&timezone={tz}",
            headers={"Authorization": f"Bearer {os.getenv('WEATHER_TOKEN')}"},
        )
        weather = weather_response.json()
        current_weather = weather.get("currentWeather", {})
        self.temp = temp(current_weather.get("temperature"))
        self.feelsLike = temp(current_weather.get("temperatureApparent"))
        self.condition = condition(current_weather.get("conditionCode"))
        self.humidity = percent(current_weather.get("humidity"))
        self.uvIndex = f"{current_weather.get('uvIndex', 0)}UV"
        self.windSpeed = speed(current_weather.get("windSpeed"))
        forecast_hourly = weather.get("forecastHourly", {})
        self.hours = [
            (
                datetime.fromisoformat(hour.get("forecastStart")),
                condition(hour.get("conditionCode")),
                temp(hour.get("temperature")),
                percent(hour.get("precipitationChance")),
            )
            for hour in forecast_hourly.get("hours", [])
        ]


forecast = Forecast(os.getenv("LAT"), os.getenv("LNG"))


def current_weather():
    scene = displayio.Group()

    temp_label = label.Label(FONT_REGULAR, text=forecast.temp, color=COLOR_FG)
    temp_label.scale = 2
    temp_label.x = display.width // 2 - temp_label.bounding_box[2]
    temp_label.y = display.height // 2
    scene.append(temp_label)

    feels_like_label = label.Label(
        FONT_REGULAR, text=f"Feels like {forecast.feelsLike}", color=COLOR_FG
    )
    feels_like_label.x = display.width // 2 - feels_like_label.bounding_box[2] // 2
    feels_like_label.y = (display.height // 2 + temp_label.bounding_box[3]) + 5
    scene.append(feels_like_label)

    condition_label = label.Label(FONT_SMALL, text=forecast.condition, color=COLOR_FG)
    condition_label.x = display.width // 2 - condition_label.bounding_box[2] // 2
    condition_label.y = (display.height - condition_label.bounding_box[3] // 2) - 2
    scene.append(condition_label)

    humidity_label = label.Label(FONT_REGULAR, text=forecast.humidity, color=COLOR_FG)
    humidity_label.x = 2
    humidity_label.y = display.height // 2 - humidity_label.bounding_box[3] // 2 - 2
    scene.append(humidity_label)

    uv_label = label.Label(FONT_REGULAR, text=forecast.uvIndex, color=COLOR_FG)
    uv_label.x = 2
    uv_label.y = display.height // 2 + uv_label.bounding_box[3] // 2 + 2
    scene.append(uv_label)

    wind_label = label.Label(FONT_REGULAR, text=forecast.windSpeed, color=COLOR_FG)
    wind_label.x = display.width - wind_label.bounding_box[2] - 2
    wind_label.y = display.height // 2
    scene.append(wind_label)

    return scene


def hourly_forecast():
    scene = displayio.Group()

    walking_y = 20
    for start, condition, temperature, chance in forecast.hours:
        summary = f"{start.hour:02}:00  {temperature}  {chance}  {condition}"
        hour_label = label.Label(FONT_REGULAR, text=summary, color=COLOR_FG)
        hour_label.x = 3
        hour_label.y = walking_y + hour_label.bounding_box[3] // 2
        scene.append(hour_label)
        walking_y += hour_label.bounding_box[3] + 2

    return scene


last_interaction = time.monotonic()
current_scene = current_weather()
root.append(current_scene)
while True:
    now = rtc.datetime
    timestamp = f"{now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02}"
    battery_badge = "+" if battery_monitor.charge_rate > 0.0 else "-"
    battery_percent = f"{int(battery_monitor.cell_percent):03}%"
    status_bar.text = f"{timestamp} | {battery_percent}{battery_badge}"
    display.refresh()

    if (time.monotonic() - last_interaction) <= 420:  # 7 minutes
        if display.brightness > 0 and (time.monotonic() - last_interaction) > 10:
            display.brightness = 0.0

        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 1)
        prev_pin_alarm = alarm.pin.PinAlarm(pin=board.D0, value=False, pull=False)
        wake_pin_alarm = alarm.pin.PinAlarm(pin=board.D1, value=True, pull=True)
        next_pin_alarm = alarm.pin.PinAlarm(pin=board.D2, value=True, pull=True)
        alarm.light_sleep_until_alarms(
            time_alarm, prev_pin_alarm, wake_pin_alarm, next_pin_alarm
        )
        if alarm.wake_alarm != time_alarm:
            last_interaction = time.monotonic()
            display.brightness = 0.5
        if alarm.wake_alarm == prev_pin_alarm:
            root.remove(current_scene)
            current_scene = current_weather()
            root.append(current_scene)
        if alarm.wake_alarm == next_pin_alarm:
            root.remove(current_scene)
            current_scene = hourly_forecast()
            root.append(current_scene)
    else:
        wake_pin_alarm = alarm.pin.PinAlarm(pin=board.D1, value=True, pull=True)
        alarm.exit_and_deep_sleep_until_alarms(wake_pin_alarm)
