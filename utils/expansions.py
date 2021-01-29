from sc2.position import Point2
from sc2.bot_ai import BotAI

from typing import Dict, List

async def get_enemy_expansions(bot : BotAI) -> List[Point2]:
    """Return a list of enemy expansion locations, in order of proximity to the enemy's main."""
    
    expo_dists : Dict[Point2, float] = {}

    for expo_p in bot.expansion_locations_list:
        if expo_p.distance_to(bot.start_location) < 5:
            dist = 1000
        else:
            dist = await bot._client.query_pathing(bot.enemy_start_locations[0], expo_p)
        expo_dists[expo_p] = dist if dist else 0.0
    return sorted(bot.expansion_locations_list, key = lambda p : expo_dists[p])