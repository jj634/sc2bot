import sc2
from sc2 import run_game, maps, Race, Difficulty

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId


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
        ccs: Units = self.townhalls.ready
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
            await self.expand_now()

        # 20 second barracks
        if self.already_pending(UnitTypeId.COMMANDCENTER) != 0:
            if self.supply_used == 20 and self.can_afford(UnitTypeId.BARRACKS) and self.already_pending(UnitTypeId.BARRACKS) == 0:
                pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
                await self.build(UnitTypeId.BARRACKS, near=pos)

        # 21 barracks reactor
        if self.supply_used == 21 and self.can_afford(UnitTypeId.REACTOR) and self.already_pending(UnitTypeId.BARRACKSREACTOR) == 0:
            barrack = self.structures(UnitTypeId.BARRACKS).idle.random_or(None)
            if barrack:
                # TODO: check if addon location is valid
                barrack.build(UnitTypeId.BARRACKSREACTOR)

        if (self.supply_used >= 20):
            await self.train_workers()

        # 22 depot
        if self.supply_used == 22 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

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
                pos : Point2 = await self.find_placement(UnitTypeId.FACTORY,near=self.start_location.towards(leftright, 5), addon_place = True)
                await self.build(UnitTypeId.FACTORY, near=pos)

        # 26 barracks tech lab
        if self.supply_used == 26 and self.can_afford(UnitTypeId.TECHLAB) and self.already_pending(UnitTypeId.BARRACKSTECHLAB) == 0:
            # barrack = self.structures(UnitTypeId.BARRACKS).filter(lambda brock: not brock.has_add_on).random
            for barrack in self.structures(UnitTypeId.BARRACKS).ready:
                if not barrack.has_add_on:
                    # TODO: check if addon location is valid
                    barrack.build(UnitTypeId.BARRACKSTECHLAB)                

        # produce marines until 16
        # TODO: when loaded in medivacs, the number of marines decreases
        if self.supply_used > 23 and self.units(UnitTypeId.MARINE).amount + self.already_pending(UnitTypeId.MARINE) < 16:
            for barrack in self.structures(UnitTypeId.BARRACKS).ready:
                if barrack.has_add_on:
                    if len(barrack.orders) < 1 + int(barrack.add_on_tag in self.reactor_tags):
                        barrack.train(UnitTypeId.MARINE)

        # 27 orbital on expo
        if self.supply_used > 23 and self.structures(UnitTypeId.BARRACKS).ready:
            # expo = self.townhalls.filter(lambda t : t.type_id == UnitTypeId.COMMANDCENTER).random
            for expo in self.townhalls.ready:
                if expo.type_id == UnitTypeId.COMMANDCENTER and not expo.is_transforming and self.already_pending(UnitTypeId.ORBITALCOMMAND) == 0:
                    expo.build(UnitTypeId.ORBITALCOMMAND)

        # 28 stim
        if self.supply_used > 28:
            techlab_rax = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_techlab).random_or(None)
            if techlab_rax and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0:
                techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
                techlab.research(UpgradeId.STIMPACK)

        # 32 starport
        if self.already_pending(UnitTypeId.STARPORT) == 0 and not self.structures(UnitTypeId.STARPORT) and not self.structures(UnitTypeId.STARPORTFLYING):
            if self.tech_requirement_progress(UnitTypeId.STARPORT) == 1:
                pos : Point2 = await self.find_placement(UnitTypeId.STARPORT,near=self.start_location.towards(leftright, 10), addon_place = True)
                # TODO: this uses find_placement internally, so use something else
                await self.build(UnitTypeId.STARPORT, near=pos)

        # 32 factory reactor
        if self.already_pending(UnitTypeId.STARPORT) != 0:
            if self.already_pending(UnitTypeId.FACTORYREACTOR) == 0 and len(self.reactor_tags) < 2:
                factory = self.structures(UnitTypeId.FACTORY).idle.random_or(None)
                if factory:
                    # TODO: check if addon location is valid
                    factory.build(UnitTypeId.FACTORYREACTOR)

        # 37 depot
        if len(self.reactor_tags) == 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.structures(UnitTypeId.SUPPLYDEPOT).amount == 2:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # 40 depot
        if self.structures(UnitTypeId.SUPPLYDEPOT).amount == 3 and self.can_afford(UnitTypeId.SUPPLYDEPOT):
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

        # 45 double medivac
        if star and star.has_reactor and self.units(UnitTypeId.MEDIVAC).amount + self.already_pending(UnitTypeId.MEDIVAC) < 2:
            starport = self.structures(UnitTypeId.STARPORT).ready.random_or(None)
            if starport:
                starport.train(UnitTypeId.MEDIVAC)

        # 53 depot
        if self.units(UnitTypeId.MEDIVAC).amount + self.already_pending(UnitTypeId.MEDIVAC) == 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.structures(UnitTypeId.SUPPLYDEPOT).amount == 4:
            await self.build(UnitTypeId.SUPPLYDEPOT, near= cc.position.towards(updown, 3))

        await self.attack()

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
            scv.gather(self.mineral_field.closest_to(cc))

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

        for marine in marines:
            enemies_in_range = self.enemy_units.filter(lambda e : marine.ground_range >= marine.distance_to(e) + 1)
            if marines.amount >= 16 and medivacs.amount >= 2:
                marine.attack(self.enemy_start_locations[0])
            if enemies_in_range and not marine.has_buff(BuffId.STIMPACK):
                marine(AbilityId.EFFECT_STIM_MARINE)
        if marines:
            sorted_marines = marines.sorted(key = lambda m : m.health)
            for medivac in medivacs:        
                lowest_marine = sorted_marines.first
                medivac.attack(lowest_marine.position)

                if lowest_marine.health <= MARINE_BOOST_THRESHOLD and lowest_marine.health > MARINE_PICKUP_THRESHOLD:
                    if medivac.has_buff(BuffId.MEDIVACSPEEDBOOST) or not self.can_cast(medivac,AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS):
                        medivac.move(lowest_marine.position)
                    else:
                        medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                elif lowest_marine.health <= MARINE_PICKUP_THRESHOLD:
                    medivac(AbilityId.LOAD_MEDIVAC,lowest_marine)



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

    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends