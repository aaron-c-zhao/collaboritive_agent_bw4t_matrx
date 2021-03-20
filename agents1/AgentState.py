from typing import Set

from matrx import utils
from matrx.actions import *
from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.BrainStrategy as BrainStrategy
import agents1.Group42Agent as Group42Agent
from agents1 import Group42MapState


class AgentState:
    def __init__(self, strategy: BrainStrategy, navigator: Navigator, state_tracker: StateTracker):
        self.agent: Group42Agent = None
        self.navigator = navigator
        self.navigator.reset_full()
        self.state_tracker = state_tracker
        self.strategy: BrainStrategy = strategy

    def set_agent(self, agent: Group42Agent):
        self.agent = agent

    def process(self, map_state: Group42MapState, state: State):
        self.state_tracker.update(state)
        self.strategy.check_update(map_state)
        # raise NotImplementedError("statePlease implement this abstract method")


# {
#     'room_name': room,
#     'indoor_area': list(map(lambda x: x['location'], state.get_room_objects(room))),
#     'doors': list(map(lambda x: {
#         'location': x['location'],
#         'status': x['is_open']
#         # whether the door is open, if not, then the agent should first navi to the front of the door
#     }, state.get_room_doors(room))),
#     'visited': False
# }

class WalkingState(AgentState):
    def process(self, map_state: Group42MapState, state: State):
        super().process(map_state, state)

        closest_room_id = map_state.get_closest_unvisited_room(map_state.get_agent_location())
        if closest_room_id is None:
            self.agent.change_state(WaitingState(self.strategy, self.navigator, self.state_tracker))
            return None, {}

        # no current waypoints: find the closest room and go there
        if len(self.navigator.get_all_waypoints()) == 0:
            room = map_state.get_room(closest_room_id)
            door = room['doors'][0]['location']
            # if door is closed, reach the spot below it first
            if not room['doors'][0]['status']:
                door = door[:1] + (door[1] + 1,)
            self.navigator.add_waypoint(door)

        if self.navigator.is_done:
            room = map_state.get_room(closest_room_id)
            self.agent.change_state(
                ExploringRoomState(self.strategy, self.navigator, self.state_tracker, closest_room_id))

            # open the door if it's not open
            if not room['doors'][0]['status']:
                return OpenDoorAction.__name__, {'object_id': room['doors'][0]['door_id']}

        return self.navigator.get_move_action(self.state_tracker), {}


class ExploringRoomState(AgentState):
    squares = [(0, -2),
               (-1, -1), (0, -1), (1, -1),
               (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
               (-1, 1), (0, 1), (1, 1),
               (0, 2)]

    def __init__(self, strategy: BrainStrategy, navigator: Navigator, state_tracker: StateTracker, room_id):
        super().__init__(strategy, navigator, state_tracker)
        self.room_id = room_id
        self.unvisited_squares: Set = None
        self.pending_block = None

    def process(self, map_state: Group42MapState, state: State):
        super().process(map_state, state)
        if self.pending_block is not None:
            res = state.get_with_property({'carried_by': map_state.agent_id})
            if res is not None and self.pending_block[2]['id'] in [x['obj_id'] for x in res['is_carrying']]:
                self.agent.grab_block(self.pending_block)
                map_state.pop_block(self.pending_block[2])
            self.pending_block = None

        room = map_state.get_room(self.room_id)

        # if just started exploring the room, then initialise the unvisited squares and go towards one of those squares
        if self.unvisited_squares is None:
            self.unvisited_squares = set(room['indoor_area'])
            self.navigator.add_waypoint(self.unvisited_squares.pop())

        # if we visited all squares in this room, we can go back to walking
        if len(self.unvisited_squares) == 0:
            self.navigator.reset_full()
            map_state.visit_room(self.room_id)
            self.agent.change_state(WalkingState(self.strategy, self.navigator, self.state_tracker))
            return None, {}

        # update the unvisited squares
        self.__update_visited_squares(map_state.get_agent_location())

        # if full capacity, start delivering
        # TODO make this smarter by cooperating with other agents
        if self.agent.is_max_capacity():
            self.agent.change_state(DeliveringState(self.strategy, self.navigator, self.state_tracker))

        # if we have already arrived to our destination, choose a new destination from the unvisited squares in the room
        if self.navigator.is_done:
            self.navigator.reset_full()
            self.navigator.add_waypoint(self.unvisited_squares.pop())

            # check if any of the blocks match the goal blocks
            # matching_blocks = map_state.get_matching_blocks_within_range(map_state.get_agent_location())
            matching_blocks = self.strategy.block_found(map_state)
            for block in filter(lambda b: not b[3], matching_blocks):
                # if we're too far away, temporarily set new destination to get closer to the block and pick it up
                # TODO extract hardcoded distance
                if utils.get_distance(map_state.get_agent_location(), block[2]['location']) > 1:
                    self.navigator.reset_full()
                    self.navigator.add_waypoint(block[2]['location'])
                    return self.navigator.get_move_action(self.state_tracker), {}

                # otherwise grab this block
                self.navigator.is_done = True
                self.pending_block = block
                return GrabObject.__name__, {'object_id': block[2]['id']}

        return self.navigator.get_move_action(self.state_tracker), {}

    def __update_visited_squares(self, curr_position):
        '''
        TODO: can be optimised
        '''
        visible_squares = set()
        for x, y in self.squares:
            visible_squares.add((curr_position[0] + x, curr_position[1] + y))
        self.unvisited_squares.difference_update(visible_squares)


class DeliveringState(AgentState):
    def __init__(self, strategy: BrainStrategy, navigator: Navigator, state_tracker: StateTracker):
        super().__init__(strategy, navigator, state_tracker)
        self.delivering_block = None

    def process(self, map_state: Group42MapState, state: State):
        super().process(map, state)

        # if not started to drop a box
        if self.delivering_block is None:
            if self.agent.is_holding_blocks():
                self.navigator.reset_full()
                self.delivering_block = self.agent.get_highest_priority_block()
                self.navigator.add_waypoint(self.delivering_block[1])
            else:
                self.agent.change_state(WalkingState(self.strategy, self.navigator, self.state_tracker))

        elif self.navigator.is_done:
            self.navigator.reset_full()
            self.agent.drop_block(self.delivering_block)
            drop_block = {'location': self.delivering_block[1], 'block': self.delivering_block[2]}
            map_state.drop_block(drop_block)
            self.delivering_block = None
            return DropObject.__name__, {'object_id': drop_block['block']['id']}

        return self.navigator.get_move_action(self.state_tracker), {}


# TODO dropoff(when invetory full),
#  rid_unnecessary_blocks(when other people found goal blocks),
#  check_goal_blocks(when next to goal state and need to check other people's half known blocks)

class WaitingState(AgentState):
    def process(self, map_state: Group42MapState, state: State):
        super().process(map_state, state)

        return None, {}
