from matrx.agents.agent_types.patrolling_agent import PatrollingAgentBrain # type: ignore
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction # type: ignore 
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest # type: ignore 
import numpy as np # type: ignore 
import random # type: ignore 
from matrx.agents.agent_utils.state import State # type: ignore 

from bw4t.BW4TBrain import BW4TBrain
from matrx.agents import HumanAgentBrain # type: ignore

from matrx.messages import Message

class Human(HumanAgentBrain):
    '''
    Human that can also handle slowdown. Currently not really implemented,
    we take the parameter but ignore it.
    '''
    def __init__(self, slowdown:int):
        super().__init__()


    def filter_observations(self, state): 
        blocks = state[{'is_collectable': True}]
        self.send_message(Message(content=f"testtests  " + str(blocks),
                                      from_id=self.agent_id,
                                      to_id=self.agent_id))
        return super().filter_observations(state)

    def decide_on_bw4t_action(self, state:State):
        return super().decide_on_bw4t_action(state)


