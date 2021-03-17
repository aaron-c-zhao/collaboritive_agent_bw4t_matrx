from matrx.agents.agent_types.patrolling_agent import PatrollingAgentBrain # type: ignore
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction # type: ignore 
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest # type: ignore 
import numpy as np # type: ignore 
import random # type: ignore 
import json
from matrx.agents.agent_utils.state import State # type: ignore 

from bw4t.BW4TBrain import BW4TBrain
from matrx.agents import HumanAgentBrain # type: ignore
from agents1.Group42Map import Map

from matrx.messages import Message

class Human(HumanAgentBrain):
    '''
    Human that can also handle slowdown. Currently not really implemented,
    we take the parameter but ignore it.
    '''
    def __init__(self, slowdown:int):
        super().__init__()
        self.map = None
        self.agents = None
    


    def filter_observations(self, state): 
        if self.map is None:
            self.map = Map(state)
            self.agents = state['World']['team_members']

        for message in self.received_messages:
            self._handle_message(state, message)

        # update state
        new_blocks = self.map.update_map(None, state)

        # communicate discovered blocks
        if new_blocks is not None:
            if len(new_blocks) > 0:
                self._broadcast('BlockFound', new_blocks)

        # for testing
        # self.log("current blocks: " + str(self.map.blocks))
        # self.log("goal blocks:" + str(self.map.drop_zone))
        self.log("matching blocks:" + str(self.map.get_matching_blocks()))

        return state # Why need to returning state


    def decide_on_bw4t_action(self, state:State):
        return super().decide_on_bw4t_action(state)

    def _handle_message(self, state, message):
        if type(message) is dict:
            self.log("handling message " + str(message))
            self.map.update_map(message, state)

    def _broadcast(self, type, data):
        content = {
                    'agentId': self.agent_id,
                    'type': type,
                    'blocks': data
                    }

        # global, so also to itself
        self.send_message(Message(content=content,
                                    from_id=self.agent_id,
                                    to_id=None))

    def is_json(self, string):
        try:
            json_object = json.loads(string)
        except ValueError as e:
            return False
        return True

    def log(self, message):
        print(self.agent_id + ":", message)
