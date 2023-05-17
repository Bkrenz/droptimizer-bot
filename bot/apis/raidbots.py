import requests
import json

class RaidBots:

    @staticmethod
    def create_report_link(report_code):
        return f'https://www.raidbots.com/simbot/report/{report_code}'
    

    @staticmethod
    def get_report_json(report_code):
        report_link = RaidBots.create_report_link(report_code)

        with requests.Session() as s:
            data = s.get(report_link + '/data.json').content.decode('utf-8')

        return json.loads(data)