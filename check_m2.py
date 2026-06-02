import os, requests
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.') / '.env')
API_KEY = os.getenv("ECOS_API_KEY") or os.getenv("API_KEY")

url = f"http://ecos.bok.or.kr/api/StatisticItemList/{API_KEY}/json/kr/1/10/161Y005/"
r = requests.get(url, timeout=15).json()
if "StatisticItemList" in r:
    for row in r["StatisticItemList"]["row"]:
        print(f"  {row.get('ITEM_CODE',''):<15} {row.get('ITEM_NAME','')}  [{row.get('CYCLE','')} ~{row.get('END_TIME','')}]")
else:
    print(f"  ERROR: {r.get('RESULT',{}).get('MESSAGE','?')}")
