import json
import os
import requests
import aiohttp
from ..embeds.raidbots_embed import RaidbotsEmbed
from ..embeds.qe_live_embed import QELiveEmbed

WOW_AUDIT_URL = 'https://wowaudit.com/v1/wishlists'

class WowAudit:

    wowaudit_credentials = os.getenv('WOW_AUDIT_CREDENTIALS')

    @staticmethod
    async def upload_report(report_id):
        url = 'https://wowaudit.com/v1/wishlists'
        
        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit.wowaudit_credentials,
            'Content-Type': 'application/json'
        }

        data = {
            'report_id': report_id,
            "configuration_name": "Single Target",
            'replace_manual_edits': True,
            'clear_conduits': True
        }

        try:
            async with aiohttp.ClientSession() as session:
                result = await session.post(url, headers=headers, json=data)
                resp = json.loads(await result.text())
                return resp
        except Exception as e:
            print(e + '\n' + e.with_traceback())


    @staticmethod
    async def upload_raidbots_report(report_code):
        resp = await WowAudit.upload_report(report_code)
        if resp['created']:
            return RaidbotsEmbed.create(report_code, True, None)
        else:
            return RaidbotsEmbed.create(report_code, False, resp['error:'])
        
    @staticmethod
    async def upload_qe_live_report(report_code):
        resp = await WowAudit.upload_report(report_code)
        if resp['created']:
            return QELiveEmbed.create(report_code, True, None)
        else:
            return QELiveEmbed.create(report_code, False, resp['error:'])


