import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId


class TOOBot(sc2.BotAI):
    async def on_step(self, iteration):
        # If we don't have a townhall anymore, send all units to attack
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER)
        if not ccs:
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units(UnitTypeId.MARINE):
                unit.attack(target)
            return
        else:
            cc: Unit = ccs.first
        # Train more SCVs
        if self.can_afford(UnitTypeId.SCV) and self.supply_workers < 15 and cc.is_idle:
            cc.train(UnitTypeId.SCV)


def main():
    run_game(
        maps.get("AbyssalReefLE"),
        [Bot(Race.Terran, TOOBot()), Computer(Race.Zerg, Difficulty.Hard)],
        realtime=False,
    )


if __name__ == "__main__":
    main()
