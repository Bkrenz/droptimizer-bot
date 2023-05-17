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

class DroptimizerService:

    @staticmethod
    async def add_reports(reports: list):
        # Make sure we have reports ready
        if len(reports) == 0:
            return [], []
        
        # Parse each report
        successful_reports = []
        failed_reports = []
        for report in reports:
            try:
                # Get Report 
                report_code = report.split('/')[5]
                data = RaidBots.get_report_json(report_code)

                # Get Report Information
                name = data['simbot']['player']
                spec = (data['simbot']['spec'] + ' ' + data['simbot']['charClass']).title()
                reportType = data['simbot']['simType']
                reportDate = datetime.datetime.fromtimestamp(int(data['simbot']['date']) / 1000)
                reportTitle = data['simbot']['publicTitle'].split('\u2022')
                difficulty = reportTitle[2].strip()
                baseline = int(data['sim']['players'][0]['collected_data']['dps']['median'])

                # Get the Player from the database
                player = Player.get_player_by_name(name)
                if player is None:
                    player = Player.create_player(name, spec)

                # Add the Report Info
                sim_report = SimReport.add_new_report(player.id, report, reportType, reportDate)

                # Get all the Simmed Items
                simmed_items = data['sim']['profilesets']['results']
                for sim in simmed_items:
                    sim_list = sim['name'].split('/')
                    item_id = sim_list[3]
                    encounter_id = sim_list[1]
                    value = int(sim['median']) - baseline

                    # Get the Encounter
                    encounter = Encounter.get_encounter_by_blizz_id(encounter_id)
                    if encounter is None:
                        encounter = Encounter.create_encounter(encounter_id)

                    # Get the Item
                    item = Item.get_item_by_blizz_id(item_id)
                    if item is None:
                        item = Item.create_item(item_id, encounter.id)

                    # Get the SimItem
                    sim_item = SimItem.get_sim_item(player.id, item.id, difficulty)
                    if sim_item is None:
                        SimItem.create_sim_item(player.id, item.id, value, difficulty)
                    else:
                        SimItem.update_sim_item(sim_item, value)

                # Add the report to the successful list
                successful_reports.append(f'{name:12} \u2022 {report_code}')

                # Upload the report to WowAudit
                asyncio.create_task(WowAudit.upload_droptimizer_report_async(report_code))

            # Catch the errors
            except Exception as e:
                logging.error(f'{e}:\n + {e.with_traceback}')
                failed_reports.append(report.split('/')[5])

        # Return
        return successful_reports, failed_reports



