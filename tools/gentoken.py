#!/usr/bin/env python3

from datetime import datetime, timedelta
from dotenv import load_dotenv
import jwt
import os

load_dotenv()

APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
if not APPLE_TEAM_ID:
    raise ValueError("APPLE_TEAM_ID missing from environment")

APPLE_WEATHER_APP_ID = os.getenv("APPLE_WEATHER_APP_ID")
if not APPLE_WEATHER_APP_ID:
    raise ValueError("APPLE_WEATHER_APP_ID missing from environment")

APPLE_WEATHER_KEY_ID = os.getenv("APPLE_WEATHER_KEY_ID")
if not APPLE_WEATHER_KEY_ID:
    raise ValueError("APPLE_WEATHER_KEY_ID missing from environment")

APPLE_WEATHER_KEY = os.getenv("APPLE_WEATHER_KEY")
if not APPLE_WEATHER_KEY:
    raise ValueError("APPLE_WEATHER_KEY missing from environment")

# Taken from <https://github.com/greencoder/weatherkit-python/blob/main/src/weatherkit/weatherkit.py>
# 
# MIT License
# 
# Copyright (c) 2022 Scott Newman
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

init_at = int(datetime.now().timestamp())
expire_at = int((datetime.now() + timedelta(weeks=26)).timestamp())  # valid for 6 months

token = jwt.encode(
    payload = {
        'iss': APPLE_TEAM_ID,
        'sub': APPLE_WEATHER_APP_ID,
        'iat': init_at,
        'exp': expire_at,
    },
    key = APPLE_WEATHER_KEY,
    headers = {
        'alg': 'ES256',
        'kid': APPLE_WEATHER_KEY_ID,
        'typ': 'JWT',
        'id': f'{APPLE_TEAM_ID}.{APPLE_WEATHER_APP_ID}'
    }
)

print(f"WEATHER_TOKEN=\"{token}\"")
