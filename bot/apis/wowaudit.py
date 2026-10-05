import json
import os
import asyncio
import logging
import requests
import aiohttp
from pathlib import Path
from ..embeds.raidbots_embed import RaidbotsEmbed
from ..embeds.qe_live_embed import QELiveEmbed

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WOW_AUDIT_URL = 'https://wowaudit.com/v1/wishlists'
WOW_AUDIT_CHARACTERS_URL = 'https://wowaudit.com/v1/characters'

class WowAudit:

    wowaudit_credentials = os.getenv('WOW_AUDIT_CREDENTIALS')

    @staticmethod
    def _authorization_header():
        credentials = WowAudit.wowaudit_credentials or os.getenv('WOW_AUDIT_CREDENTIALS')
        if not credentials:
            credential_path = Path(__file__).resolve().parents[2] / 'resources' / 'WOW_AUDIT_CREDENTIALS'
            if credential_path.is_file():
                credentials = credential_path.read_text(encoding='utf-8').strip()
                if credentials.startswith('WOW_AUDIT_CREDENTIALS='):
                    credentials = credentials.split('=', 1)[1].strip().strip('"').strip("'")

        if not credentials:
            raise RuntimeError('WoWAudit credentials are not configured.')
        if not credentials.lower().startswith('bearer '):
            credentials = f'Bearer {credentials}'
        return credentials

    @staticmethod
    async def get_wishlist_overview():
        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit._authorization_header(),
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(WOW_AUDIT_URL, headers=headers) as response:
                response.raise_for_status()
                return await response.json()

    @staticmethod
    async def get_characters():
        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit._authorization_header(),
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(WOW_AUDIT_CHARACTERS_URL, headers=headers) as response:
                response.raise_for_status()
                return await response.json()

    @staticmethod
    async def get_character_wishlists(character_ids: list[int]):
        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit._authorization_header(),
        }
        semaphore = asyncio.Semaphore(5)

        async with aiohttp.ClientSession() as session:
            async def get_character_wishlist(character_id: int):
                async with semaphore:
                    url = f'{WOW_AUDIT_URL}/{character_id}'
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()

            wishlists = await asyncio.gather(*(get_character_wishlist(character_id) for character_id in character_ids))
        return dict(zip(character_ids, wishlists))

    @staticmethod
    async def upload_report(report_id):
        url = 'https://wowaudit.com/v1/wishlists'

        headers = {
            'accept': 'application/json',
            'Authorization': WowAudit._authorization_header(),
            'Content-Type': 'application/json'
        }

        data = {
            'report_id': report_id,
            'replace_manual_edits': True,
            'configuration_name': 'Single Target',
            'clear_conduits': True
        }

        configuration_name = os.getenv('WOW_AUDIT_CONFIGURATION')
        if configuration_name:
            data['configuration_name'] = configuration_name

        try:
            async with aiohttp.ClientSession() as session:
                result = await session.post(url, headers=headers, json=data)
                response_text = await result.text()
                
                # Try to parse response as JSON
                try:
                    resp = json.loads(response_text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, check HTTP status
                    if result.status >= 400:
                        print(f"WowAudit API Error (HTTP {result.status}): {response_text}")
                        return {'created': False, 'base': [response_text or f"HTTP {result.status}"]}
                    # If status is ok but can't parse JSON, return error
                    print(f"Invalid JSON response from WowAudit: {response_text}")
                    return {'created': False, 'base': ["WowAudit returned an unexpected response. Please try again later."]}
                
                # Check if response indicates success
                if resp.get('created') is True:
                    return resp
                
                # Response was parsed but indicates an error (created is False or missing)
                # Extract error message from response
                error_msg = None
                if isinstance(resp.get('base'), list) and resp['base']:
                    # base is a list of errors
                    error_msg = resp['base']
                elif isinstance(resp.get('base'), str):
                    # base is a single error string
                    error_msg = [resp['base']]
                elif 'error' in resp:
                    error_msg = [resp['error']] if isinstance(resp['error'], str) else resp['error']
                elif 'message' in resp:
                    error_msg = [resp['message']] if isinstance(resp['message'], str) else resp['message']
                else:
                    # Couldn't find specific error, return the whole response
                    error_msg = [json.dumps(resp)]
                
                print(f"WowAudit API returned error: {error_msg}")
                return {'created': False, 'base': error_msg or ['Unknown error']}
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
        logger.debug(f"=== Raidbots Report Response ===")
        logger.debug(f"Report Code: {report_code}")
        logger.debug(f"Full Response: {resp}")
        logger.debug(f"Created: {resp.get('created')}")
        logger.debug(f"Base: {resp.get('base')}")
        logger.debug(f"================================")
        
        if resp.get('created'):
            return RaidbotsEmbed.create(report_code, True, None)
        else:
            error_list = resp.get('base', ['Unknown error'])
            return RaidbotsEmbed.create(report_code, False, error_list)

    @staticmethod
    async def upload_qe_live_report(report_code):
        resp = await WowAudit.upload_report(report_code)
        if resp['created']:
            return QELiveEmbed.create(report_code, True, None)
        else:
            return QELiveEmbed.create(report_code, False, resp['base'])


