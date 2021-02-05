import sc2
from sc2.cache import property_cache_once_per_frame_no_copy
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId

from collections import Counter


@property_cache_once_per_frame_no_copy
def _abilities_all_units(bot_object : BotAI) -> Counter:
    """ Cache for the already_pending function """
    abilities_amount = Counter()
    for unit in bot_object.units({UnitTypeId.SCV, UnitTypeId.DRONE, UnitTypeId.PROBE}):
        for order in unit.orders:
            abilities_amount[order.ability] += 1

    return abilities_amount

def workers_building(bot_object : BotAI, unit_type: UnitTypeId) -> float:
    """
    Returns a number of buildings or units already in progress, or if a
    worker is en route to build it.

    :param unit_type:
    """
    ability = bot_object._game_data.units[unit_type.value].creation_ability
    return bot_object._abilities_all_units[0][ability]