from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.AgentState as agentstate
from agents1 import Group42Map
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

    @staticmethod
    def get_brain_strategy(settings: Dict[str, object], agent: Group42Agent):
        if 'colorblind' in settings and settings['colorblind']:
            return ColorBlindStrategy(agent)
        if 'shapeblind' in settings and settings['shapeblind']:
            return ShapeBlindStrategy(agent)
        if 'slowdown' in settings and settings['slowdown'] > 1:
            return SlowStrategy(agent)
        print("USING NORMAL STRATEGY")
        return NormalStrategy(agent)

    def change_state(self, newState: agentstate.AgentState):
        self.agent_state = newState
        self.agent_state.set_brain(self)

    def get_action(self, map: Group42Map, state: State):
        self.curr_position = state[self.agent.agent_id]['location']

    def get_position(self):
        return self.curr_position


class NormalStrategy(BrainStrategy):
    def get_action(self, map: Group42Map, state: State):
        super().get_action(map, state)
        return self.agent_state.process(map, state)


class ColorBlindStrategy(BrainStrategy):
    def get_action(self, map: Group42Map, state: State):
        self.agent_state.process(map, state)
        # possibleActions = {'grab': GrabObject.__name__,
        #                    'drop': DropObject.__name__,
        #                    'openDoor': OpenDoorAction.__name__,
        #                    'closeDoor': CloseDoorAction.__name__}

        # action_kwargs = {}
        # action_kwargs['object_id'] = None

        pass


class ShapeBlindStrategy(BrainStrategy):
    def get_action(self, map: Group42Map, state: State):
        pass


class SlowStrategy(BrainStrategy):
    def get_action(self, map: Group42Map, state: State):
        pass
