import sc2
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

from typing import Set, Union



async def pickup_micro(
    bot: sc2.BotAI,
    marines : Units = None,
    medivacs: Units = None,
    endangered_marines_tags: Set[int] = set(),
    target: Point2 = None,
    retreat_point: Point2 = None
    ):
    """
    Pickup micro on medivacs and marines.
     - Marines a move to enemy main.
     - Medivacs heal lowest marines.
     - Stim when in range of an enemy unit. Marines less than EMPATHY_STIM_RANGE away from a stimmed marine will stim themselves.
     - Marines are picked up when at or below MARINE_PICKUP_THRESHOLD, and dropped off at a safe location.
    """
    MARINE_PICKUP_THRESHOLD = 10
    EMPATHY_STIM_RANGE = 10

    marines : Units = marines
    medivacs : Units = medivacs
    target : Point2 = target or bot.enemy_start_locations[0]
    retreat_point : Point2 = bot.start_location

    energy_medivacs : Units = medivacs.filter(lambda m : m.energy_percentage >= 0.1)
    for marine in marines:
        endangered_marines_nearby = marines.filter(
            lambda u : u.type_id == UnitTypeId.MARINE
                        and u.tag != marine.tag
                        and u.tag in endangered_marines_tags
                        and u.distance_to(marine) <= EMPATHY_STIM_RANGE)

        marine_endangered = marine.tag in endangered_marines_tags
        if (
            marine_endangered
            and marine.health <= MARINE_PICKUP_THRESHOLD
            and medivacs
        ):
            closest_medivac = medivacs.filter(lambda m : m.cargo_left > 0).sorted(key = lambda m : m.distance_to(marine))
            marine.smart(closest_medivac.first)
        elif (
            (marine_endangered or endangered_marines_nearby)
            and not marine.has_buff(BuffId.STIMPACK)
            and energy_medivacs
        ):
            marine(AbilityId.EFFECT_STIM_MARINE)
        else:
            marine.attack(target)


    sorted_marines = marines.sorted(key = lambda m : m.health)
    sorted_marines_iter = iter(sorted_marines)

    endangered_marines = sorted_marines.filter(lambda m : m.tag in endangered_marines_tags)
    endangered_marines_iter = iter(endangered_marines)

    for medivac in medivacs:
        if medivac.has_cargo:
            # drop off at closest safe position
            medivac_endangered = bot.enemy_units.filter(lambda e : e.target_in_range(medivac))
            if not medivac_endangered and (await bot.can_place(UnitTypeId.SENSORTOWER, [medivac.position]))[0]:
                # TODO: make sure location valid, and within expo radius
                medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
                if medivac.is_moving:
                    medivac.hold_position()
            else:
                # TODO: helper method to determine "direction" of battle
                medivac.move(retreat_point)
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
                medivac.move(retreat_point)