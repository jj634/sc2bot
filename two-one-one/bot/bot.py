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

from routines.terran.depots_required import depots_required
from routines.terran.drop_tactics import DropTactics
from routines.terran.join_tactics import JoinTactics
from utils.expansions import get_expansions
from utils.workers_building import workers_building
from utils.distribute_workers import distribute_workers

import itertools
from typing import Dict, List, Set, Tuple


#  python .\two-one-one\run.py --Map "Acropolis LE" --ComputerDifficulty "Hard" --Realtime
class TOOBot(sc2.BotAI):
    """
    plan:
    harass as much as possible with marine drops, trying to outposition the enemy's main army
    turtle at home with walls, tanks, pfs, and turrets
     - expand to only three locations
    """
    NAME: str = "211-bot"
    RACE: Race = Race.Terran

    # number of squads to send to each harass point
    HARASS_SIZE = 2

    def __init__(self):
        self.waiting_marine_tags : Set[int] = set()
        self.waiting_medivac_tags : Set[int] = set()
        self.stranded_marine_tags : Set[int] = set()
        self.units_by_tag : Dict[int, Unit] = None
        self.enemy_expansions : List[Point2] = None
        self.own_expansions : List[Point2] = None
        self.harass_groups : Set[DropTactics] = set()
        self.harass_assignments : Dict[Point2, List[DropTactics]] = dict()
        self.join_assignments : Dict[DropTactics, List[JoinTactics]] = dict()
        self.enemy_size : int = 3

    async def on_start(self):
        # TODO: add to this if another expansion encountered, eg a ninja base
        self.enemy_expansions = await get_expansions(self, limit=8, enemy=True)
        self.own_expansions = await get_expansions(self, limit=8, enemy=False)

    async def on_step(self, iteration):
        self.units_by_tag = {unit.tag : unit for unit in self.all_own_units}

        print(list((str(point) +": "+ str(list(len(group.medivac_tags) for group in groups)) for point, groups in self.harass_assignments.items())))

        # above or below player_start_location, depending on spawn
        updown : Point2 = Point2((self.game_info.player_start_location.x, self.game_info.map_center.y))
        # to the left or right of player_start_location, depending on spawn
        leftright : Point2 = Point2((self.game_info.map_center.x, self.game_info.player_start_location.y))

        num_depots = self.structures(
            {UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP}
        ).ready.amount
        pending_depots = workers_building(self, UnitTypeId.SUPPLYDEPOT)

        num_barracks = self.structures(UnitTypeId.BARRACKS).ready.amount
        pending_barracks = workers_building(self, UnitTypeId.BARRACKS)

        num_factories = self.structures(UnitTypeId.FACTORY).ready.amount
        pending_factories = workers_building(self, UnitTypeId.FACTORY)

        num_starports = self.structures(UnitTypeId.STARPORT).ready.amount
        pending_starports = workers_building(self, UnitTypeId.STARPORT)

        num_refineries = self.gas_buildings.ready.amount
        pending_refineries = workers_building(self, UnitTypeId.REFINERY)

        num_ebays = self.structures(UnitTypeId.ENGINEERINGBAY).ready.amount
        pending_ebays = workers_building(self, UnitTypeId.ENGINEERINGBAY)

        solo_barracks = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : not b.has_add_on)

        await self.train_workers_until(19)
        # TODO: make sure that the build doesn't continue in the middle later on in the game

        if not self.townhalls.ready:
            if not self.units:
                await self.chat_send("(pineapple)")
            target : Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.units():
                unit.attack(target)
            return


