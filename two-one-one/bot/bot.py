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
        # If we don't have a townhall anymore, send all units to attack
        ccs: Units = self.townhalls
        if ccs is None:
            print("no ccs!")
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units(UnitTypeId.MARINE):
                unit.attack(target)
            return
        else:
            cc: Unit = ccs.first


        # Build order begins

        await self.train_workers_until(19)
        # TODO: make sure that the build doesn't continue in the middle later on in the game

        # 14 depot
        if self.supply_used == 14 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 5))

        # 15 barracks
        if self.supply_used == 15 and self.can_afford(UnitTypeId.BARRACKS) and self.already_pending(UnitTypeId.BARRACKS) == 0:
            await self.build(UnitTypeId.BARRACKS, near=cc.position.towards(self.game_info.map_center, 5))

        # 16 refinery
        if self.supply_used == 16 and self.can_afford(UnitTypeId.REFINERY) and self.already_pending(UnitTypeId.REFINERY) == 0:
            # All the vespene geysers nearby, including ones with a refinery on top of it
            vgs = self.vespene_geyser.closer_than(10, cc)
            for vg in vgs:
                # check if there is already a refinery on vg
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

        # 19 orbital command
        if self.supply_used == 19 and self.can_afford(UnitTypeId.ORBITALCOMMAND):
            if self.structures(UnitTypeId.BARRACKS).ready:
                cc.build(UnitTypeId.ORBITALCOMMAND)

        # 19 reaper
        if self.supply_used == 19 and self.can_afford(UnitTypeId.REAPER):
            barrack = self.structures(UnitTypeId.BARRACKS).idle.random_or(None)
            if barrack:
                barrack.train(UnitTypeId.REAPER)

        # 20 expand
        if self.supply_used == 20 and self.can_afford(UnitTypeId.COMMANDCENTER):
            await self.build(UnitTypeId.COMMANDCENTER, near=cc.position.towards(self.game_info.map_center, 5))

        if (self.supply_used >= 20):
            await self.train_workers()

        # 20 second barracks

        # 21 barracks reactor

        # 22 depot

        # 22 refinery

        # 23 factory

        # produce marines until 16

        # 26 barracks tech lab

        # 27 orbital on expo

        # 28 stim

        # 32 starport

        # 32 factory reactor

        # 37 depot

        # 40 depot

        # 45 double medivac

        # 53 depot
        

        # TODO: improve this, see why distribute_workers doesn't work
        # await self.distribute_workers()
        for a in self.gas_buildings:
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w:
                    w.random.gather(a)
        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(cc))


        

    async def train_workers(self):
        """
        Continuously trains workers until every base has 22 workers.
        """
        # a random idle cc, or None if no idle cc's
        cc = self.townhalls.idle.random_or(None)
        if (
            cc and
            self.can_afford(UnitTypeId.SCV) and
            self.supply_workers < self.townhalls.amount * 22
        ):
            cc.train(UnitTypeId.SCV)


    async def train_workers_until(self, until_supply: int):
        """
        Continuously trains workers until the current supply is until_supply.
        :param until_supply:
        """
        # a random idle cc, or None if no idle cc's
        cc = self.townhalls.idle.random_or(None)
        if (
            cc and
            self.can_afford(UnitTypeId.SCV) and
            self.supply_used < until_supply
        ):
            cc.train(UnitTypeId.SCV)

    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends