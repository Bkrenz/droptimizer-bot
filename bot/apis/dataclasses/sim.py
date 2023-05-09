from dataclasses import dataclass


@dataclass
class Sim:
    info: str
    base_dps: float
    sim_dps: float
    sim_difference: float
    raid_id: int
    boss_id: int
    difficulty: str
    item_id: int
    item_slot: int

    def __init__(self, info, base_dps, sim_dps):
        info_split = info.split('/')
        self.info = info
        self.base_dps = base_dps
        self.sim_dps = sim_dps
        self.sim_difference = self.sim_dps - self.base_dps
        self.raid_id = info_split[0]
        self.boss_id = info_split[1]
        self.difficulty = info_split[2].split('-')[-1]
        self.item_id = info_split[3]
        self.item_slot = info_split[5]
