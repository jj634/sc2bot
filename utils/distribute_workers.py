# this code is adapted from bot_ai/distribute_workers

import sc2
from sc2.bot_ai import BotAI

async def distribute_workers(bot_object : BotAI):
    """
    Distributes workers across all the bases taken.
    """
    if not bot_object.mineral_field or not bot_object.workers or not bot_object.townhalls.ready:
        return
    worker_pool = [worker for worker in bot_object.workers.idle]
    bases = bot_object.townhalls.ready
    gas_buildings = bot_object.gas_buildings.ready

    # list of places that need more workers
    deficit_mining_places = []

    for mining_place in bases | gas_buildings:
        difference = mining_place.surplus_harvesters

        # too many workers
        if difference > 0: 
            if mining_place.has_vespene:
                # get all workers that target the gas extraction site
                # or are on their way back from it
                local_workers = bot_object.workers.filter(
                    lambda unit: unit.order_target == mining_place.tag
                    or (unit.is_carrying_vespene and unit.order_target == bases.closest_to(mining_place).tag)
                )
            else:
                # get tags of minerals around expansion
                local_minerals_tags = {
                    mineral.tag for mineral in bot_object.mineral_field if mineral.distance_to(mining_place) <= 8
                }
                # get all target tags a worker can have
                # tags of the minerals he could mine at that base
                # get workers that work at that gather site
                local_workers = bot_object.workers.filter(
                    lambda unit: unit.order_target in local_minerals_tags
                    or (unit.is_carrying_minerals and unit.order_target == mining_place.tag)
                )
            for worker in local_workers[:difference]:
                worker_pool.append(worker)
        # too few workers
        elif difference < 0:
            # add mining place to deficit bases for every missing worker
            deficit_mining_places += [mining_place for _ in range(-difference)]

    # prepare all minerals near a base if we have too many workers
    # and need to send them to the closest patch
    if len(worker_pool) > len(deficit_mining_places):
        all_minerals_near_base = [
            mineral
            for mineral in bot_object.mineral_field
            if any(mineral.distance_to(base) <= 8 for base in bot_object.townhalls.ready)
        ]

    # distribute every worker in the pool
    for worker in worker_pool:
        # as long as have workers and mining places
        if deficit_mining_places:
            # find closest mining place
            current_place = min(deficit_mining_places, key=lambda place: place.distance_to(worker))
            # remove it from the list
            deficit_mining_places.remove(current_place)
            # if current place is a gas extraction site, go there
            if current_place.vespene_contents:
                worker.gather(current_place)
            # if current place is a gas extraction site,
            # go to the mineral field that is near and has the most minerals left
            else:
                local_minerals = (
                    mineral for mineral in bot_object.mineral_field if mineral.distance_to(current_place) <= 8
                )
                # local_minerals can be empty if townhall is misplaced
                target_mineral = max(local_minerals, key=lambda mineral: mineral.mineral_contents, default=None)
                if target_mineral:
                    worker.gather(target_mineral)
        # more workers to distribute than free mining spots
        # send to closest if worker is doing nothing
        elif worker.is_idle and all_minerals_near_base:
            target_mineral = min(all_minerals_near_base, key=lambda mineral: mineral.distance_to(worker))
            worker.gather(target_mineral)
        else:
            # there are no deficit mining places and worker is not idle
            # so dont move him
            pass