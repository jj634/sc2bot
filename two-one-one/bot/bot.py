import sc2
from sc2 import run_game, maps, Race, Difficulty

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

import sys
sys.path.append(".") # Adds higher directory to python modules path.

from routines.terran.medivac_pickup import pickup_micro
from routines.terran.depots_required import depots_required


#  python .\two-one-one\run.py --Map "Acropolis LE" --ComputerDifficulty "Hard" --Realtime
class TOOBot(sc2.BotAI):
    NAME: str = "211-bot"
    """This bot's name"""
    RACE: Race = Race.Terran
    """This bot's Starcraft 2 race"""

    reaper_created = False

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_step(self, iteration):
        # above or below player_start_location, depending on spawn
        updown : Point2 = Point2((self.game_info.player_start_location.x, self.game_info.map_center.y))
        # to the left or right of player_start_location, depending on spawn
        leftright : Point2 = Point2((self.game_info.map_center.x, self.game_info.player_start_location.y))

        # If we don't have a townhall anymore, send all units to attack
        if not self.townhalls.ready:
            print("no ccs!")
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.units():
                unit.attack(target)
            return


        # Build order begins

        finished_depots = self.structures(
            {UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP}
        ).ready.amount

        num_depots = self.structures(UnitTypeId.SUPPLYDEPOT).amount
        pending_depots = self.already_pending(UnitTypeId.SUPPLYDEPOT)

        num_barracks = self.structures(UnitTypeId.BARRACKS).amount
        pending_barracks = self.already_pending(UnitTypeId.BARRACKS)

        num_factories = self.structures(UnitTypeId.FACTORY).amount
        pending_factories = self.already_pending(UnitTypeId.FACTORY)

        num_starports = self.structures(UnitTypeId.STARPORT).amount
        pending_starports = self.already_pending(UnitTypeId.STARPORT)

        num_refineries = self.gas_buildings.amount
        pending_refineries = self.already_pending(UnitTypeId.REFINERY)

        solo_barracks = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : not b.has_add_on)

        await self.train_workers_until(19)
        # TODO: make sure that the build doesn't continue in the middle later on in the game

        # 14 depot
        if (
            num_depots + pending_depots == 0
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near = self.start_location.towards(updown, 3))

        # 15 barracks
        if (
            self.tech_requirement_progress(UnitTypeId.BARRACKS) == 1
            and num_barracks + pending_barracks == 0
        ):
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near = self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        # 16 refinery
        if (
            num_barracks == 1
            and num_refineries + pending_refineries == 0
        ):
            # TODO: could be taken by enemy refinery
            vg_filter = lambda vg : all(vg.distance_to(refinery) > 3 for refinery in self.gas_buildings)
            unrefined_vg = self.vespene_geyser.closer_than(10, self.start_location).filter(vg_filter).random_or(None)
            if unrefined_vg:
                await self.build(UnitTypeId.REFINERY, near=unrefined_vg)

        # 19 orbital command
        idle_cc = self.structures(UnitTypeId.COMMANDCENTER).idle
        if (
            self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) == 1
            and idle_cc and not idle_cc.first.is_transforming
        ):
            idle_cc.first.build(UnitTypeId.ORBITALCOMMAND)

        # 19 reaper
        # TODO: skip reaper
        barrack = self.structures(UnitTypeId.BARRACKS).ready
        if (
            self.already_pending(UnitTypeId.ORBITALCOMMAND) > 0
            and barrack 
            and self.units(UnitTypeId.REAPER).amount + self.already_pending(UnitTypeId.REAPER) == 0
            and not self.reaper_created
        ):
            barrack.first.train(UnitTypeId.REAPER)

        # 20 expand
        if (
            self.already_pending(UnitTypeId.REAPER) > 0
            and self.townhalls.amount + self.already_pending(UnitTypeId.COMMANDCENTER) == 1
        ):
            await self.expand_now()

        # 20 second barracks
        if (
            self.already_pending(UnitTypeId.COMMANDCENTER) > 0
            and num_barracks + pending_barracks == 1
        ):
            # TODO: check that this does not block the first barrack's addon location
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        # 21 barracks reactor
        if  (
            pending_barracks == 1
            and len(self.reactor_tags) + self.already_pending(UnitTypeId.BARRACKSREACTOR) == 0
            and self.reaper_created
            and solo_barracks
        ):
            solo_barracks.first.build(UnitTypeId.BARRACKSREACTOR)

        if (self.structures(UnitTypeId.ORBITALCOMMAND).ready):
            await self.train_workers()

        # 22 depot
        if (
            self.already_pending(UnitTypeId.BARRACKSREACTOR) == 1
            and num_depots + pending_depots == 1
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # 22 refinery
        if (
            pending_depots == 1
            and num_refineries + pending_refineries == 1
        ):
            # TODO: could be taken by enemy refinery
            vg_filter = lambda vg : all(vg.distance_to(refinery) > 3 for refinery in self.gas_buildings)
            unrefined_vg = self.vespene_geyser.closer_than(10, self.start_location).filter(vg_filter).random_or(None)
            if unrefined_vg:
                await self.build(UnitTypeId.REFINERY, near=unrefined_vg)

        # 23 factory
        if (
            num_refineries == 2
            and self.tech_requirement_progress(UnitTypeId.FACTORY) == 1
            and num_factories + pending_factories + self.structures(UnitTypeId.FACTORYFLYING).amount == 0
        ):
            pos : Point2 = await self.find_placement(UnitTypeId.FACTORY,near=self.start_location.towards(leftright, 5), addon_place = True)
            await self.build(UnitTypeId.FACTORY, near=pos)

        # 26 barracks tech lab
        if (
            pending_factories == 1
            and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0
            and self.already_pending(UnitTypeId.BARRACKSTECHLAB) == 0
        ):
            if solo_barracks:
                solo_barracks.first.build(UnitTypeId.BARRACKSTECHLAB)

        # constantly produce marines
        # TODO: when loaded in medivacs, the number of marines decreases
        for barrack in self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_add_on):
            if len(barrack.orders) < 1 + int(barrack.add_on_tag in self.reactor_tags):
                barrack.train(UnitTypeId.MARINE)

        # 27 orbital on expo

        # 28 stim
        techlab_rax = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_techlab).random_or(None)
        if (
            techlab_rax
            and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0
        ):
            techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
            techlab.research(UpgradeId.STIMPACK)

        # 32 starport
        if (
            num_starports + pending_starports == 0
            and not self.structures(UnitTypeId.STARPORTFLYING)
        ):
            if self.tech_requirement_progress(UnitTypeId.STARPORT) == 1:
                pos : Point2 = await self.find_placement(UnitTypeId.STARPORT,near=self.start_location.towards(leftright, 10), addon_place = True)
                # TODO: this uses find_placement internally, so use something else
                await self.build(UnitTypeId.STARPORT, near=pos)

        # 32 factory reactor
        if (
            pending_starports == 1
            and len(self.reactor_tags) + self.already_pending(UnitTypeId.FACTORYREACTOR) == 1
        ):
            factory = self.structures(UnitTypeId.FACTORY).idle.random_or(None)
            if factory:
                # TODO: check if addon location is valid
                factory.build(UnitTypeId.FACTORYREACTOR)

        # 37 depot
        if (
            len(self.reactor_tags) == 2
            and num_depots == 2
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # 40 depot
        if num_depots == 3:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # switch factory and starport
        star : Unit = self.structures(UnitTypeId.STARPORT).ready.random_or(None)
        fac : Unit = self.structures(UnitTypeId.FACTORY).ready.random_or(None)
        starflying : Unit = self.structures(UnitTypeId.STARPORTFLYING).random_or(None)
        facflying : Unit = self.structures(UnitTypeId.FACTORYFLYING).random_or(None)
        if star and not star.has_reactor:
            star(AbilityId.LIFT)
        elif fac and fac.has_reactor and starflying:
            fac(AbilityId.LIFT)
        elif starflying and fac and starflying.is_idle:
            starflying.move(fac.position)
        elif starflying and facflying and starflying.is_idle:
            starflying(AbilityId.LAND,facflying.position)
        elif facflying and facflying.is_idle:
            pos : Point2 = await self.find_placement(UnitTypeId.FACTORY,near=self.start_location.towards(leftright, 5))
            facflying(AbilityId.LAND,pos)

        # continually train medivacs
        for starport in self.structures(UnitTypeId.STARPORT).ready.filter(lambda s : s.has_add_on):
            if len(starport.orders) < 2:
                starport.train(UnitTypeId.MEDIVAC)

        # continually build depots
        if (
            num_depots > 3
            and (await depots_required(self)) > finished_depots + pending_depots
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.position.towards(updown, 3))

        if self.already_pending_upgrade(UpgradeId.STIMPACK) == 1:
            await pickup_micro(self)

        # more barracks
        if (
            num_starports == 1
            and pending_barracks + self.structures(UnitTypeId.BARRACKS).ready.amount < (self.townhalls.amount * 3) - 1
        ):
            # TODO: check that this does not block the first barrack's addon location
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        if (
            self.already_pending_upgrade(UpgradeId.STIMPACK) > 0
            and solo_barracks
        ):
            solo_barracks.first.build(UnitTypeId.BARRACKSREACTOR)

        # drop mules
        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            # TODO: include mineral fields close to any cc
            mfs: Units = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

        # TODO: improve this, see why distribute_workers doesn't work
        # await self.distribute_workers()
        for a in self.gas_buildings:
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w:
                    w.random.gather(a)
        for scv in self.workers.idle:
            # TODO: set rally, distribute workers to expo
            scv.gather(self.mineral_field.closest_to(self.start_location))

    async def train_workers(self):
        """
        Continuously trains workers until every base has 22 workers.
        """
        # a random idle cc, or None if no idle cc's
        cc = self.townhalls(UnitTypeId.ORBITALCOMMAND).idle.random_or(None)
        if (
            cc and
            self.can_afford(UnitTypeId.SCV) and
            self.supply_workers + self.already_pending(UnitTypeId.SCV) < self.townhalls.amount * 22
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

    async def on_unit_created(self, unit: Unit):
        if unit.type_id == UnitTypeId.REAPER:
            self.reaper_created = True

    async def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends