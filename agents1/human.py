from matrx.agents.agent_types.patrolling_agent import PatrollingAgentBrain # type: ignore
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction # type: ignore 
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest # type: ignore 
import numpy as np # type: ignore 
import random # type: ignore 
import json
from matrx.agents.agent_utils.state import State # type: ignore 

from bw4t.BW4TBrain import BW4TBrain
from matrx.agents import HumanAgentBrain # type: ignore
from agents1.Group42MapState import MapState

from matrx.messages import Message

class Human(HumanAgentBrain):
    '''
    Human that can also handle slowdown. Currently not really implemented,
    we take the parameter but ignore it.
    '''
    def __init__(self, slowdown:int):
        super().__init__()
        self.map_state = None
        self.agents = None
    


    def filter_observations(self, state): 
        if self.map_state is None:
            self.map_state = MapState(state)
            self.agents = state['World']['team_members']


        # Updating the map with visible blocks
        self.map_state.update_map(None, state)

        # handle messages
        for message in self.received_messages:
            self._handle_message(state, message)

        

        


        # for testing
        # self.log("current blocks: " + str(self.map_state.blocks))
        # self.log("goal blocks:" + str(self.map_state.drop_zone))
        # self.log("matching blocks:" + str(self.map_state.get_matching_blocks_within_range(self.map.get_agent_location(state))))
        # self.log("self: " + str(self.map_state.get_agent_location(state, None)))
        # for agent in state.get_agents():
        #     self.log(str(agent['obj_id']) + ": " + str(self.map_state.get_agent_location(state, agent['obj_id'])))
        # self.log("wanted colors: " + str(self.map_state._get_goal_colour_set()))
        # self.log("wanted shape: " + str(self.map_state._get_goal_shape_set()))
        # self.log("rooms: " + str(self.map_state.rooms))
        # self.log("filter: " + str(self.map_state.filter_blocks_within_range(2, self.map_state.get_agent_location(state))))
        # self.log("carried blocks: " + str(self.map_state.carried_blocks))
        # self.log("agents: " + str(list(map(lambda x: {'block': x['is_carrying'], 'agent': x['obj_id']}, state.get_agents()))))
        
        # finally, send all messages stored in the mapstate Queue
        # SHOULD BE IN DECIDE_ON_BW4T_ACTION BUT HERE FOR DEBUGGING
        for message in self.map_state.get_message_queue():
            self.send_message(message)
        
        
        
        return state # Why need to returning state


    def decide_on_bw4t_action(self, state:State):


        

        return super().decide_on_bw4t_action(state)

    def _handle_message(self, state, message):
        if type(message) is dict:
            # self.log("handling message " + str(message))
            self.map_state.update_map(message, state)

    def _broadcast(self, message):
        self.send_message(message)

    def log(self, message):
        print(self.agent_id + ":", message)
