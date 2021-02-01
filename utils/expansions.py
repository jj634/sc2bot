from sc2.position import Point2
from sc2.bot_ai import BotAI

from typing import Dict, List

async def get_expansions(bot : BotAI, limit : int, enemy : bool) -> List[Point2]:
    """
    Return a list of expansion locations, in order of proximity to the player's main.

    :param bot:
    :param limit:
    :param enemy:
    """
    assert limit >= 0, "limit must be greater than 0"

    expo_dists : Dict[Point2, float] = {}

    own_start_loc = bot.enemy_start_locations[0] if enemy else bot.start_location
    opp_start_loc = bot.start_location if enemy else bot.enemy_start_locations[0]

    for expo_p in bot.expansion_locations_list:
        if expo_p.distance_to(opp_start_loc) < 5:
            dist = 1000
        else:
            dist = await bot._client.query_pathing(own_start_loc, expo_p)
        expo_dists[expo_p] = dist if dist else 0.0
    return sorted(bot.expansion_locations_list, key = lambda p : expo_dists[p])[0:limit]