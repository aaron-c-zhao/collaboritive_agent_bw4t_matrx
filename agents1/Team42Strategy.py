from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.Team42AgentState as agst
import agents1.Team42Agent as Team42Agent
from agents1.Team42MapState import MapState
from agents1.Team42Utils import reduce

'''
'OpenDoorAction'	'door_range':1, 'object_id':doorId
'MoveNorth' 'MoveEast' 'MoveSouth' 'MoveWest'	
GrabObject	'object_id':blockId
DropObject	'object_id':blockId
None (do nothing)	
'''


class Team42Strategy:
    def __init__(self, agent: Team42Agent, slowness):
        self.agent: Team42Agent = agent
        self.slowness = slowness
        self.traverse_order = 1 # magic number here: 0 for x first, 1 for y first

    @staticmethod
    def get_brain_strategy(settings: Dict[str, object], agent: Team42Agent):
        slowdown = settings['slowdown']
        colorblind = settings['colorblind'] if 'colorblind' in settings else False
        shapeblind = settings['shapeblind'] if 'shapeblind' in settings else False
        if colorblind:
            if shapeblind:
                return TotallyBlindStrategy(agent, slowdown)
            return ColorBlindStrategy(agent, slowdown)
        if shapeblind:
            return ShapeBlindStrategy(agent, slowdown)
        return NormalStrategy(agent, slowdown)

    def is_all_blocks_found(self, map_state: MapState):
        return reduce(lambda a, b: a + bool(b['found_blocks']), map_state.goal_blocks, 0) == len(map_state.goal_blocks)

    def get_matching_blocks_nearby(self, map_state: MapState):
        return map_state.filter_blocks_within_range(loc=map_state.get_agent_location(),
                                                    blocks=map_state.get_matching_blocks())

    def initial_state(self, navigator: Navigator, state_tracker: StateTracker):
        '''
        State machine entry point. Walking state by default, but can be overwritten
        '''
        return agst.WalkingState(self, navigator, state_tracker)

    def check_update(self, map_state: MapState):
        # match_blocks(b1, b2)
        pass

    def get_next_room(self, map_state: MapState):
        return map_state.get_closest_unvisited_room(map_state.get_agent_location(), self.traverse_order)

    def switch_traverse_order(self):
        self.traverse_order = 0 if self.traverse_order == 1 else 1

class NormalStrategy(Team42Strategy):
    def check_update(self, map_state: MapState):
        return None


class ColorBlindStrategy(Team42Strategy):
    def check_update(self, map_state: MapState):
        pass
        # if len(map_state.carried_blocks) == 0:
        #     return
        #
        # blocks = list([block for agent in map_state.blocks_carried_by_agents.values() for block in agent])
        # if len(blocks) == 0:
        #     return
        #
        # target_block_properties = [d['properties'] for d in map_state.goal_blocks]
        # shapes = [d['shape'] for d in target_block_properties]
        #
        # # all fully found blocks
        # for block in list(filter(lambda b: b['visited'] == 3, blocks)):
        #     if block['shape'] in shapes:
        #         shapes.pop(block['shape'])
        #
        # shapes_to_find = set(shapes)
        #
        # # if any of our blocks has a quality which is no longer needed, then the block can be thrown away
        # return list(filter(None, (b['id'] if b['shape'] not in shapes_to_find else None for b in map_state.carried_blocks.values())))


class ShapeBlindStrategy(Team42Strategy):
    pass


class SlowStrategy(Team42Strategy):
    pass


class TotallyBlindStrategy(Team42Strategy):
    def initial_state(self, navigator: Navigator, state_tracker: StateTracker):
        # totally blind agent awaits for updates in the world info. It could start off by following a random agent.
        return agst.WaitingState(self, navigator, state_tracker)
