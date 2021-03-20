from typing import Dict

from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State
from matrx.messages import Message

import agents1.AgentState as agst
from agents1.BrainStrategy import BrainStrategy
from agents1.Group42MapState import MapState
from bw4t.BW4TBrain import BW4TBrain


class Group42Agent(BW4TBrain):
    '''
    This agent should be dumb but reliable
    '''

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        # self._moves = [MoveNorth.__name__, MoveEast.__name__, MoveSouth.__name__, MoveWest.__name__]
        self.settings = settings
        self.strategy = None
        self.map_state = None
        self.agents = None
        self._door_range = 1
        self.agent_state: agst.AgentState = None
        self.holding = []

    def initialize(self):
        super().initialize()
        self.strategy = BrainStrategy.get_brain_strategy(self.settings, self)
        # self.map_state = None
        # self.agents = None
        self._door_range = 1
        # self.agent_state: AgentState = None
        # self.change_state(
        self.change_state(
            self.strategy.initial_state(Navigator(self.agent_id, self.action_set), StateTracker(self.agent_id)))
        #     agst.WalkingState(self.strategy, Navigator(self.agent_id, self.action_set), StateTracker(self.agent_id)))
        # self.holding = []

    def change_state(self, newState: agst.AgentState):
        self.agent_state = newState
        self.agent_state.set_agent(self)

    def grab_block(self, block):
        self.holding.append(block)
        self.holding.sort(key=lambda b: b[0])

    def drop_block(self, block):
        for i, b in enumerate(self.holding):
            if b[1] == block[1]:
                self.holding.pop(i)
                return

    def is_holding_blocks(self):
        return len(self.agent_properties['is_carrying']) > 0

    def is_max_capacity(self):
        return len(self.agent_properties['is_carrying']) > 2

    def get_highest_priority_block(self):
        # print(self.agent_properties['is_carrying'][0])
        return self.holding[0]

    def filter_bw4t_observations(self, state) -> State:
        if self.map_state is None:
            self.map_state = MapState(state)
            self.agents = state['World']['team_members']

        # Updating the map with visible blocks
        self.map_state.update_map(None, state)

        # handle messages
        # self.log("received: " + str(len(self.received_messages)) + " messages")
        for message in self.received_messages:
            if message['agentId'] != self.map_state.agent_id:
                self._handle_message(message)

        self.received_messages.clear()

        # for testing
        # self.log("current blocks: " + str(self.map.blocks))
        # self.log("goal blocks:" + str(self.map.drop_zone))
        # self.log("matching blocks:" + str(self.map.get_matching_blocks()))
        return state

    def decide_on_bw4t_action(self, state: State):
        # self.log("carrying: " + str(self.map_state.carried_blocks))

        action = self.agent_state.process(self.map_state, state)

        # finally, send all messages stored in the mapstate Queue
        for message in self.map_state.get_message_queue():
            # self.log("sending message " + str(message))
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

    def _handle_message(self, message):
        if type(message) is dict:
            self.log("handling message " + str(message))
            self.map_state.update_map(message, None)

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
