# weather-charm

Turn an Adafruit ESP32-S3 Reverse TFT Feather into an appliance to check the current weather conditions wherever you are.

## Prerequisites

This project is written against [CircuitPython 9.2.7](https://circuitpython.org/board/adafruit_feather_esp32s3_reverse_tft/). Download the requisite .UF2 file and copy it to your feather's mass storage.

## settings.toml

### wifi

- `CIRCUITPY_WIFI_SSID`
- `CIRCUITPY_WIFI_PASSWORD`

### time

- `ADAFRUIT_IO_USERNAME`
- `ADAFRUIT_IO_KEY`
- `TIME_ZONE`

### weather

- `LAT`
- `LNG`
- `WEATHER_TOKEN`
