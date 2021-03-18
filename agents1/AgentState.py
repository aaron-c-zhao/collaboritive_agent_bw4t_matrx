from typing import Set

from matrx.actions import *
from matrx.agents import Navigator, StateTracker
from matrx.agents.agent_utils.state import State

import agents1.BrainStrategy as BrainStrategy
from agents1 import Group42Map


class AgentState:
    def __init__(self, navigator: Navigator, state_tracker: StateTracker):
        self.brain: BrainStrategy = None
        self.navigator = navigator
        self.navigator.reset_full()
        self.state_tracker = state_tracker
        self.goal_blocks = None

    def set_brain(self, brain: BrainStrategy):
        self.brain = brain

    def process(self, map: Group42Map, state: State):
        self.state_tracker.update(state)
        # raise NotImplementedError("Please implement this abstract method")

    @staticmethod
    def match_blocks(block1, block2):
        return block1['shape'] == block2['shape'] and block1['colour'] == block2['colour']

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
    def process(self, map: Group42Map, state: State):
        super().process(map, state)

        closest_room_id = map.get_closest_unvisited_room(self.brain.get_position())
        if closest_room_id is None:
            self.brain.change_state(WaitingState(self.navigator, self.state_tracker))
            return None, {}

        # no current waypoints: find the closest room and go there
        if len(self.navigator.get_all_waypoints()) == 0:
            room = map.get_room(closest_room_id)
            door = room['doors'][0]['location']
            # if door is closed, reach the spot below it first
            if not room['doors'][0]['status']:
                door = door[:1] + (door[1] + 1,)
            self.navigator.add_waypoint(door)

        if self.navigator.is_done:
            room = map.get_room(closest_room_id)
            self.brain.change_state(ExploringRoomState(self.navigator, self.state_tracker, closest_room_id))

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

    def __init__(self, navigator: Navigator, state_tracker: StateTracker, room_id):
        super(ExploringRoomState, self).__init__(navigator, state_tracker)
        self.room_id = room_id
        self.unvisited_squares: Set = None

    def process(self, map: Group42Map, state: State):
        super().process(map, state)

        room = map.get_room(self.room_id)

        # if just started exploring the room, then initialise the unvisited squares and go towards one of those squares
        if self.unvisited_squares is None:
            self.unvisited_squares = set(room['indoor_area'])
            self.navigator.add_waypoint(self.unvisited_squares.pop())

        if self.goal_blocks is None:
            self.goal_blocks = map.get_matching_blocks()

        # if we haven't visited all squares, update the unvisited squares and keep exploring
        self.__update_visited_squares()

        # TODO find blocks
        visible_blocks = map.get_visible_blocks()
        for block in visible_blocks:
            for goal in self.goal_blocks:
                if self.match_blocks(block, goal[2]):
                    self.navigator.reset_full()
                    self.navigator.add_waypoint(block['location'])
                    return self.navigator.get_move_action(self.state_tracker), {}
                    print("found_block")
                    print(block)
                    return GrabObject.__name__, {'object_id': block['id']}

        if len(self.unvisited_squares) == 0:
            self.navigator.reset_full()
            map.visit_room(self.room_id)
            self.brain.change_state(WalkingState(self.navigator, self.state_tracker))
            return None, {}

        if self.navigator.is_done:
            self.navigator.reset_full()
            self.navigator.add_waypoint(self.unvisited_squares.pop())

        return self.navigator.get_move_action(self.state_tracker), {}

    def __update_visited_squares(self):
        '''
        TODO: can be optimised
        '''
        curr_position = self.brain.get_position()
        visible_squares = set()
        for x, y in self.squares:
            visible_squares.add((curr_position[0] + x, curr_position[1] + y))
        self.unvisited_squares.difference_update(visible_squares)


class GrabBoxState(AgentState):
    def process(self, map: Group42Map, state: State, ):

        pass

class DeliveringState(AgentState):
    def process(self, map: Group42Map, state: State):
        pass

class WaitingState(AgentState):
    def process(self, map: Group42Map, state: State):
        return None, {}
