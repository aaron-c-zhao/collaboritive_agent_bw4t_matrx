import json
import random  # type: ignore
from typing import Dict

import numpy as np  # type: ignore
from matrx.actions import MoveNorth, OpenDoorAction  # type: ignore
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest  # type: ignore
from matrx.agents.agent_utils.state import State  # type: ignore
from matrx.messages import Message

from agents1.BrainStrategy import BrainStrategy
from agents1.Group42MapState import MapState
from bw4t.BW4TBrain import BW4TBrain


class Group42Agent(BW4TBrain):
    '''
    This agent should be dumb but reliable
    '''

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        self._moves = [MoveNorth.__name__, MoveEast.__name__, MoveSouth.__name__, MoveWest.__name__]
        self.settings = settings

    def initialize(self):
        super().initialize()
        self.strategy = BrainStrategy.get_brain_strategy(self.settings, self)
        self.map = None
        self.agents = None
        self._door_range = 1

    def filter_bw4t_observations(self, state) -> State:
        if self.map is None:
            self.map = MapState(state)
            self.agents = state['World']['team_members']

        # Updating the map with visible blocks
        self.map.update_map(None, state)

        # handle messages
        for message in self.received_messages:
            self._handle_message(state, message)


        # for testing
        # self.log("current blocks: " + str(self.map.blocks))
        # self.log("goal blocks:" + str(self.map.drop_zone))
        # self.log("matching blocks:" + str(self.map.get_matching_blocks()))
        return state

    def decide_on_bw4t_action(self, state: State):

        self.log("carrying: " + str(self.map.carried_blocks))

        action = self.strategy.get_action(self.map, state)

        # finally, send all messages stored in the mapstate Queue
        for message in self.map.get_message_queue():
            self.send_message(message)

        return action

    # def _nearbyDoors(self, state: State):
    #     # copy from humanagent
    #     # Get all doors from the perceived objects
    #     objects = list(state.keys())
    #     doors = [obj for obj in objects if 'is_open' in state[obj]]
    #     doors_in_range = []
    #     for object_id in doors:
    #         # Select range as just enough to grab that object
    #         dist = int(np.ceil(np.linalg.norm(
    #             np.array(state[object_id]['location']) - np.array(
    #                 state[self.agent_id]['location']))))
    #         if dist <= self._door_range:
    #             doors_in_range.append(object_id)
    #     return doors_in_range

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

    # def is_json(self, string):
    #     try:
    #         json_object = json.loads(string)
    #     except ValueError as e:
    #         return False
    #     return True

    def log(self, message):
        print(self.agent_id + ":", message)
