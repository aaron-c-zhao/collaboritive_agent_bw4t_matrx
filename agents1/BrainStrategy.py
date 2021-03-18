from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.AgentState as agentstate
from agents1 import Group42MapState
import agents1.Group42Agent as Group42Agent

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
        self.agent_state: agentstate.AgentState = None
        self.change_state(agentstate.WalkingState(Navigator(agent.agent_id, agent.action_set), StateTracker(agent.agent_id)))
        self.curr_position = None
        self.holding = []

    @staticmethod
    def get_brain_strategy(settings: Dict[str, object], agent: Group42Agent):
        if 'colorblind' in settings and settings['colorblind']:
            return ColorBlindStrategy(agent)
        if 'shapeblind' in settings and settings['shapeblind']:
            return ShapeBlindStrategy(agent)
        if 'slowdown' in settings and settings['slowdown'] > 1:
            return SlowStrategy(agent)
        return NormalStrategy(agent)

    def change_state(self, newState: agentstate.AgentState):
        self.agent_state = newState
        self.agent_state.set_brain(self)

    def get_action(self, map: Group42MapState, state: State):
        pass

    def grab_block(self, block):
        self.holding.append(block)
        self.holding.sort()

    def drop_block(self, block):
        for i, b in enumerate(self.holding):
            if b[1] == block[1]:
                self.holding.pop(i)
                return

    def is_holding_blocks(self):
        return len(self.holding) > 0

    def is_max_capacity(self):
        return len(self.holding) > 2

    def get_highest_priority_block(self):
        return self.holding[0]



class NormalStrategy(BrainStrategy):
    def get_action(self, map: Group42MapState, state: State):
        return self.agent_state.process(map, state)


class ColorBlindStrategy(BrainStrategy):
    def get_action(self, map_state: Group42MapState, state: State):
        self.agent_state.process(map, state)
        # possibleActions = {'grab': GrabObject.__name__,
        #                    'drop': DropObject.__name__,
        #                    'openDoor': OpenDoorAction.__name__,
        #                    'closeDoor': CloseDoorAction.__name__}
        pass


class ShapeBlindStrategy(BrainStrategy):
    def get_action(self, map_state: Group42MapState, state: State):
        pass


class SlowStrategy(BrainStrategy):
    def get_action(self, map_state: Group42MapState, state: State):
        pass
