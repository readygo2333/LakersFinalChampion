import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human

import time
import math


class Lakers(sc2.BotAI):
    def __init__(self, use_model=True):
        self.combinedActions = []
        self.enemy_expand_location = None
        self.first_supply_built=False
        self.stage = "early_rush"
        self.counter_units = {
            #Enemy: [Enemy_Cunts, Army, Num]
            MARINE: [3, SIEGETANK, 1],
            MARAUDER: [3, MARINE, 3],
            REAPER: [3, SIEGETANK, 3],
            GHOST: [2, MARINE, 3],
            SIEGETANK: [1, BANSHEE, 1],
            BANSHEE: [1, MARINE, 3]
            }

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
        #if iteration == 0:
        #    await self.on_game_start()
        #    return
        cc = self.units(COMMANDCENTER).ready
        if not cc.exists:
            self.worker_rush(iteration)
            return
      
        if self.stage == "early_rush":
            await self.early_rush(iteration)
            return
        #await self.main_progress(iteration)


    async def early_rush(self, iteration):
        cc = self.units(COMMANDCENTER).ready
        #采矿
        await self.distribute_workers()
        #造农民
        await self.train_WORKERS(cc)
        cc = self.units(COMMANDCENTER).ready
        #1.房子，第一个堵路口
        await self.build_rush_SUPPLYDEPOT(cc)
        
        #2. 气矿
        #await self.build_REFINERY(cc)
        
        #3. 兵营
        await self.build_rush_BARRACKS(cc)
        
        #4. 枪兵
        await self.train_MARINE()
        #5. 坦克
        await self.train_SIEGETANK()
        
        
        
    # Start
    async def main_progress(self, iteration):
        #await self.worker_rush(iteration)
        await self.worker_detect(iteration)
        #await self.marine_detect(iteration)
        cc = self.units(COMMANDCENTER).ready
        if not cc.exists:
            self.worker_rush(iteration)
            return
        else:
            cc = cc.first

        ############### 修建筑 ####################
        await self.build_SUPPLYDEPOT(cc)      # 修建补给站
        await self.build_BARRACKS(cc)         # 修建兵营
        await self.build_FACTORY(cc)          # 修建重工厂
        await self.build_STARPORT(cc)         # 修建星港
        #await self.build_ENGINEERINGBAY(cc)   # 修建工程站
        #await self.build_SENSORTOWER(cc)      # 修建感应塔
        #await self.build_MISSILETURRET(cc)    # 修建导弹他
        #await self.build_GHOSTACADEMY(cc)     # 修建幽灵学院
        #await self.build_BUNKER(cc)           # 修建地堡
        await self.build_REFINERY(cc)         # 修建精炼厂

        ################ 采矿 ######################
        await self.distribute_workers()
        for a in self.units(REFINERY):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        ################ 训练 ######################
        await self.train_WORKERS(cc)      # 训练农民
        await self.train_MARINE()         # 训练机枪兵
        #await self.train_MARAUDER()       # 训练掠夺者
        #await self.train_REAPER()         # 训练收割者
        #await self.train_GHOST()          # 训练幽灵
        #await self.train_SIEGETANK()      # 训练坦克
        await self.train_BANSHEE()        # 训练女妖战机

        ############### 进攻 ###################
        # 当机枪兵大于16个时，进攻
        #if self.units(MARINE).amount > 15:
        #    for marine in self.units(MARINE):
        #        await self.do(marine.attack(self.enemy_start_locations[0]))

        # 机枪兵大于10个，女妖大于3，进攻
        if self.units(MARINE).amount > 10 and self.units(BANSHEE).amount > 3:
            for ma in self.units(MARINE):
                await self.do(ma.attack(self.enemy_start_locations[0]))
            for bs in self.units(BANSHEE):
                await self.do(bs.attack(self.enemy_start_locations[0]))

    ############ 功能函数 ################
    async def worker_rush(self, iteration):
        self.actions = []
        target = self.enemy_start_locations[0]
        if iteration == 0:
            for worker in self.workers:
                self.actions.append(worker.attack(target))
        await self.do_actions(self.actions)

    async def worker_detect(self, iteration):
        self.actions = []
        target = self.enemy_start_locations[0]
        if iteration != 0 and iteration / 15 == 0:
            for worker in self.workers:
                self.actions.append(worker.attack(target))
                break
        await self.do_actions(self.actions)

    async def marine_detect(self, iteration):
        self.actions = []
        target = self.enemy_start_locations[0]
        if iteration != 0 and iteration / 10 == 0:
            for unit in self.units(MARINE):
                self.actions.append(unit.attack(target))
                break
        await self.do_actions(self.actions)

    async def train_WORKERS(self, cc):
        for cc in self.units(COMMANDCENTER).ready.noqueue:
            workers = len(self.units(SCV).closer_than(15, cc.position))
            minerals = len(self.state.mineral_field.closer_than(15, cc.position))
            if minerals > 4:
                if workers < 18:
                    if self.can_afford(SCV):
                        await self.do(cc.train(SCV))

    async def build_rush_SUPPLYDEPOT(self, cc):
    #   第一个房子，堵路口
        if self.supply_left <= 10 and self.can_afford(SUPPLYDEPOT) and not self.already_pending(SUPPLYDEPOT): # and not self.first_supply_built:
            supply_placement_positions = self.main_base_ramp.corner_depots
            commander = self.units(COMMANDCENTER)
            supply_placement_positions = {d for d in supply_placement_positions if commander.closest_distance_to(d) > 1}
            target_supply_location = supply_placement_positions.pop()
            await self.build(SUPPLYDEPOT, near=target_supply_location)
        elif self.units(SUPPLYDEPOT).amount >= 1:
            #self.build_SUPPLYDEPOT(self, cc)
            return
            
        

    async def build_SUPPLYDEPOT(self, cc):
        if self.supply_left <= 3 and self.can_afford(SUPPLYDEPOT) and not self.already_pending(SUPPLYDEPOT): # and not self.first_supply_built:
            #await self.build(SUPPLYDEPOT, near = cc.position.towards(self.game_info.map_center, 8))
            return


    async def build_rush_BARRACKS(self, cc):
        #双兵营,造在第一个房子附近，一起堵路口
        if self.units(SUPPLYDEPOT).amount == 1:
            first_supply = self.units(SUPPLYDEPOT).first
        
        if self.units(BARRACKS).amount < 1 and self.can_afford(BARRACKS):
            await self.build(BARRACKS, near = self.units(SUPPLYDEPOT).random)
            
        if self.units(BARRACKS).amount == 1 and self.can_afford(BARRACKS):
            await self.build(BARRACKS, near = self.units(BARRACKS).first)

    async def build_BARRACKS(self, cc):
        if self.units(BARRACKS).amount == 0 and self.can_afford(BARRACKS):
            await self.build(BARRACKS, near = cc.position.towards(self.game_info.map_center, 9))
        if self.units(BARRACKS).amount < 3 and self.units(FACTORY).ready.exists and self.can_afford(BARRACKS):
            await self.build(BARRACKS, near = cc.position.towards(self.game_info.map_center, 9))
        if self.units(BARRACKS).amount < 5 and self.units(STARPORT).ready.exists and self.can_afford(BARRACKS):
            await self.build(BARRACKS, near = cc.position.towards(self.game_info.map_center, 9))

    async def build_FACTORY(self, cc):
        if self.units(FACTORY).amount < 3 and self.units(BARRACKS).ready.exists and self.can_afford(FACTORY) and not self.already_pending(FACTORY):
            await self.build(FACTORY, near = cc.position.towards(self.game_info.map_center, 9))
        # 修建 FACTORYTECHLAB, 以建造坦克
        for sp in self.units(FACTORY).ready:
            if sp.add_on_tag == 0:
                await self.do(sp.build(FACTORYTECHLAB))

    async def build_STARPORT(self, cc):
        if self.units(STARPORT).amount < 3 and self.units(FACTORY).ready.exists and self.can_afford(STARPORT) and not self.already_pending(STARPORT):
            await self.build(STARPORT, near = cc.position.towards(self.game_info.map_center, 9))
        # 修建 STARPORTTECHLAB, 以建女妖
        for sp in self.units(STARPORT).ready:
            if sp.add_on_tag == 0:
                await self.do(sp.build(STARPORTTECHLAB))

    async def build_ENGINEERINGBAY(self, cc):
        if self.units(ENGINEERINGBAY).amount < 2 and self.can_afford(ENGINEERINGBAY) and not self.already_pending(ENGINEERINGBAY):
            await self.build(ENGINEERINGBAY, near = cc.position.towards(self.game_info.map_center, 9))

    async def build_SENSORTOWER(self, cc):
        if self.units(SENSORTOWER).amount < 2 and self.units(ENGINEERINGBAY).ready.exists and self.can_afford(SENSORTOWER) and not self.already_pending(SENSORTOWER):
            await self.build(SENSORTOWER, near = cc.position.towards(self.game_info.map_center, 9))

    async def build_MISSILETURRET(self, cc):
        if self.units(MISSILETURRET).amount < 4 and self.units(SENSORTOWER).ready.exists and self.can_afford(MISSILETURRET) and not self.already_pending(MISSILETURRET):
            #await self.build(MISSILETURRET, near = cc.position.towards(self.game_info.map_center, 9))
            ramp = self.main_base_ramp.corner_depots
            cm = self.units(COMMANDCENTER)
            ramp = {d for d in ramp if cm.closest_distance_to(d) > 1}
            target = ramp.pop()
            await self.build(MISSILETURRET, near=target)

    async def build_GHOSTACADEMY(self, cc):
        if self.units(GHOSTACADEMY).amount < 1 and self.units(FACTORY).ready.exists and self.can_afford(GHOSTACADEMY) and not self.already_pending(GHOSTACADEMY):
            await self.build(GHOSTACADEMY, near = cc.position.towards(self.game_info.map_center, 9))

    async def build_BUNKER(self, cc):
        if self.units(BUNKER).amount < 5 and self.units(GHOSTACADEMY).ready.exists and self.can_afford(BUNKER) and not self.already_pending(BUNKER):
            await self.build(BUNKER, near = cc.position.towards(self.game_info.map_center, 9))

    async def build_REFINERY(self, cc):
        #if self.units(REFINERY).amount < 2 and self.can_afford(REFINERY):
        #    await self.build(REFINERY, near = cc.position.towards(self.game_info.map_center, 9))
        if self.units(BARRACKS).exists and self.units(REFINERY).amount < 2 and self.can_afford(REFINERY) and not self.already_pending(REFINERY):
            vgs = self.state.vespene_geyser.closer_than(20.0, cc)
            for vg in vgs:
                if self.units(REFINERY).closer_than(1.0, vg).exists:
                    break
                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break
                await self.do(worker.build(REFINERY, vg))
                break

    # 训练机枪兵
    async def train_MARINE(self):
        if self.units(MARINE).amount < 16 and self.can_afford(MARINE):
            for barrack in self.units(BARRACKS).ready.noqueue:
                await self.do(barrack.train(MARINE))

        # 训练掠夺者
    async def train_MARAUDER(self):
        if self.units(MARAUDER).amount < 5 and self.can_afford(MARAUDER):
            for marauder in self.units(BARRACKS).ready:
                await self.do(marauder.train(MARAUDER))

    # 训练收割者
    async def train_REAPER(self):
        if self.units(REAPER).amount < 5 and self.can_afford(REAPER):
            for re in self.units(BARRACKS).ready:
                await self.do(re.train(REAPER))

    # 训练幽灵
    async def train_GHOST(self):
        if self.units(GHOST).amount < 5 and self.can_afford(GHOST):
            for gst in self.units(GHOSTACADEMY).ready:
                await self.do(gst.train(GHOST))

    # 训练坦克
    async def train_SIEGETANK(self):
        if self.units(SIEGETANK).amount < 5 and self.can_afford(SIEGETANK):
            for st in self.units(FACTORY).ready:
                await self.do(st.train(SIEGETANK))

    # 训练女妖战机
    async def train_BANSHEE(self):
        if self.units(BANSHEE).amount < 5 and self.can_afford(BANSHEE):
            for bs in self.units(STARPORT).ready:
                await self.do(bs.train(BANSHEE))

def main():
    sc2.run_game(sc2.maps.get("PortAleksanderLE"), [
        Bot(Race.Terran, Lakers()),
        Computer(Race.Terran, Difficulty.Easy)
        #Human(Race.Terran)
    ], realtime=False)

if __name__ == '__main__':
    main()
