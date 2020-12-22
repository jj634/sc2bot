import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId

class TOOBot(sc2.BotAI):
    NAME: str = "211-bot"
    """This bot's name"""
    RACE: Race = Race.Terran
    """This bot's Starcraft 2 race"""

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_step(self, iteration):
        await self.distribute_workers()

        # If we don't have a townhall anymore, send all units to attack
        ccs: Units = self.townhalls
        if not ccs:
            print("no ccs!")
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units(UnitTypeId.MARINE):
                unit.attack(target)
            return
        else:
            cc: Unit = ccs.first


        # Build supply depots, two at a time (given the money)
        # if self.supply_left < 4 and self.supply_used >= 14:
        #     if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2:
        #         print("building depot!")
        #         await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 5))

        # 14 depot
        if self.supply_used == 14 and self.can_afford(UnitTypeId.SUPPLYDEPOT):
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 5))

        if self.supply_used == 16 and self.can_afford(UnitTypeId.BARRACKS):
            await self.build(UnitTypeId.BARRACKS, near=cc.position.towards(self.game_info.map_center, 5))

        if self.supply_used == 16 and self.can_afford(UnitTypeId.REFINERY) and self.gas_buildings.amount < 1:
            # All the vespene geysirs nearby, including ones with a refinery on top of it
            vgs = self.vespene_geyser.closer_than(10, cc)
            for vg in vgs:
                if self.gas_buildings.filter(lambda unit: unit.distance_to(vg) < 1):
                    continue
                # Select a worker closest to the vespene geysir
                worker: Unit = self.select_build_worker(vg)
                # Worker can be none in cases where all workers are dead
                # or 'select_build_worker' function only selects from workers which carry no minerals
                if worker is None:
                    continue
                # Issue the build command to the worker, important: vg has to be a Unit, not a position
                worker.build_gas(vg)
                # Only issue one build geysir command per frame
                break

        if self.supply_used == 19 and self.can_afford(UnitTypeId.ORBITALCOMMAND):
            cc.build(UnitTypeId.ORBITALCOMMAND)

        if self.supply_used == 20 and self.can_afford(UnitTypeId.COMMANDCENTER):
            await self.build(UnitTypeId.COMMANDCENTER, near=cc.position.towards(self.game_info.map_center, 5))


        # Train 60 scvs
        elif self.can_afford(UnitTypeId.SCV) and self.supply_workers < 60 and cc.is_idle:
            print("training scv!")
            cc.train(UnitTypeId.SCV)

        # Idle workers should mine
        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(cc))

    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends


# def main():
#     run_game(
#         maps.get("AbyssalReefLE"),
#         [Bot(Race.Terran, TOOBot()), Computer(Race.Zerg, Difficulty.Easy)],
#         realtime=False,
#     )


# if __name__ == "__main__":
#     main()
