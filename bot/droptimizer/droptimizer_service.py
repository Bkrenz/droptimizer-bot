import os
import asyncio
import logging
import requests
import json
import datetime

from ..models.player import Player
from ..models.item import Item
from ..models.sim_report import SimReport
from ..models.sim_item import SimItem
from ..models.encounter import Encounter

from ..apis.wowaudit import WowAudit
from ..apis.raidbots import RaidBots

from ..embeds.successful_reports_embed import create_successful_reports_embed

class DroptimizerService:

    @staticmethod
    async def add_reports(reports: list):
        # Make sure we have reports ready
        if len(reports) == 0:
            return [], []
        
        # Parse each report
        embed_list = []
        for report in reports:
            try:
                # Get Report 
                report_code = report.split('/')[5]

                # Upload the report to WowAudit
                asyncio.create_task(WowAudit.upload_droptimizer_report_async(report_code))
                resp = await WowAudit.upload_droptimizer_report_async(report_code)
                if resp['created']:
                    embed_list.append(create_successful_reports_embed(report_code, True, ''))
                else:
                    embed_list.append(create_successful_reports_embed(report_code, False, resp['error:']))

            # Catch the errors
            except Exception as e:
                logging.error(f'{e}')

        # Return
        return embed_list



