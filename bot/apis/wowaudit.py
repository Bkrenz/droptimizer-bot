import json
import os
import asyncio
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
            'replace_manual_edits': True,
            'clear_conduits': True
        }

        configuration_name = os.getenv('WOW_AUDIT_CONFIGURATION')
        if configuration_name:
            data['configuration_name'] = configuration_name

        try:
            async with aiohttp.ClientSession() as session:
                result = await session.post(url, headers=headers, json=data)
                
                # Check for HTTP errors
                if result.status >= 400:
                    error_text = await result.text()
                    print(f"WowAudit API Error (HTTP {result.status}): {error_text}")
                    
                    # Try to extract error message from API response
                    try:
                        error_resp = json.loads(error_text)
                        error_msg = error_resp.get('error') or error_resp.get('message') or error_resp.get('base') or error_text
                        if isinstance(error_msg, list):
                            error_msg = '\n'.join(str(e) for e in error_msg)
                    except (json.JSONDecodeError, AttributeError):
                        error_msg = error_text or f"HTTP {result.status}"
                    
                    return {'created': False, 'base': [error_msg] if error_msg else [f"HTTP {result.status}"]}
                
                resp = json.loads(await result.text())
                return resp
        except aiohttp.ClientConnectionError as e:
            print(f"Connection error connecting to WowAudit: {e}")
            return {'created': False, 'base': ["Unable to connect to WowAudit. Please check your internet connection and try again."]}
        except aiohttp.ClientSSLError as e:
            print(f"SSL error connecting to WowAudit: {e}")
            return {'created': False, 'base': ["Security error connecting to WowAudit. Please try again later."]}
        except asyncio.TimeoutError:
            print("Timeout while uploading report to WowAudit")
            return {'created': False, 'base': ["Request timed out. WowAudit took too long to respond. Please try again later."]}
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response from WowAudit: {e}")
            return {'created': False, 'base': ["WowAudit returned an unexpected response. Please try again later."]}
        except Exception as e:
            print(f"Unexpected error uploading to WowAudit: {e}")
            return {'created': False, 'base': [f"Unexpected error: {str(e)}"]}


    @staticmethod
    async def upload_raidbots_report(report_code):
        resp = await WowAudit.upload_report(report_code)
        if resp['created']:
            return RaidbotsEmbed.create(report_code, True, None)
        else:
            print(resp)
            return RaidbotsEmbed.create(report_code, False, resp['base'])

    @staticmethod
    async def upload_qe_live_report(report_code):
        resp = await WowAudit.upload_report(report_code)
        if resp['created']:
            return QELiveEmbed.create(report_code, True, None)
        else:
            return QELiveEmbed.create(report_code, False, resp['base'])


