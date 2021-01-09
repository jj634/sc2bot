import sc2
from sc2 import run_game, maps, Race, Difficulty

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class TOOBot(sc2.BotAI):
    NAME: str = "211-bot"
    """This bot's name"""
    RACE: Race = Race.Terran
    """This bot's Starcraft 2 race"""

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_step(self, iteration):
        # above or below player_start_location, depending on spawn
        updown : Point2 = Point2((self.game_info.player_start_location.x, self.game_info.map_center.y))
        # to the left or right of player_start_location, depending on spawn
        leftright : Point2 = Point2((self.game_info.map_center.x, self.game_info.player_start_location.y))

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
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))

        # 15 barracks
        if self.supply_used == 15 and self.can_afford(UnitTypeId.BARRACKS) and self.already_pending(UnitTypeId.BARRACKS) == 0:
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=cc.position.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

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
        # TODO: drop mules upon completion
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
            # TODO: place at correct position
            await self.build(UnitTypeId.COMMANDCENTER, near=cc.position.towards(self.game_info.map_center, 5))

        # 20 second barracks
        if self.already_pending(UnitTypeId.COMMANDCENTER) != 0:
            if self.supply_used == 20 and self.can_afford(UnitTypeId.BARRACKS) and self.already_pending(UnitTypeId.BARRACKS) == 0:
                pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=cc.position.towards(self.game_info.map_center, 15), addon_place = True)
                await self.build(UnitTypeId.BARRACKS, near=pos)

        # 21 barracks reactor
        if self.supply_used == 21 and self.can_afford(UnitTypeId.REACTOR) and self.already_pending(UnitTypeId.BARRACKSREACTOR) == 0:
            barrack = self.structures(UnitTypeId.BARRACKS).idle.random_or(None)
            if barrack:
                # TODO: check if addon location is valid
                barrack.build(UnitTypeId.BARRACKSREACTOR)

        # 22 depot
        if self.supply_used == 22 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))

        # 22 refinery
        if self.already_pending(UnitTypeId.SUPPLYDEPOT) != 0:
            if self.supply_used == 22 and self.can_afford(UnitTypeId.REFINERY) and self.already_pending(UnitTypeId.REFINERY) == 0:
                vgs = self.vespene_geyser.closer_than(10, cc)
                for vg in vgs:
                    if self.gas_buildings.filter(lambda unit: unit.distance_to(vg) < 1):
                        continue
                    else:
                        await self.build(UnitTypeId.REFINERY, near=vg)
                        break

        # 23 factory
        if self.supply_used == 23 and self.can_afford(UnitTypeId.FACTORY) and self.already_pending(UnitTypeId.FACTORY) == 0:
            if self.tech_requirement_progress(UnitTypeId.FACTORY) == 1:
                pos : Point2 = await self.find_placement(UnitTypeId.FACTORY,near=cc.position.towards(leftright, 15), addon_place = True)
                await self.build(UnitTypeId.FACTORY, near=pos)

        # 26 barracks tech lab
        if self.supply_used == 26 and self.can_afford(UnitTypeId.TECHLAB) and self.already_pending(UnitTypeId.BARRACKSTECHLAB) == 0:
            # barrack = self.structures(UnitTypeId.BARRACKS).filter(lambda brock: not brock.has_add_on).random
            for barrack in self.structures(UnitTypeId.BARRACKS).ready:
                if not barrack.has_add_on:
                    # TODO: check if addon location is valid
                    barrack.build(UnitTypeId.BARRACKSTECHLAB)                

        # produce marines until 16
        if self.supply_used > 23 and self.units(UnitTypeId.MARINE).amount < 16:
            for barrack in self.structures(UnitTypeId.BARRACKS).ready:
                if barrack.has_add_on and len(barrack.orders) < 2:
                    barrack.train(UnitTypeId.MARINE)

        # 27 orbital on expo
        if self.supply_used > 23 and self.structures(UnitTypeId.BARRACKS).ready:
            # expo = self.townhalls.filter(lambda t : t.type_id == UnitTypeId.COMMANDCENTER).random
            for expo in self.townhalls.ready:
                if expo.type_id == UnitTypeId.COMMANDCENTER and not expo.is_transforming:
                    expo.build(UnitTypeId.ORBITALCOMMAND)

        # 28 stim
        if self.supply_used > 28:
            techlab_rax = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_techlab).random_or(None)
            if techlab_rax and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0:
                techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
                techlab.research(UpgradeId.STIMPACK)

        # 32 starport
        if self.already_pending(UnitTypeId.STARPORT) == 0 and not self.structures(UnitTypeId.STARPORT):
            if self.tech_requirement_progress(UnitTypeId.STARPORT) == 1:
                print("building starport")
                pos : Point2 = await self.find_placement(UnitTypeId.STARPORT,near=cc.position.towards(leftright, 15), addon_place = True)
                # TODO: this uses find_placement internally, so use something else
                await self.build(UnitTypeId.STARPORT, near=pos)

        # 32 factory reactor
        if self.already_pending(UnitTypeId.FACTORYREACTOR) == 0 and len(self.reactor_tags) < 2:
            factory = self.structures(UnitTypeId.FACTORY).idle.random_or(None)
            if factory:
                # TODO: check if addon location is valid
                factory.build(UnitTypeId.FACTORYREACTOR)

        # 37 depot
        if self.supply_used == 37 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))

        # 40 depot
        if self.supply_used == 40 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))

        # switch factory and starport

        # 45 double medivac

        # 53 depot
        if self.supply_used == 53 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))
        

        if (self.supply_used >= 20):
            await self.train_workers()
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