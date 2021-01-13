import sc2
from sc2.position import Point2, Point3
from sc2 import Race, Difficulty
from sc2.data import Result
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units

"""
This bot tests medivac pickup micro.
"""


class MedivacPickup(sc2.BotAI):
    async def on_start(self):
        await self.client.debug_create_unit(
            [
                [UnitTypeId.MEDIVAC, 2, self.start_location.towards(self.game_info.map_center, 5), 1],
                [UnitTypeId.MARINE, 16, self.start_location.towards(self.game_info.map_center, 5), 1],
            ]
        )

    async def on_step(self, iteration):
        await self.attack()

    async def attack(self):
        """
        Send marines to attack once there are 16 marines and 2 medivacs.
         - Marines a move to enemy main
         - Medivacs follow marines
         - Stim when in range of an enemy unit
         - When a marine falls below 20 hp, pick it up and drop it immediately ?
         - When a marine falls below 10 hp, pick it up and keep it
        """
        # MEDIVAC_RANGE = 5
        MARINE_BOOST_THRESHOLD = 30
        MARINE_PICKUP_THRESHOLD = 15

        marines = self.units(UnitTypeId.MARINE)
        medivacs = self.units(UnitTypeId.MEDIVAC)

        endangered_marines = set()

        for marine in marines:
            enemies_in_range = self.enemy_units.filter(lambda e : e.target_in_range(marine))
            if enemies_in_range:
                endangered_marines.add(marine.tag)
            if marines.amount >= 16 and medivacs.amount >= 2:
                marine.attack(self.enemy_start_locations[0])
            if enemies_in_range and not marine.has_buff(BuffId.STIMPACK):
                marine(AbilityId.EFFECT_STIM_MARINE)
        if marines:
            sorted_marines = marines.sorted(key = lambda m : m.health)
            
            for medivac in medivacs:
                medivac.attack(sorted_marines.first.position)

                endangered_marines = sorted_marines.filter(lambda m : m.tag in endangered_marines)
                enemies_in_range = self.enemy_units.filter(lambda e : e.type_id != UnitTypeId.SCV).filter(lambda e : e.target_in_range(medivac))
                # pickup marines in enemy range
                if endangered_marines:
                    lowest_endangered_marine = endangered_marines.first
                    if lowest_endangered_marine.health <= MARINE_BOOST_THRESHOLD and lowest_endangered_marine.health > MARINE_PICKUP_THRESHOLD:
                        if medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) or not self.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                            medivac.move(lowest_endangered_marine.position)
                        else:
                            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    elif lowest_endangered_marine.health <= MARINE_PICKUP_THRESHOLD:
                        medivac(AbilityId.LOAD_MEDIVAC,lowest_endangered_marine)
                if not enemies_in_range:
                    medivac(AbilityId.UNLOADALLAT_MEDIVAC)


def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Terran, MedivacPickup()), Computer(Race.Terran, Difficulty.Medium)],
        realtime=True,
        disable_fog=True,
    )


if __name__ == "__main__":
    main()