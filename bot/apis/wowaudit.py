import os
import requests

class WowAudit:

    wowaudit_credentials = os.getenv('WOW_AUDIT_CREDENTIALS')

    @staticmethod
    def upload_droptimizer_report(report_id):
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

        requests.post(url, headers=headers, json=data)