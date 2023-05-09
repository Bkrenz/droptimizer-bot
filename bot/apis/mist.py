import json
import os

import requests


class Mist:
    URL = os.getenv("MIST_REST_API_URL")

    @classmethod
    def get_applicant_by_id(cls, applicant_id):
        return requests.get(f"{cls.URL}/applicant/{applicant_id}",
                            headers={'Content-Type': "application/json"})

    @classmethod
    def get_previous_applicant_ids(cls, discord, battlenet, applicant_id):
        data = {"discord_contact": discord,
                "battlenet_contact": battlenet,
                "called_from": applicant_id}
        return requests.get(f"{cls.URL}/applicant/exists",
                            data=json.dumps(data),
                            headers={'Content-Type': "application/json"})

    @classmethod
    def put_archive_comments_by_id(cls, applicant_id, encoded_messages):
        return requests.put(f"{cls.URL}/applicant/archive/{applicant_id}",
                            data=encoded_messages,
                            headers={'Content-Type': "application/octet-stream"})
