# this is not my code! source: https://github.com/DrInfy/sharpy-sc2/blob/ea49613f74db3e9d52b1c2fc87b90814d9f7f015/sharpy/plans/acts/terran/auto_depot.py#L17

from math import ceil

import sc2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units

async def depots_required(
    bot: sc2.BotAI,
    ) -> int:
    """
    Returns the number of supply depots needed based on bot's production structures
    """
    growth_speed = 0
    townhall_count = bot.structures(
        {UnitTypeId.COMMANDCENTER, UnitTypeId.PLANETARYFORTRESS, UnitTypeId.ORBITALCOMMAND}
    ).ready.amount

    rax_count = bot.structures(UnitTypeId.BARRACKS).ready.amount
    rax_count += bot.structures(UnitTypeId.BARRACKSREACTOR).ready.amount

    factory_count = bot.structures(UnitTypeId.FACTORY).ready.amount
    factory_count += bot.structures(UnitTypeId.FACTORYREACTOR).ready.amount
    starport_count = bot.structures(UnitTypeId.STARPORT).ready.amount
    starport_count += bot.structures(UnitTypeId.STARPORTREACTOR).ready.amount

    # Probes/scv take 12 seconds to build
    # https://liquipedia.net/starcraft2/Nexus_(Legacy_of_the_Void)
    growth_speed += townhall_count / 12.0

    # https://liquipedia.net/starcraft2/Barracks_(Legacy_of_the_Void)
    # fastest usage is marauder supply with 2 supply and train 21 seconds
    growth_speed += rax_count * 2 / 21.0

    # https://liquipedia.net/starcraft2/Factory_(Legacy_of_the_Void)
    # fastest usage is helliom with 2 supply and build time of 21 seconds
    growth_speed += factory_count * 2 / 21.0

    # https://liquipedia.net/starcraft2/Starport_(Legacy_of_the_Void)
    # We'll use viking timing here
    growth_speed += starport_count * 2 / 30.0

    growth_speed *= 1.2  # Just a little bit of margin of error
    build_time = 21  # depot build time
    # build_time += min(self.ai.time / 60, 5) # probe walk time

    predicted_supply = min(200, bot.supply_used + build_time * growth_speed)
    current_depots = bot.structures(
        {UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP}
    ).ready.amount

    if bot.supply_cap == 200:
        return current_depots

    return ceil((predicted_supply - bot.supply_cap) / 8) + current_depots