from ..models.player import Player
from ..models.item import Item
from ..models.sim_report import SimReport
from ..models.sim_item import SimItem
from ..models.encounter import Encounter

from ..cogs.exception_logging_cog import ExceptionLoggingCog

import logging
import requests
import json
import datetime

class DroptimizerService:

    def __init__(self):
        pass

    @staticmethod
    def add_reports(reports: list):
        if len(reports) == 0:
            return
        for report in reports:
            try:
                # Get Report 
                with requests.Session() as s:
                    data = s.get(report + '/data.json').content.decode('utf-8')
                data = json.loads(data)

                # Get Report Information
                name = data['simbot']['player']
                spec = (data['simbot']['spec'] + ' ' + data['simbot']['charClass']).title()
                reportType = data['simbot']['simType']
                reportDate = datetime.datetime.now()

                # Get the Player from the database
                player = Player.get_player_by_name(name)
                if player is None:
                    player = Player.create_player(name, spec)

                # Add the Report
                sim_report = SimReport.add_new_report(player.id, report, reportType, reportDate)

            except Exception as e:
                logging.error(f'{e}:\n + {e.with_traceback}')
                print(e.with_traceback)



