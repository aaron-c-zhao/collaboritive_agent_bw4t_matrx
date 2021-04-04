from typing import Dict
import numpy
from matrx.actions import MoveNorth, OpenDoorAction  # type: ignore
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest  # type: ignore
from matrx.agents import StateTracker, Navigator
from matrx.agents.agent_utils.state import State  # type: ignore
from matrx.messages import Message

from bw4t.BW4TBrain import BW4TBrain


class Team22Agent(BW4TBrain):
    # 0 means go to a new room
    # 1 means go into room and store blocks
    # 2 means check if we have goal block in cache
    # 3 means deliver goal block to drop zone
    goal = 0
    separator_string = ';;;'

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        # Init variables
        self.navigator_running = False
        self.traversed_rooms = {}
        self.other_agents = []
        self.blocks = []
        self.wait = 0
        self.delivered_block_ids = []
        self.state_tracker = None
        self.room_name_to_enter = None
        self.navigator = None
        self.block_target_id = None
        self.goal_blocks = None
        self._door_range = 1
        self._moves = [MoveNorth.__name__, MoveEast.__name__, MoveSouth.__name__, MoveWest.__name__]

    def initialize(self):
        super().initialize()
        # Setup tracker
        self.state_tracker = StateTracker(agent_id=self.agent_id)
        self.navigator = Navigator(agent_id=self.agent_id,
                                   action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)

    def filter_bw4t_observations(self, state):
        #print((self.goal_blocks))
        new_blocks = []
        # Init goal blocks (in correct order)
        if self.goal_blocks is None:
            self.goal_blocks = [x for x in state.values() if 'is_goal_block' in x and x['is_goal_block']]
            # Share goal blocks
            #content = 'goal_blocks' + self.separator_string + json.dumps(self.goal_blocks)
            new_blocks = self.goal_blocks
            content = {'type': "Hello"}
            self.send_message(Message(content=content, from_id=self.agent_id))
            #self.send_message(Message(content=content, from_id=self.agent_id))

        self.handle_messages()
        self.state_tracker.update(state)
        # Store blocks we see in our cache
        for b in state.values():
            # Not a block
            if 'is_collectable' not in b or not b['is_collectable']:
                continue
            # If block in a random room, don't perceive it
            room_name = b['name'].split(' ')[2]
            if room_name not in self.traversed_rooms:
                continue
            # If delivered block, don't perceive it
            if b['obj_id'] in self.delivered_block_ids:
                continue

            # If a new block, cache it
            cached_block = next((x for x in self.blocks if x.id == b['obj_id']), None)
            block = {
                'is_goal_block': b['is_goal_block'],
                'is_collectable': b['is_collectable'],
                'obj_id': b['obj_id'],
                'location': b['location'],
                'visualization': b['visualization']
            }
            new_blocks.append(block)
            if cached_block is None:
                self.blocks.append(Block(block))
            else:
                for cached_block_ in self.blocks:
                    if cached_block_.id == b['obj_id']:
                        if cached_block_.shape is None:
                            cached_block_.shape = b['visualization'].get('shape')
                        if cached_block_.color is None:
                            cached_block_.color = b['visualization'].get('colour')
        if new_blocks:
            content = format_message("BlockFound", new_blocks, None, None, self.agent_id)
            self.send_message(Message(content=content, from_id=self.agent_id))
        return state

    def decide_on_bw4t_action(self, state: State):
        # Do a move based on our current goal
        move = None, {}
        #print(self.goal)
        try:
            # Explore rooms
            if self.goal == 0:
                move = self.scout_rooms(state)
            if self.goal == 1:
                move = self.explore_room(state)
            if self.goal == 2:
                move = self.find_goal_block(state)
            if self.goal == 3:
                move = self.pick_up_block()
            if self.goal == 4:
                move = self.deliver_goal_block()
        # Do nothing if exception
        except Exception:
            pass
        return move

    def scout_rooms(self, state: State):
        if not self.navigator_running:
            self.navigator_running = True
            # Find closest new room that is traversable
            target_location = None
            target_room_name = None
            dist = None
            for room_name in state.get_all_room_names():
                if room_name != 'world_bounds':
                    door = state.get_closest_room_door(room_name)[0]
                    # If new
                    try:
                        self.traversed_rooms[room_name]
                    except:
                        # If can get in distance of 1
                        loc = find_traversable_location_adjacent(state.get_traverse_map(), door['location'])
                        if loc is not None:
                            # If closer than current
                            if dist is None or state.get_distance_map()[loc] < dist:
                                target_location = loc
                                target_room_name = room_name
                                dist = state.get_distance_map()[loc]

            self.room_name_to_enter = target_room_name
            self.navigator.add_waypoint(target_location)
        elif self.navigator.is_done:
            # We have reached loc
            self.navigator_running = False
            self.navigator.reset_full()
            self.goal = 1

        return self.navigator.get_move_action(self.state_tracker), {}

    def explore_room(self, state: State):
        # If we haven't opened the door yet
        if not state.get_closest_room_door(self.room_name_to_enter)[0]['is_open']:
            return OpenDoorAction.__name__, \
                   {'object_id': state.get_closest_room_door(self.room_name_to_enter)[0]['obj_id']}

        # Move through the room
        if not self.navigator_running:
            self.navigator_running = True
            self.navigator.add_waypoints([x['location'] for x in state.get_room_objects(self.room_name_to_enter)])
            self.traversed_rooms[self.room_name_to_enter] = True
        elif self.navigator.is_done:
            self.navigator_running = False
            self.navigator.reset_full()
            self.goal = 2
        return self.navigator.get_move_action(self.state_tracker), {}

    def find_goal_block(self, state: State):
        if not self.navigator_running:
            targets = []
            for b in self.blocks:
                if b.shape == self.goal_blocks[0]['visualization'].get('shape') and \
                        b.color == self.goal_blocks[0]['visualization'].get('colour'):
                    targets.append(b)
            if targets:
                target = self.get_closest_block(targets)
            # If block is not found, keep scouting
            else:
                self.goal = 0
                return self.scout_rooms(state)


            # Block is found, go collect it
            self.navigator_running = True
            self.navigator.add_waypoint(target.location)
            self.block_target_id = target.id

        elif self.navigator.is_done:
            self.navigator_running = False
            self.navigator.reset_full()
            self.goal = 3
        return self.navigator.get_move_action(self.state_tracker), {}

    def pick_up_block(self):
        # Pick up block
        if len(self.agent_properties['is_carrying']) == 0:
            #print("I WANT TO PICK")
            self.wait = 0
            self.goal = 4
            return 'GrabObject', {'object_id': self.block_target_id}
        else:
            return self.navigator.get_move_action(self.state_tracker), {}

    def deliver_goal_block(self):
        #if len(self.agent_properties['is_carrying']) == 1:
         #   print(self.agent_id)
          #  print(len(self.agent_properties['is_carrying']))
        #print(self.navigator_running)

        # Deliver it to drop zone
        if not self.navigator_running and len(self.agent_properties['is_carrying']) == 1:
            #print(self.agent_id)
            #print("Check in 1")
            content = format_message("PickUp", None, self.block_target_id, None, self.agent_id)
            self.send_message(Message(content=content, from_id=self.agent_id))
            self.navigator_running = True
            self.navigator.add_waypoint(self.goal_blocks[0]['location'])

        if not self.navigator_running and len(self.agent_properties['is_carrying']) == 0 and self.wait == 1:
            #print(self.agent_id)
            #print("HELLOOOO")
            del self.goal_blocks[0]
            self.block_target_id = None
            self.goal = 0
            self.wait = 0

        elif self.navigator.is_done:
            #print("Check in 2")
            self.navigator_running = False
            self.navigator.reset_full()
            del self.goal_blocks[0]
            self.goal = 2
            # Tell agents a goal block has been delivered
            agent_loc = self.state_tracker.get_memorized_state()[self.agent_id]['location']
            content = format_message("Dropped", None, self.block_target_id, agent_loc, self.agent_id)
            self.send_message(Message(content=content, from_id=self.agent_id))
            # Delete the block from cache
            self.delivered_block_ids.append(self.block_target_id)
            cached_block = None
            for cached_block_ in self.blocks:
                if cached_block_.id == self.block_target_id:
                    cached_block = cached_block_
            if cached_block is not None:
                self.blocks.remove(cached_block)
            return 'DropObject', {'object_id': self.block_target_id}

        self.wait += 1
        return self.navigator.get_move_action(self.state_tracker), {}
        
    def handle_messages(self):
        for m in self.received_messages:

            try:
                if m['type'] == "BlockFound":
                    for block in m['data']["blocks"]:
                        if block['is_goal_block']:
                            for cached_goal_block in self.goal_blocks:
                                if cached_goal_block['obj_id'] == block['obj_id']:
                                    if cached_goal_block['visualization'].get('shape') is None:
                                        cached_goal_block['visualization']['shape'] = block['visualization'].get('shape')
                                    if cached_goal_block['visualization'].get('colour') is None:
                                        cached_goal_block['visualization']['colour'] = block['visualization'].get('colour')
                        else:
                            cached_block = next((x for x in self.blocks if x.id == block['obj_id']), None)
                            if cached_block is None:
                                self.blocks.append(Block(block))
                            else:
                                for cached_block_ in self.blocks:
                                    if cached_block_.id == block['obj_id']:
                                        if cached_block_.shape is None:
                                            cached_block_.shape = block['visualization'].get('shape')
                                        if cached_block_.color is None:
                                            cached_block_.color = block['visualization'].get('colour')

                if m["type"] == "PickUp":
                    if m['agent_id'] != self.agent_id:
                        block_id = m['data']['obj_id']
                        for cached_block in self.blocks:
                            if cached_block.id == block_id:
                                self.blocks.remove(cached_block)
                                for goal_block in self.goal_blocks:
                                    if goal_block['visualization'].get('shape') == cached_block.shape and goal_block['visualization'].get('colour') == cached_block.color:
                                        self.goal_blocks.remove(goal_block)



                # Goal block has been delivered
                if m['type'] == "Dropped":
                    if m['agent_id'] != self.agent_id:
                        block_id = m['data']['obj_id']
                        self.delivered_block_ids.append(block_id)
                        cached_block = None
                        for cached_block_ in self.blocks:
                            if cached_block_.id == block_id:
                                cached_block = cached_block_
                        if cached_block is not None:
                            self.blocks.remove(cached_block)
                        for goal_block in self.goal_blocks:
                            if goal_block['visualization'].get('shape') == cached_block.shape and goal_block['visualization'].get('colour') == cached_block.color:
                                self.goal_blocks.remove(goal_block)
            except Exception:
                pass

        self.received_messages = []

    def get_closest_block(self, blocks):
        closest_dist = float('inf')
        closest_block = None
        agent_loc = self.state_tracker.get_memorized_state()[self.agent_id]['location']
        point1 = numpy.array((agent_loc[0], agent_loc[1], 0))
        for block in blocks:
            point2 = numpy.array((block.location[0], block.location[1], 0))
            dist = numpy.linalg.norm(point1 - point2)
            if closest_dist > dist:
                closest_dist = dist
                closest_block = block
        return closest_block

