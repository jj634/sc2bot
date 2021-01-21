import sc2
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from typing import Union



async def pickup_micro(
    bot: sc2.BotAI,
    marines : Units = None,
    medivacs: Units = None,
    target: Union[Unit, Point2, Point3] = None
    ):
    """
    Pickup micro on medivacs and marines.
        - Marines a move to enemy main.
        - Medivacs heal lowest marines.
        - Stim when in range of an enemy unit. Marines less than 10 away from a stimmed marine will stim themselves.
        - Marines are picked up when at or below 15 HP, and dropped off at a safe location.
    """
    MARINE_PICKUP_THRESHOLD = 15
    EMPATHY_STIM_RANGE = 10

    marines = marines or bot.units(UnitTypeId.MARINE)
    medivacs = medivacs or bot.units(UnitTypeId.MEDIVAC)
    target = target or bot.enemy_start_locations[0]

    endangered_marines_tags = set()

    for marine in marines:
        if marine.health <= 5:
            closest_medivac = medivacs.sorted(key = lambda m : m.distance_to(marine))
            if closest_medivac:
                marine.move(closest_medivac.first)
            else:
                marine.move(bot.start_location)
        else:
            marine.attack(target)

        enemies_in_range = bot.enemy_units.filter(lambda e : e.target_in_range(marine))
        stimmed_marines_nearby = marines.filter(lambda u : u.type_id == UnitTypeId.MARINE and u.tag != marine.tag and u.has_buff(BuffId.STIMPACK) and u.distance_to(marine) <= EMPATHY_STIM_RANGE)
        if enemies_in_range:
            endangered_marines_tags.add(marine.tag)
        if (enemies_in_range or stimmed_marines_nearby) and not marine.has_buff(BuffId.STIMPACK):
            # TODO: stim only when medivac with energy nearby
            marine(AbilityId.EFFECT_STIM_MARINE)

    sorted_marines = marines.sorted(key = lambda m : m.health)
    sorted_marines_iter = iter(sorted_marines)

    endangered_marines = sorted_marines.filter(lambda m : m.tag in endangered_marines_tags)
    endangered_marines_iter = iter(endangered_marines)

    for medivac in medivacs:
        if medivac.has_cargo:
            # drop off at closest safe position
            medivac_endangered = bot.enemy_units.filter(lambda e : e.type_id != UnitTypeId.SCV and e.target_in_range(medivac))
            if medivac_endangered:
                # TODO: helper method to determine "direction" of battle
                medivac.move(bot.start_location)
            else:
                medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
        elif not (len(medivac.orders) > 0 and medivac.orders[0].ability.id == AbilityId.LOAD_MEDIVAC):
            next_endangered_marine = next(endangered_marines_iter, None)
            if next_endangered_marine:
                if not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) and await bot.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                    medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                elif next_endangered_marine.health <= MARINE_PICKUP_THRESHOLD:
                    # move and load
                    medivac(AbilityId.LOAD_MEDIVAC,next_endangered_marine)
                else:
                    medivac(AbilityId.MEDIVACHEAL_HEAL, next_endangered_marine)
            elif marines:
                next_marine = next(sorted_marines_iter, sorted_marines.random_or(None))
                if next_marine:
                    medivac.attack(next_marine.position)
            else:
                # no marines
                medivac.move(bot.start_location)