import os, requests
from dotenv import load_dotenv
load_dotenv()

with open('.fyers_token') as f:
    access_token = f.read().strip()
app_id = os.getenv('FYERS_APP_ID')

url = 'https://api-t1.fyers.in/data/history'
headers = {'Authorization': f'{app_id}:{access_token}'}
params = {
    'symbol': 'NSE:RELIANCE-EQ',
    'resolution': 'D',
    'date_format': '1',
    'range_from': '2025-07-07',
    'range_to': '2026-07-07',
    'cont_flag': '1',
}
r = requests.get(url, params=params, headers=headers)
data = r.json()
status = data.get("s")
print(f"Status: {status}")
if status == "ok":
    candles = data.get("candles", [])
    print(f"Candles: {len(candles)} rows")
    print(f"First: {candles[0]}")
    print(f"Last: {candles[-1]}")
else:
    print(f"Error: {data}")