class Block:
    def __init__(self, obj):
        self.id = obj['obj_id']
        self.shape = obj['visualization'].get('shape')
        self.color = obj['visualization'].get('colour')
        self.location = (obj['location'][0], obj['location'][1])


def find_traversable_location_adjacent(traverse_map, loc):
    if traverse_map[loc]:
        return loc
    if traverse_map[(loc[0] - 1, loc[1])]:
        return loc[0] - 1, loc[1]
    if traverse_map[(loc[0] + 1, loc[1])]:
        return loc[0] + 1, loc[1]
    if traverse_map[(loc[0], loc[1] + 1)]:
        return loc[0], loc[1] + 1
    if traverse_map[(loc[0], loc[1] - 1)]:
        return loc[0], loc[1] - 1
    return None

def format_message(type, blocks, obj_id, location, agent_id):
    message = ""
    if type == "BlockFound":
        message = {
            'agent_id': agent_id,
            'type': type,
            'data': {'blocks': blocks}
        }
    if type == "PickUp":
        message = {
            'agent_id': agent_id,
            'type': type,
            'data': {'obj_id': obj_id}
        }
    if type == "Dropped":
        message = {
            'agent_id': agent_id,
            'type': type,
            'data': {'location': location,
                'obj_id': obj_id}
        }
    return message