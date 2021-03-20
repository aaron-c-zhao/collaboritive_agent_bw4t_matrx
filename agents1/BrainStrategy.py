from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.AgentState as AgentState
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
    def __init__(self, agent: Group42Agent):
        self.agent: Group42Agent = agent

    @staticmethod
    def get_brain_strategy(settings: Dict[str, object], agent: Group42Agent):
        slowdown = settings['slowdown']
        colorblind = settings['colorblind'] if 'colorblind' in settings else False
        shapeblind = settings['shapeblind'] if 'shapeblind' in settings else False
        if colorblind:
            if shapeblind:
                return TotallyBlindStrategy(agent)
            return ColorBlindStrategy(agent)
        if shapeblind:
            return ShapeBlindStrategy(agent)
        return NormalStrategy(agent)

    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        pass

    def check_update(self, map_state: MapState):
        # check the block that haven't been found
        #
        pass


class NormalStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        map_state.get_matching_blocks_within_range(map_state.get_agent_location())


class ColorBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass
        # possibleActions = {'grab': GrabObject.__name__,
        #                    'drop': DropObject.__name__,
        #                    'openDoor': OpenDoorAction.__name__,
        #                    'closeDoor': CloseDoorAction.__name__}

    def block_found(self, map_state: MapState):
        map_state.get_matching_blocks_within_range(map_state.get_agent_location())


class ShapeBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass

    def block_found(self, map_state: MapState):
        map_state.get_candidate_blocks_colour()


class SlowStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass


class TotallyBlindStrategy(BrainStrategy):
    def get_action(self, map_state: MapState, state: State):
        pass
