import sc2
from sc2.position import Point2, Point3
from sc2 import Race, Difficulty
from sc2.data import Result
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId

"""
This bot tests medivac pickup micro.
"""


class StimBot(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration > 5:
            depot = self.structures(UnitTypeId.SUPPLYDEPOT)
            if not depot and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
                await self.build(UnitTypeId.SUPPLYDEPOT, near = self.start_location.towards(self.game_info.map_center, 5))
            if depot and self.already_pending(UnitTypeId.BARRACKS) == 0 and self.structures(UnitTypeId.BARRACKS).amount == 0:
                pos : Point2 = await self.find_placement(UnitTypeId.BARRACKS,near=self.start_location.towards(self.game_info.map_center, 5), addon_place = True)
                await self.build(UnitTypeId.BARRACKS, near=pos)

            for barrack in self.structures(UnitTypeId.BARRACKS).filter(lambda b : not b.has_add_on).ready:
                barrack.build(UnitTypeId.BARRACKSTECHLAB)

            techlab_rax = self.structures(UnitTypeId.BARRACKS).ready.filter(lambda b : b.has_techlab).random_or(None)
            if techlab_rax and self.already_pending_upgrade(UpgradeId.STIMPACK) == 0:
                techlab = self.structures.find_by_tag(tag = techlab_rax.add_on_tag)
                techlab.research(UpgradeId.STIMPACK)

def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Terran, StimBot()), Computer(Race.Terran, Difficulty.Medium)],
        realtime=True,
    )


if __name__ == "__main__":
    main()