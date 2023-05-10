import os
import requests
import aiohttp

class WowAudit:

    wowaudit_credentials = os.getenv('WOW_AUDIT_CREDENTIALS')

    @staticmethod
    async def upload_droptimizer_report_async(report_id):
        url = 'https://wowaudit.com/v1/wishlists'
        
        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit.wowaudit_credentials,
            'Content-Type': 'application/json'
        }

        data = {
            'report_id': report_id,
            'replace_manual_edits': True,
            'clear_conduits': True
        }

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, headers=headers, json=data)
        except Exception as e:
            print(e + '\n' + e.with_traceback())
