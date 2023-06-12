from ..models import session
from ..models.sim_item import SimItem
from ..models.item import Item
from ..models.player import Player

class DroptimizerSummary:

    async def get_difficulty_summary(difficulty: str, min_value: int = 500) -> dict:
        
        # Get all the Sim Items with minimum value
        sim_items = session.query(SimItem).filter(SimItem.difficulty == difficulty).filter(SimItem.value >= min_value).all()

        summary = {}
        for sim in sim_items:
            item = session.query(Item).filter(Item.id == sim.item).first()
            player = session.query(Player).filter(Player.id == sim.player).first()
            if item.name not in summary:
                summary[item.name] = {}
            summary[item.name][player.name] = sim.value

        return summary