# rax, refinery, orbital, reactor, expo, depot, second rax, ebay, factory, second gas, planetary, tech lab, stim, depot, starport, factory reactor, another 2 depots right after previous one, switch star/fac, double medi

        # depot
        if (
            num_depots + pending_depots == 0
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near = self.start_location.towards(updown, 3))

        # barracks
        if (
            self.tech_requirement_progress(UnitTypeId.BARRACKS) == 1
            and num_barracks + pending_barracks == 0
        ):
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near = self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        # refinery
        if (
            pending_barracks == 1
            and num_refineries + pending_refineries == 0
        ):
            # TODO: could be taken by enemy refinery
            vg_filter = lambda vg : all(vg.distance_to(refinery) > 3 for refinery in self.gas_buildings)
            unrefined_vg = self.vespene_geyser.closer_than(10, self.start_location).filter(vg_filter).random_or(None)
            if unrefined_vg:
                await self.build(UnitTypeId.REFINERY, near=unrefined_vg)

        # orbital command
        idle_cc = self.structures(UnitTypeId.COMMANDCENTER).idle
        if (
            self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) == 1
            and self.structures(UnitTypeId.ORBITALCOMMAND).amount == 0
            and idle_cc and not idle_cc.first.is_transforming
        ):
            idle_cc.first.build(UnitTypeId.ORBITALCOMMAND)

        # barracks reactor
        if  (
            self.already_pending(UnitTypeId.ORBITALCOMMAND) == 1
            and len(self.reactor_tags) + self.already_pending(UnitTypeId.BARRACKSREACTOR) == 0
            and solo_barracks.amount == 1
        ):
            solo_barracks.first.build(UnitTypeId.BARRACKSREACTOR)

        # expand
        # TODO: if blocked, make in base and lift to correct spot
        if (
            self.already_pending(UnitTypeId.BARRACKSREACTOR) == 1
            and self.townhalls.amount + self.already_pending(UnitTypeId.COMMANDCENTER) == 1
        ):
            await self.expand_now()

        # second barracks
        if (
            self.already_pending(UnitTypeId.COMMANDCENTER) == 1
            and num_barracks + pending_barracks == 1
        ):
            # TODO: check that this does not block the first barrack's addon location
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        # depot
        if (
            num_barracks == 1 and pending_barracks == 1
            and self.already_pending(UnitTypeId.COMMANDCENTER) == 1
            and num_depots + pending_depots == 1
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # ebay
        if (
            num_depots == 1 and pending_depots == 1
            and num_ebays + pending_ebays == 0
        ):
            center_vector = (self.game_info.map_center.x - self.start_location.x, self.game_info.map_center.y - self.start_location.y)
            build_direction = (self.start_location.x - center_vector[0], self.start_location.y - center_vector[1])
            await self.build(UnitTypeId.ENGINEERINGBAY, near= self.start_location.towards(Point2(build_direction), 10))

        # factory
        if (
            num_ebays == 0 and pending_ebays == 1
            and self.tech_requirement_progress(UnitTypeId.FACTORY) == 1
            and num_factories + pending_factories + self.structures(UnitTypeId.FACTORYFLYING).amount == 0
        ):
            pos : Point2 = await self.find_placement(UnitTypeId.FACTORY,near=self.start_location.towards(leftright, 5), addon_place = True)
            await self.build(UnitTypeId.FACTORY, near=pos)

        # second gas
        if (
            num_factories == 0 and pending_factories == 1
            and num_refineries == 1 and pending_refineries == 0
        ):
            # TODO: could be taken by enemy refinery
            vg_filter = lambda vg : all(vg.distance_to(refinery) > 3 for refinery in self.gas_buildings)
            unrefined_vg = self.vespene_geyser.closer_than(10, self.start_location).filter(vg_filter).random_or(None)
            if unrefined_vg:
                await self.build(UnitTypeId.REFINERY, near=unrefined_vg)

        # planetary
        if (
            self.structures(UnitTypeId.ORBITALCOMMAND).amount == 1
            and self.tech_requirement_progress(UnitTypeId.PLANETARYFORTRESS) == 1
            and idle_cc and not idle_cc.first.is_transforming
        ):
            idle_cc.first.build(UnitTypeId.PLANETARYFORTRESS)

        # barracks tech lab
        if (
            self.already_pending(UnitTypeId.PLANETARYFORTRESS) == 1
            and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0
            and self.already_pending(UnitTypeId.BARRACKSTECHLAB) == 0
            and solo_barracks
        ):
            solo_barracks.first.build(UnitTypeId.BARRACKSTECHLAB)

        # constantly produce marines
        # TODO: when loaded in medivacs, the number of marines decreases
        for barrack in self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_add_on):
            if len(barrack.orders) < 1 + int(barrack.add_on_tag in self.reactor_tags):
                barrack.train(UnitTypeId.MARINE)

        # stim check before star
        techlab_rax = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_techlab).random_or(None)
        if (
            techlab_rax
            and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0
        ):
            techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
            techlab.research(UpgradeId.STIMPACK)

        # depot
        if (
            self.already_pending_upgrade(UpgradeId.STIMPACK) > 0
            and num_depots == 2 and pending_depots == 0
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # starport
        if (
            self.already_pending_upgrade(UpgradeId.STIMPACK) > 0
            and num_starports + pending_starports == 0
            and not self.structures(UnitTypeId.STARPORTFLYING)
        ):
            if self.tech_requirement_progress(UnitTypeId.STARPORT) == 1:
                pos : Point2 = await self.find_placement(UnitTypeId.STARPORT,near=self.start_location.towards(leftright, 10), addon_place = True)
                # TODO: this uses find_placement internally, so use something else
                await self.build(UnitTypeId.STARPORT, near=pos)

        # factory reactor
        if (
            pending_starports == 1
            and len(self.reactor_tags) + self.already_pending(UnitTypeId.FACTORYREACTOR) == 1
        ):
            factory = self.structures(UnitTypeId.FACTORY).idle.random_or(None)
            if factory:
                # TODO: check if addon location is valid
                factory.build(UnitTypeId.FACTORYREACTOR)

        # depot
        if (
            len(self.reactor_tags) == 2
            and num_depots == 3 and pending_depots == 0
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.towards(updown, 3))

        # depot
        if (
            num_depots == 4 and pending_depots == 0
        ):
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
            num_depots >= 5
            and (await depots_required(self)) > num_depots + pending_depots
        ):
            await self.build(UnitTypeId.SUPPLYDEPOT, near= self.start_location.position.towards(updown, 3))

        # combat shields
        if (
            techlab_rax
            and self.already_pending_upgrade(UpgradeId.STIMPACK) == 1
            and self.already_pending_upgrade(UpgradeId.SHIELDWALL) == 0
        ):
            techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
            techlab.research(UpgradeId.SHIELDWALL)

        # more barracks
        if (
            num_starports == 1
            and self.already_pending_upgrade(UpgradeId.SHIELDWALL) > 0
            and pending_barracks + self.structures(UnitTypeId.BARRACKS).ready.amount < min((self.townhalls.amount * 3) - 1, 8)
        ):
            # TODO: check that this does not block the first barrack's addon location
            pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 15), addon_place = True)
            await self.build(UnitTypeId.BARRACKS, near=pos)

        if (
            self.already_pending_upgrade(UpgradeId.STIMPACK) > 0
            and solo_barracks
        ):
            solo_barracks.first.build(UnitTypeId.BARRACKSREACTOR)

        # handle waiting marines and medivacs
        self.waiting_marine_tags = self.waiting_marine_tags & self.units_by_tag.keys()
        self.waiting_medivac_tags = self.waiting_medivac_tags & self.units_by_tag.keys()

        waiting_marines : Units = Units({self.units_by_tag[m_tag] for m_tag in self.waiting_marine_tags}, self)
        waiting_medivacs : Units = Units({self.units_by_tag[m_tag] for m_tag in self.waiting_medivac_tags}, self)

        chill_spot = self.own_expansions[self.townhalls.amount > 0].towards(self.game_info.map_center, 7)
        for unit in (waiting_marines + waiting_medivacs).filter(lambda u : u.distance_to(chill_spot) > 5):
            unit.attack(chill_spot)

        # handle attack groups

        needs_regroup_groups : Set[DropTactics] = set()
        perished_groups : Set[DropTactics] = set()
        for group in self.harass_groups:
            needs_regroup = await group.handle(self.units_by_tag)
            perished = group.perished(self.units_by_tag)
            if needs_regroup:
                needs_regroup_groups.add(group)
            elif perished:
                perished_groups.add(group)

        for group in needs_regroup_groups | perished_groups:
            if group in needs_regroup_groups:
                self.waiting_marine_tags |= group.marine_tags
                self.waiting_medivac_tags |= group.medivac_tags
            elif group in perished_groups:
                self.stranded_marine_tags |= group.marine_tags
            
            self.harass_groups.remove(group)
            self.harass_assignments[group.targets[0]].remove(group)
            
            joiners : List[JoinTactics] = self.join_assignments[group]
            if joiners:
                new_drop_tactics = DropTactics(
                    marine_tags=joiners[0].marine_tags,
                    medivac_tags=joiners[0].medivac_tags,
                    targets=group.targets,
                    retreat_point=group.retreat_point,
                    bot_object=self,
                    walk=False
                )
                
                if len(joiners) > 1:
                    joiners[1].assignment = new_drop_tactics

                self.join_assignments[new_drop_tactics] = joiners[1:]
                self.harass_groups.add(new_drop_tactics)

                current_groups = self.harass_assignments.get(new_drop_tactics.targets[0]) or []
                current_groups.append(new_drop_tactics)
                self.harass_assignments[new_drop_tactics.targets[0]] = current_groups
            del self.join_assignments[group]

        # harass
        if self.already_pending_upgrade(UpgradeId.STIMPACK) >= 0.9:
            while (
                len(self.waiting_marine_tags) >= 8
                and len(self.waiting_medivac_tags) >= 1
            ):
                print("new group!")
                new_harass_marine_tags = set(itertools.islice(self.waiting_marine_tags, 8))
                new_harass_medivac_tags = set(itertools.islice(self.waiting_medivac_tags, 1))

                self.waiting_marine_tags.difference_update(new_harass_marine_tags)
                self.waiting_medivac_tags.difference_update(new_harass_medivac_tags)

                heuristic_scores : Dict[Tuple[Point2, int], int] = dict()
                for enemy_base_i in range(self.enemy_size):
                    enemy_base = self.enemy_expansions[enemy_base_i]
                    for harass_i in range(self.HARASS_SIZE):
                        index = enemy_base_i + self.enemy_size * harass_i

                        enemy_base_squads = self.harass_assignments.get(enemy_base) or []
                        squad_size = 0
                        if harass_i < len(enemy_base_squads):
                            current_squad = enemy_base_squads[harass_i]
                            squad_size += len(current_squad.medivac_tags)
                            joiners = self.join_assignments[current_squad]
                            if joiners:
                                squad_size += sum(len(joiner.medivac_tags) for joiner in joiners)

                        heuristic_scores[(enemy_base, harass_i)] = index + squad_size * 1000

                best_match : Tuple[Point2, int] = min(heuristic_scores.keys(), key = lambda t : heuristic_scores[t])
                print(f"heuristic: {best_match[0]}, {best_match[1]}")
                print(list(self.harass_assignments.keys()))
                if best_match[0] in self.harass_assignments.keys() and best_match[1] < len(self.harass_assignments[best_match[0]]):
                    # there is an existing DropTactics. create a JoinTactics group
                    print("adding new join tactics")
                    existing_drop_tactic = self.harass_assignments[best_match[0]][best_match[1]]
                    existing_join_tactics = self.join_assignments[existing_drop_tactic]
                    next_assignment = existing_join_tactics[len(existing_join_tactics) - 1] if existing_join_tactics else existing_drop_tactic
                    new_join_tactics = JoinTactics(
                        marine_tags=new_harass_marine_tags,
                        medivac_tags=new_harass_medivac_tags,
                        bot_object=self,
                        assignment=next_assignment
                    )

                    self.join_assignments[existing_drop_tactic].append(new_join_tactics)
                else:
                    # there is not an existing DropTactics. create a new DropTactics group
                    print("adding new drop tactics")
                    new_drop_tactics = DropTactics(
                        marine_tags=new_harass_marine_tags,
                        medivac_tags=new_harass_medivac_tags,
                        targets=[best_match[0], self.enemy_start_locations[0]],
                        retreat_point=self.own_expansions[self.townhalls.amount > 0],
                        bot_object=self,
                        walk=False
                    )
                    current_groups = self.harass_assignments.get(best_match[0]) or []
                    current_groups.append(new_drop_tactics)
                    self.harass_assignments[best_match[0]] = current_groups
                    self.harass_groups.add(new_drop_tactics)
                    self.join_assignments[new_drop_tactics] = []

        for main_drop, join_groups in self.join_assignments.items():
            for join_group_i in range(len(join_groups)):
                join_group : JoinTactics = join_groups[join_group_i]
                arrived = await join_group.handle(self.units_by_tag)
                if join_group.assignment.perished(self.units_by_tag):
                    assert type(join_group.assignment) == JoinTactics, "somehow a drop tactics slipped by"
                    next_assignment = join_group.assignment
                    while next_assignment.perished(self.units_by_tag):
                        join_groups.remove(next_assignment)
                        next_assignment = next_assignment.assignment
                    join_group.assignment = next_assignment
                elif arrived:
                    join_group.assignment.marine_tags = join_group.assignment.marine_tags | join_group.marine_tags
                    join_group.assignment.medivac_tags = join_group.assignment.medivac_tags | join_group.medivac_tags

                    if join_group_i + 1 < len(join_groups):
                        arrived_joiner = join_groups[join_group_i + 1]
                        arrived_joiner.assignment = join_group.assignment

                    self.join_assignments[main_drop].remove(join_group)


        # drop mules
        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            # TODO: include mineral fields close to any cc
            mfs: Units = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

        await distribute_workers(self)

        await self.train_workers()

    async def train_workers(self):
        """
        Continuously trains workers until every base has 22 workers.
        """
        # a random idle cc, or None if no idle cc's
        idle_cc = self.townhalls({UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS}).idle.random_or(None)
        if (
            idle_cc
            and self.supply_workers + self.already_pending(UnitTypeId.SCV) < self.townhalls.amount * 22
        ):
            idle_cc.train(UnitTypeId.SCV)


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
        if unit.type_id == UnitTypeId.MARINE:
            self.waiting_marine_tags.add(unit.tag)
        elif unit.type_id == UnitTypeId.MEDIVAC:
            self.waiting_medivac_tags.add(unit.tag)

    async def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends