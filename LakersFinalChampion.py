import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SIEGETANK, SCV,SUPPLYDEPOT,REFINERY, BARRACKS, MARINE, BANSHEE, BARRACKSTECHLAB,BARRACKSREACTOR,\
MARAUDER,LIFT_BARRACKS,LAND_BARRACKS,BARRACKSFLYING,ENGINEERINGBAY,ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,RESEARCH_COMBATSHIELD,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,RESEARCH_CONCUSSIVESHELLS,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3,ARMORY,FACTORY,ATTACK_ATTACKTOWARDS,PATROL,SCAN_MOVE,RALLY_UNITS

import time
import math


class LFC(sc2.BotAI):
    def __init__(self, use_model=True):
        self.combinedActions = []
        self.enemy_expand_location = None
        self.first_supply_built=False
        self.counter_units = {BANSHEE: [[MARINE, 3]], MARINE: [SIEGETANK, 0.3], SIEGETANK: [[BANSHEE, 1]]}


    async def on_game_start(self):
        for worker in self.workers:
            closest_mineral_patch = self.state.mineral_field.closest_to(worker)
            self.combinedActions.append(worker.gather(closest_mineral_patch))
            await self.do_actions(self.combinedActions)
        self.enemy_expand_location = await self.find_enemy_expand_location()

    async def find_enemy_expand_location(self):
        closest = None
        distance = math.inf
        for el in self.expansion_locations:
            def too_near_to_expansion(t):
                return t.position.distance_to(el) < self.EXPANSION_GAP_THRESHOLD

            if too_near_to_expansion(sc2.position.Point2(self.enemy_start_locations[0])):
                continue

            d = await self._client.query_pathing(self.enemy_start_locations[0], el)
            if d is None:
                continue

            if d < distance:
                distance = d
                closest = el
        return closest

    async def on_step(self, iteration):

        if iteration == 0:
            await self.on_game_start()
            return


        await self.distribute_workers()
        await self.build_workers()
        await self.build_supply()
#        await self.build_assimilators()
#        await self.expand()
#        await self.offensive_force_buildings()
#        await self.build_offensive_force()

    async def build_workers(self):
        for cc in self.units(COMMANDCENTER).ready.noqueue:
            workers = len(self.units(SCV).closer_than(15,cc.position))
            minerals = len(self.state.mineral_field.closer_than(15,cc.position))
            if minerals > 4:
                if workers < 18:
                    if self.can_afford(SCV):
                        await self.do(cc.train(SCV))

    async def build_supply(self):
        if self.supply_used <= 14 and self.can_afford(SUPPLYDEPOT) and not self.first_supply_built:
            supply_placement_positions = self.main_base_ramp.corner_depots
            commander = self.units(COMMANDCENTER)
            supply_placement_positions = {d for d in supply_placement_positions if commander.closest_distance_to(d) > 1}
            target_supply_location = supply_placement_positions.pop()
            await self.build(SUPPLYDEPOT, near=target_supply_location)      
            self.first_supply_built = True
    



run_game(maps.get("PortAleksanderLE"), [
    Bot(Race.Terran, LFC()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)
