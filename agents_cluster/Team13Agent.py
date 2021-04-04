from typing import List, Dict
import numpy as np  # type: ignore
import random  # type: ignore
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction, GrabObject, DropObject  # type: ignore
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest  # type: ignore
from matrx.agents.agent_utils.state import State  # type: ignore
from matrx.agents.agent_utils.state_tracker import StateTracker
from matrx.agents.agent_utils.navigator import Navigator  # type: ignore
from matrx.utils import get_distance
from .messaging import *
from bw4t.BW4TBrain import BW4TBrain
from bw4t.BW4TBlocks import CollectableBlock

from enum import Enum


class Phase(Enum):
    EXPLORING = 1
    PICKUP = 2
    DROP = 3


class Team13Agent(BW4TBrain):
    """
    This agent makes random walks and opens any doors it hits upon
    """

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        self._moves = [MoveNorth.__name__, MoveEast.__name__, MoveSouth.__name__, MoveWest.__name__]
        self.slowdown = settings['slowdown']

    def initialize(self):
        super().initialize()
        self.state_tracker = StateTracker(agent_id=self.agent_id)
        self.navigator = Navigator(agent_id=self.agent_id, action_set=self.action_set,
                                   algorithm=Navigator.A_STAR_ALGORITHM)
        self.navigator.reset_full()
        self._door_range: int = 1
        self.knowledge: Dict[str, Dict] = {}
        # Synchronized knowledge about drop zone
        self.drops: Dict[str, Dict] = {}
        # For each drop zone we assign a certain block
        self.drop_to_block: Dict[str, str] = {}  # <DropId, (BlockId)>
        self.phase = Phase.EXPLORING
        self.message_queue = []
        self.previous_carry_amount = 0
        self.can_grab: List[Dict] = []
        self.current_action_tick_started = -1000
        self.current_action_duration_in_ticks = self.slowdown
        # A list of the goal blocks where we have to deliver to
        self.targets: List[str] = []
        # A map of location -> blockId
        self.dropped: Dict[(int, int), str] = {}
        self.tiles: set = set()
        self.block_range = self.agent_properties['sense_capability'][CollectableBlock]
        self.traverse_map = {}

    def setup(self):
        """
        Our own init function. Called at the very beginning.
        """
        broadcast_collect_blocks(self)
        broadcast_hello_message(self)
        self.traverse_map = self.state.get_traverse_map()

    def map_location(self, door):
        """
        Get a reachable location near the door
        """
        dirs = [(1, 0), (-1, 0), (0, -1), (0, 1)]
        (x, y) = door['location']
        for (d1, d2) in dirs:
            if self.traverse_map[(x + d1, y + d2)]:
                return x + d1, y + d2
        return x, y + 1

    def filter_bw4t_observations(self, state):
        if state['World']['nr_ticks'] == 0:
            self.setup()

        # Send messages at the last tick of the slowdown
        if self.message_queue and self.is_at_last_action_duration_tick(state['World']['nr_ticks']):
            for f, args in self.message_queue:
                f(*args)
            self.message_queue = []

        # If we have no waypoints, then we tell the agent to explore all rooms
        if len(self.navigator.get_all_waypoints()) == 0 and self.phase is Phase.EXPLORING:
            waypoints = []

            # Get the order in which to visit the rooms
            doors = self.get_door_order()

            for door in doors:
                # Append waypoint to location under the door
                waypoints.append(self.map_location(door))
                # Append tiles of corresponding room
                tiles = state.get_room_objects(door['room_name'])

                location_tiles = list(map(lambda x: x['location'], tiles))
                waypoints.extend(location_tiles)

                for x in location_tiles:
                    self.tiles.add(x)

            self.navigator.add_waypoints(waypoints)

        # Save and broadcast encountered blocks
        if self.phase != Phase.DROP:
            # Check which objects can be grabbed from currernt position
            self.can_grab = self.process_knowledge(state)

        # If the agent has successfully picked up an object
        if len(self.state[self.agent_id]['is_carrying']) == self.previous_carry_amount + 1:
            # Send pickup message and assign yourself to first free dropzone for this shape and colour
            picked_up(self, self.state[self.agent_id]['is_carrying'][-1])

        self.previous_carry_amount = len(self.state[self.agent_id]['is_carrying'])

        # If we have something to drop and are not in the dropping phase, switch to the dropping phase
        if 0 != len(self.drop_to_block) and len(self.drop_to_block) == len(self.drops) and self.phase != Phase.DROP:
            self.phase = Phase.DROP
            waypoints = []
            for drop in sorted(self.drop_to_block.keys()):
                blockId = self.drop_to_block[drop]
                if blockId in map(lambda x: x['obj_id'], self.state[self.agent_id]['is_carrying']):
                    loc = self.drops[drop]['location']
                    waypoints.append((loc[0], loc[1]))
                    self.targets.append(drop)
            self.navigator.reset_full()
            self.navigator.add_waypoints(waypoints)

        # Save incoming info about blocks
        handle_messages(self)

        return state

    def decide_on_bw4t_action(self, state: State):

        # Open any nearby closed doors
        if self.phase is Phase.EXPLORING:
            for doorId in self._nearbyDoors(state):
                if not state[doorId]['is_open']:
                    return OpenDoorAction.__name__, {'object_id': doorId}

            current_loc = self.state[self.agent_id]['location']

            if current_loc in self.tiles:
                possible_match = [x for x in self.get_nearby_blocks(self.state) if
                                  any([self.check_partially_look_same(x, y) for y in self.left_to_find().values()])]

                blocks = set(map(lambda x: x['location'], possible_match))

                next_waypoints = list(map(lambda x: x[1], self.navigator.get_upcoming_waypoints()))
                to_remove = list(x for x in next_waypoints if
                                 get_distance(x, current_loc) <= self.block_range and x not in blocks)
                new_waypoints = [x for x in next_waypoints if x not in to_remove]
                self.navigator.reset_full()
                self.navigator.add_waypoints(new_waypoints)

        # Try to grab/drop objects if you are in pickup phase
        elif self.phase is Phase.PICKUP:
            return GrabObject.__name__, {'object_id': random.choice(self.can_grab)['obj_id']}
        elif self.phase is Phase.DROP:
            # Check if the agent is on a drop zone
            if self.targets and self.state[self.agent_id]['location'] == self.state[self.targets[0]]['location']:
                loc = self.state[self.agent_id]['location']
                # Check underneath you
                possible_match = [x for x in self.state.values() if
                                  ('location' in x and x['location'] == (loc[0], loc[1] + 1))]

                # If there is a wall below or a box is dropped immediately below this tile we can drop our box
                # possible_match == 1 means wall underneath
                if len(possible_match) == 1 or (loc[0], loc[1] + 1) in self.dropped or any(
                        [x['is_collectable'] for x in possible_match if 'is_collectable' in x]):
                    object_id = None

                    # Checks to see if any blocks are placed above current location
                    blocks_above = [x for x in self.get_nearby_blocks(self.state) if
                                    x['location'] == (loc[0], loc[1] - 1)]

                    if blocks_above:
                        try:
                            # Try and get the drop zone corresponding to the location (if it exists)
                            new_target = \
                                [x for x in self.drops if self.drops[x]['location'] == blocks_above[0]['location']][0]
                            # Add the above dropzone to the targets list
                            self.targets.insert(1, new_target)
                            # Update the navigator to go through the drop zone above
                            new_waypoints = [self.drops[new_target]['location']]
                            new_waypoints.extend(list(map(lambda x: x[1], self.navigator.get_upcoming_waypoints())))
                            self.navigator.reset_full()
                            self.navigator.add_waypoints(new_waypoints)
                            # Grab the object placed above
                            return GrabObject.__name__, {'object_id': blocks_above[0]['obj_id']}
                        except:
                            pass

                    # Select drop zone the agent is standing on
                    for drop in self.drop_to_block:
                        if self.state[drop]['location'] == loc:
                            object_id = drop
                            break

                    self.targets.pop(0)

                    blockid_to_drop = self.drop_to_block[object_id]

                    # Send drop message after the drop action has been executed
                    self.current_action_tick_started = state['World']['nr_ticks']
                    self.message_queue.append(
                        (dropped, (self, self.knowledge[blockid_to_drop], state[self.agent_id]['location'])))

                    return DropObject.__name__, {'object_id': blockid_to_drop}
                else:
                    # Wait for someone to drop their object before you drop yours
                    return None, {}

        self.state_tracker.update(state)

        try:
            action = self.navigator.get_move_action(self.state_tracker)
        except:
            return None, {}

        return action, {}

    def _nearbyDoors(self, state: State):
        # copy from humanagent
        # Get all doors from the perceived objects
        objects = list(state.keys())
        doors = [obj for obj in objects if 'is_open' in state[obj]]
        doors_in_range = []
        for object_id in doors:
            # Select range as just enough to grab that object
            dist = int(np.ceil(np.linalg.norm(
                np.array(state[object_id]['location']) - np.array(
                    state[self.agent_id]['location']))))
            if dist <= self._door_range:
                doors_in_range.append(object_id)
        return doors_in_range

    def process_knowledge(self, state):
        """
        Broadcast the agent's knowledge about blocks to all other agents
        """
        # Get encountered blocks
        nearby_blocks = self.get_nearby_blocks(state)

        # Save blocks locally
        for block in nearby_blocks:
            self.update_knowledge(block)

        # Broadcast blocks
        if len(nearby_blocks) > 0:
            broadcast_knowledge(self, nearby_blocks)
            # Check if we can grab an object
            grabbable_blocks = self.get_grabbable_blocks(nearby_blocks)

            # If we can grab an object switch to a "grab" phase
            if grabbable_blocks:
                self.phase = Phase.PICKUP

                return grabbable_blocks

        # Otherwise keep exploring
        self.phase = Phase.EXPLORING
        return None

    def assign_block(self, block):
        """
        Called when a PickUp message is received. Assigns a drop zone to the picked up block
        """
        for drop in self.drops:
            if drop not in self.drop_to_block and self.check_look_same(self.drops[drop], self.knowledge[block]):
                self.drop_to_block[drop] = block
                return

    def get_grabbable_blocks(self, blocks):
        """
        Return the blocks which the agent is able to pick up, i.e. in the pickup range,
        and that correspond to a drop zone
        """
        ret = []

        for block in blocks:
            if get_distance(block['location'], self.state[self.agent_id]['location']) <= 1:
                for drop in self.left_to_find().values():
                    if self.check_look_same(drop, self.knowledge[block['obj_id']]):
                        ret.append(block)
                        break

        return ret

    def left_to_find(self):
        """
        Checks which drops don't have a block picked for
        """
        drops_copy = {}
        for drop_key in self.drops:
            if drop_key not in self.drop_to_block:
                drops_copy[drop_key] = self.drops[drop_key]
        return drops_copy

    def check_look_same(self, block1, block2):
        """
        Checks that two shapes look the same
        """
        return ('shape' in block1['visualization'] and 'shape' in block2['visualization']) and (
                block1['visualization']['shape'] == block2['visualization']['shape']) and \
               ('colour' in block1['visualization'] and 'colour' in block2['visualization']) and (
                       block1['visualization']['colour'] == block2['visualization']['colour'])

    def check_partially_look_same(self, block1, block2):
        return ('shape' in block1['visualization'] and 'shape' in block2['visualization']) and (
                block1['visualization']['shape'] == block2['visualization']['shape']) or \
               ('colour' in block1['visualization'] and 'colour' in block2['visualization']) and (
                       block1['visualization']['colour'] == block2['visualization']['colour'])

    def get_nearby_blocks(self, state: State):
        """
        Checks what blocks can be seen from our position.
        Excludes block that can be seen through walls.
        """
        objects = list(state.keys())
        blocks = []

        for obj in objects:
            if "class_inheritance" in state[obj]:
                if state[obj]["class_inheritance"][0] == "CollectableBlock":  # does this cover all blocks??
                    if self.is_reachable(state, state[obj]['location']):
                        blocks.append(state[obj])

        return blocks

    def get_door_order(self):
        """
        Returns the optimal order in which to visit the rooms.
        Starts with the room closest to our current location and iteratively adds the room closest to the last room.
        """
        objects = list(self.state.keys())
        doors = [self.state[obj] for obj in objects if ('door' in obj)]

        ret = []

        current_loc = self.state[self.agent_id]['location']

        while len(doors):
            min_dist = 1e9
            door = None
            for x in doors:
                dist = get_distance(x['location'], current_loc)
                if dist < min_dist:
                    door = x
                    min_dist = dist

            current_loc = door['location']
            doors.remove(door)
            ret.append(door)
        return ret

    def is_reachable(self, state, location):
        """
        Checks if a block can be reached from our current position
        """
        new_waypoint = location
        if new_waypoint == self.state[self.agent_id]['location']:
            return True
        new_navigator = Navigator(agent_id=self.agent_id,
                                  action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)
        new_navigator.add_waypoints([(new_waypoint[0], new_waypoint[1])])
        self.state_tracker.update(state)
        if new_navigator.get_move_action(self.state_tracker):
            return True
        return False

    def update_knowledge(self, block):
        """
        Updates our knowledge of the positions of blocks with newly received information
        """
        block_id = block["obj_id"]
        if block_id in self.knowledge:
            old_visualization = self.knowledge[block_id]["visualization"].copy()

            self.knowledge[block_id].update(block)
            self.knowledge[block_id]["visualization"] = old_visualization

            self.knowledge[block_id]["visualization"].update(block["visualization"])
        else:
            self.knowledge[block_id] = block

    def update_drops(self, drop):
        """
        Updates our knowledge of how the drop zones look like
        """
        drop_id = drop['obj_id']

        if drop_id in self.drops:
            old_visualization = self.drops[drop_id]['visualization'].copy()

            self.drops[drop_id].update(drop)
            self.drops[drop_id]['visualization'] = old_visualization

            self.drops[drop_id]['visualization'].update(drop['visualization'])
        else:
            self.drops[drop_id] = drop

    def is_at_last_action_duration_tick(self, curr_tick):
        """
        Returns True if this agent is at its last tick of the action's duration.
        """
        is_last_tick = curr_tick == (self.current_action_tick_started + self.current_action_duration_in_ticks)
        return is_last_tick
