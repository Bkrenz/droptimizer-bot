import requests
import json
import datetime

report = 'https://www.raidbots.com/simbot/report/6jG1JPvndLamKVXGkFFTuP'

with requests.Session() as s:
    data = s.get(report + '/data.json').content.decode('utf-8')
data = json.loads(data)

report_time = int(data['simbot']['date'])
print(report_time)
date = datetime.datetime.fromtimestamp(report_time / 1000)
print(date)