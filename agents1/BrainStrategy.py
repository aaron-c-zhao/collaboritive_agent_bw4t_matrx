from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.AgentState as agst
import agents1.Group42Agent as Group42Agent
from agents1.Group42MapState import MapState

'''
'OpenDoorAction'	'door_range':1, 'object_id':doorId
'MoveNorth' 'MoveEast' 'MoveSouth' 'MoveWest'	
GrabObject	'object_id':blockId
DropObject	'object_id':blockId
None (do nothing)	
'''


class BrainStrategy:
    def __init__(self, agent: Group42Agent, slowness):
        self.agent: Group42Agent = agent
        self.slowness = slowness

    @staticmethod
    def get_brain_strategy(settings: Dict[str, object], agent: Group42Agent):
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

    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        pass

    def initial_state(self, navigator: Navigator, state_tracker: StateTracker):
        '''
        State machine entry point. Walking state by default, but can be overwritten
        '''
        return agst.WalkingState(self, navigator, state_tracker)

    def check_update(self, map_state: MapState):
        return
        # match_blocks(b1, b2)
        if len(map_state.carried_blocks) == 0:
            return

        blocks = list([block for agent in map_state.blocks_carried_by_agents.values() for block in agent])
        if len(blocks) == 0:
            return
        target_block_properties = [d['properties'] for d in map_state.drop_zone]
        shapes = [d['shape'] for d in target_block_properties]
        colors = [d['colour'] for d in target_block_properties]
        # all fully found blocks
        for block in list(filter(lambda b: b['visited'] == 3, blocks)):
            if block['shape'] in shapes:
                shapes.pop(block['shape'])
            if block['colour'] in colors:
                colors.remove(block['colour'])

        shapes = set(shapes)
        colors = set(colors)

        unnecessary_blocks = [map_state.carried_blocks]


        pass


class NormalStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        return map_state.filter_blocks_within_range(loc=map_state.get_agent_location(),
                                                    blocks=map_state.get_matching_blocks(color=True, shape=True))


class ColorBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass
        # possibleActions = {'grab': GrabObject.__name__,
        #                    'drop': DropObject.__name__,
        #                    'openDoor': OpenDoorAction.__name__,
        #                    'closeDoor': CloseDoorAction.__name__}

    def block_found(self, map_state: MapState):
        return map_state.filter_blocks_within_range(loc=map_state.get_agent_location(),
                                                    blocks=map_state.get_matching_blocks(color=False, shape=True))


class ShapeBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        return map_state.filter_blocks_within_range(loc=map_state.get_agent_location(),
                                                    blocks=map_state.get_matching_blocks(color=True, shape=False))


class SlowStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass


class TotallyBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        pass

    def initial_state(self, navigator: Navigator, state_tracker: StateTracker):
        # totally blind agent awaits for updates in the world info. It could start off by following a random agent.
        return agst.WaitingState(self, navigator, state_tracker)
