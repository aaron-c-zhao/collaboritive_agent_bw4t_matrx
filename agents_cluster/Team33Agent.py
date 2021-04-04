import operator
from typing import final, List, Dict, Final
import numpy as np  # type: ignore
import random  # type: ignore

from matrx import utils
from matrx.agents import StateTracker, Navigator
from matrx.actions import MoveNorth, OpenDoorAction, CloseDoorAction, GrabObject, DropObject  # type: ignore
from matrx.actions.move_actions import MoveEast, MoveSouth, MoveWest  # type: ignore
from matrx.agents.agent_utils.state import State  # type: ignore
from matrx.messages.message import Message

from bw4t.BW4TBrain import BW4TBrain


# Creates a message object ready to be sent to all agents, with a description
def make_message(msg, desc, agent_id):
    obj = {'agent_id': agent_id, 'type': desc}

    if desc == "BlockFound":
        obj['data'] = {}
        obj['data']['blocks'] = msg

    elif desc == 'PickUp':
        obj['data'] = {}
        obj['data']['obj_id'] = msg['obj_id']

    elif desc == 'Dropped':
        obj['data'] = {}
        obj['data']['location'] = msg['location']
        obj['data']['obj_id'] = msg['obj_id']

    return obj


# Checks whether there is a block for which the agent knows both its shape and colour, and it can be put on
# one of the targets.
def check_if_object_corresponds_to_target(available_objects, target_objects):
    for key in available_objects.keys():
        for obj in available_objects[key]:
            keys = obj.keys()
            if 'colour' in keys and 'shape' in keys:
                color = obj['colour']
                shape = obj['shape']
                for target_obj in target_objects:
                    target_color = target_obj['colour']
                    target_shape = target_obj['shape']
                    if color == target_color and shape == target_shape:
                        return obj, target_obj
    return None, None


# If there is any information contained in the observation_object which the agent still doesn't know
# then add it to the all_objects object, which contains information about all object with type as the
# observation_object.
def add_observation_object(observation_object, all_objects):
    if not any(b['obj_id'] == observation_object['obj_id'] for b in
               all_objects):  # If there is no object with that ID, just add it
        obj_to_add = {'obj_id': observation_object['obj_id'], 'location': observation_object['location']}
        if 'shape' in observation_object['visualization'].keys():
            obj_to_add['shape'] = observation_object['visualization']['shape']
        if 'colour' in observation_object['visualization'].keys():
            obj_to_add['colour'] = observation_object['visualization']['colour']
        all_objects.append(obj_to_add)
    else:  # If there is an object with that ID, check if we can add new information (e.g shape or colour to it)
        object_already_there = next(
            curr_object for curr_object in all_objects if curr_object['obj_id'] == observation_object['obj_id'])
        object_already_there_keys = object_already_there.keys()
        if 'shape' not in object_already_there_keys and 'shape' in observation_object['visualization'].keys():
            object_already_there['shape'] = observation_object['visualization']['shape']
        if 'colour' not in object_already_there_keys and 'colour' in observation_object['visualization'].keys():
            object_already_there['colour'] = observation_object['visualization']['colour']


# Call the add_observation_object method for every object in found_objects.
def add_observation_objects(found_objects, all_objects):
    for obj in found_objects:
        add_observation_object(obj, all_objects)


# Compress the information for an object (target, block) to what we will need in our implementation.
def parse_block(block):
    parsed_block = {'obj_id': block['obj_id'], 'location': block['location']}
    if 'shape' in block['visualization']:
        parsed_block['shape'] = block['visualization']['shape']
    if 'colour' in block['visualization']:
        parsed_block['colour'] = block['visualization']['colour']
    return parsed_block


# Compress the information about all blocks nearby
def get_nearby_blocks(state: State):
    objects = list(state.keys())
    blocks = [state[obj] for obj in objects if 'is_collectable' in state[obj]]
    blocks = [block for block in blocks if block['is_collectable']]
    return blocks


# Returns what the agent sees for all targets.
def get_drop_off_blocks(state):
    drop_off_blocks = []
    for key in state.keys():
        info = state[key]
        if any('is_goal_block' in x for x in info.keys()):
            if info['is_goal_block']:
                drop_off_blocks.append(info)
    return drop_off_blocks


class Team33Agent(BW4TBrain):
    '''
    This is the agent created by Group33. NOTE: Our agent first adds all blocks to their target, and in case they
    weren't added in the right order, simply one agent goes and grabs and drops the objects in the required order.
    '''

    def __init__(self, settings: Dict[str, object]):
        super().__init__(settings)
        self._moves = [MoveNorth.__name__, MoveEast.__name__, MoveSouth.__name__, MoveWest.__name__]

        # Targets are stored here in the format provided in the parse_block method.
        self.drop_off_blocks = []

        # Room names are stored here.
        self.room_data = None

        # Dictionary, for which the key is the room name, and the value - a list, consisting of all blocks
        # inside the room in the format provided in the parse_block method.
        self.objects = []

        # Here the id's of objects picked by any agent are stored.
        self.taken_objects = set()

        # Used for storing targets' shapes and locations
        self.target_visualizations = []

        # Stores the names of all agents.
        self.agents = None

        # Becomes True if the agent waited on the previous turn (in case of colliding agents).
        # Prevents agent from waiting infinitely.
        self.already_waited = False

        # This number shows how many objects were carried on the previous step.
        # Used to identify whether an object was successfully taken or not.
        self.number_of_carried_objects = 0

        # This boolean is used in order to check that we test with agents from the same cluster as ours.
        self.is_tested_with_same_cluster_agents = False

    def initialize(self):
        super().initialize()
        self._door_range = 1

    # We do not further filter the state.
    def filter_bw4t_observations(self, state) -> State:
        return state

    # This function is used to process the received messages.
    def process_messages(self, state):
        for message in self.received_messages:
            # If the message scheme is different, simply break the loop.
            if 'type' not in message.keys():
                break
            # Adds new information (if present) for a target/block.
            if message['type'] == 'BlockFound':
                # If the agents we are testing with aren't from our cluster, just continue to next message.
                # Since one of them can be a Hello message.
                if not self.is_tested_with_same_cluster_agents:
                    continue
                for block in message['data']['blocks']:
                    # If it is a block, then add info the agent still doesn't know for this block (if present).
                    if block['is_collectable']:
                        add_observation_object(block, self.objects)
                    # Else, add info the agent still doesn't know for this target (if present), and also
                    # adds the visualization of the target to the target_visualization list.
                    else:
                        add_observation_object(block, self.drop_off_blocks)
                        current_block = next(drop_off for drop_off in self.drop_off_blocks
                                             if block['obj_id'] == drop_off['obj_id'])
                        if 'shape' in current_block and 'colour' in current_block \
                                and len(self.target_visualizations) < len(self.drop_off_blocks):
                            self.target_visualizations.append((current_block['shape'], current_block['colour']))

            # If an object was picked up, then add it to the taken_objects list and remove the visualization
            # of this object from target_visualizations, so that this agent doesn't try to pick up an object
            # with the same visualization.
            elif message['type'] == 'PickUp':
                # If the agents we are testing with aren't from our cluster, just continue to next message.
                # Since one of them can be a Hello message.
                if not self.is_tested_with_same_cluster_agents:
                    continue
                grabbed_block = next(block for block in self.objects if block['obj_id'] == message['data']['obj_id'])
                self.taken_objects.add(grabbed_block['obj_id'])
                target = next(((shape, colour) for (shape, colour) in self.target_visualizations
                              if grabbed_block['shape'] == shape and grabbed_block['colour'] == colour), None)
                if target is not None:
                    self.target_visualizations.remove(target)

            # If an object was dropped, then in case it was dropped on its target, remove the target from the
            # drop_off_blocks list, so that this agent does not try to put a block on this target.
            # If it is dropped somewhere else, just remove it from the taken_objects list, so that the agent can pick
            # it up again, and update its location.
            elif message['type'] == 'Dropped':
                # If the agents we are testing with aren't from our cluster, just continue to next message.
                # Since one of them can be a Hello message.
                if not self.is_tested_with_same_cluster_agents:
                    continue
                drop_location = message['data']['location']
                drop_off = next((drop for drop in self.drop_off_blocks if drop['location'] == drop_location), None)
                if drop_off is not None:
                    self.drop_off_blocks.remove(drop_off)
                else:
                    dropped_block = next(
                        block for block in self.objects if block['obj_id'] == message['data']['obj_id'])
                    self.taken_objects.remove(dropped_block['obj_id'])
                    dropped_block['location'] = message['data']['location']

            # If it is a hello message, then we know that we test with agents from the same cluster as ours.
            elif message['type'] == 'Hello':
                self.is_tested_with_same_cluster_agents = True

    # We decide on action in this method.
    def decide_on_bw4t_action(self, state: State):
        # First, process all new messages if we are using agents from the same cluster.
        self.process_messages(state)

        # If this is the first iteration, send a hello message so that it is known that we test
        # with our cluster.
        if self.agents is None:
            mess = [make_message({}, 'Hello', self.agent_id)]
            self.send_msg(mess)
            self.received_messages = []

        # If this is the first iteration and we haven't stored the names of all agents.
        if self.agents is None:
            self.agents = [agent['name'] for agent in state.get_agents()]
            self.agents.sort()

        messages = []

        # Check whether a new block was successfully taken. In case it was - send a message to all other
        # agents that this agent has taken this block.
        blocks = state.get_self()['is_carrying']
        if len(blocks) > self.number_of_carried_objects:
            target_block = parse_block(blocks[-1])
            self.taken_objects.add(target_block['obj_id'])
            target = next((shape, colour) for (shape, colour) in self.target_visualizations
                          if target_block['shape'] == shape and target_block['colour'] == colour)
            self.target_visualizations.remove(target)
            messages.append(make_message(target_block, 'PickUp', self.agent_id))
        self.number_of_carried_objects = len(blocks)

        # Get information for the nearby blocks, and in case there is such information, update
        # the agent's view on the blocks and add it as a message to the other agents.
        blocks = get_nearby_blocks(state)
        if len(blocks) > 0:
            messages.append(make_message(blocks, 'BlockFound', self.agent_id))
            add_observation_objects(blocks, self.objects)

        state_tracker = StateTracker(agent_id=self.agent_id)
        navigator = Navigator(agent_id=self.agent_id,
                              action_set=self.action_set, algorithm=Navigator.A_STAR_ALGORITHM)
        navigator.reset_full()

        # If this is the first iteration and we haven't stored the room names for all rooms.
        if not self.room_data and not self.drop_off_blocks:
            self.room_data = state.get_all_room_names()

        curr_location = self.agent_properties['location']

        # Check if there are any agents at the same location as this one.
        agents_on_same_position = []
        for agent in state.get_agents():
            if agent['location'] == curr_location:
                agents_on_same_position.append(agent['name'])
        agents_on_same_position.sort()

        # If there are, then only the agent with the smallest alphabetical name would make a move.
        # This is in order to prevent that 2 agents grab one object at the same time. Also, if the
        # agent has waited on the previous step, it will definitely make a move now.
        if state.get_self()['name'] != agents_on_same_position[0] and not self.already_waited:
            self.already_waited = True
            act: tuple = (None, {})
            if len(messages) > 0:
                self.send_msg(messages)
            self.received_messages = []
            return act

        self.already_waited = False

        # If all target blocks have been taken, go and deliver them to their target.
        if self.drop_off_blocks and not self.target_visualizations:
            # Firstly, get all locations on which any object the agent carries can be put, and sort them
            # by which location should be delivered first.
            carried_objects = state.get_self()['is_carrying']
            locations = []
            for drop_off in self.drop_off_blocks:
                target = next((obj for obj in carried_objects if obj['visualization']['shape'] == drop_off['shape']
                               and obj['visualization']['colour'] == drop_off['colour']), None)
                if target is not None:
                    locations.append(drop_off['location'])

            locations.sort(key=operator.itemgetter(1), reverse=True)

            # If an agent doesn't have any objects to deliver, it simply stays.
            if len(locations) == 0:
                if len(messages) > 0:
                    self.send_msg(messages)
                self.received_messages = []
                # print("I don't have any targets to deliver.")
                return None, {}

            # If the agent is already on the location to drop an object:
            if curr_location == locations[0]:
                width, length = state.get_world_info()['grid_shape']
                location_below = (curr_location[0], curr_location[1] + 1)
                # If there are still other objects that need to be delivered before it delivers
                # its object, simply wait.
                if location_below[1] < width and next((drop for drop in self.drop_off_blocks
                                                       if drop['location'] == location_below), None) is not None:
                    if len(messages) > 0:
                        self.send_msg(messages)
                    self.received_messages = []
                    # print("Waiting for an agent to drop on previous location.")
                    return None, {}

                # Else, drop the object and remove the target from the yet undropped targets.
                curr_target = next(target for target in self.drop_off_blocks if target['location'] == curr_location)
                id_to_put = next(obj['obj_id'] for obj in carried_objects if obj['visualization']['shape'] ==
                                 curr_target['shape'] and obj['visualization']['colour'] == curr_target['colour'])
                obj_to_send = {'location': curr_location, 'obj_id': id_to_put}
                messages.append(make_message(obj_to_send, 'Dropped', self.agent_id))
                self.send_msg(messages)
                self.received_messages = []
                self.drop_off_blocks.remove(curr_target)
                return DropObject.__name__, {'object_id': id_to_put}
            # Else, go towards this location.
            else:
                navigator.add_waypoints([locations[0]])
                state_tracker.update(state)
                action = navigator.get_move_action(state_tracker=state_tracker)
                act: tuple = (action, {})
                if len(messages) > 0:
                    self.send_msg(messages)
                self.received_messages = []
                return act

        # If this is the first iteration and we haven't stored the target objects, we store them
        if not self.drop_off_blocks:
            drops = get_drop_off_blocks(state)
            self.drop_off_blocks = [parse_block(block) for block in drops]
            if not self.target_visualizations:
                for drop_off in self.drop_off_blocks:
                    if 'shape' not in drop_off.keys() or 'colour' not in drop_off.keys():
                        break
                    self.target_visualizations.append((drop_off['shape'], drop_off['colour']))
            messages.append(make_message(drops, "BlockFound", self.agent_id))

        # If there is an object, for which we know that it can be put on a target, the agent will go and take it.
        target_block = self.check_if_target_object_is_known(curr_location, state, state_tracker, navigator)
        if target_block is not None:
            # If the agent's curent location is the same as the object's, grab it and remove its visualization
            # from the target_visualizations list, so that no other agents would try to get an object with the
            # same visualization, and for the same target.
            if target_block['location'] == curr_location:
                if len(messages) > 0:
                    self.send_msg(messages)
                self.received_messages = []
                return GrabObject.__name__, {'object_id': target_block['obj_id']}
            # Else, go towards the object.
            else:
                navigator.add_waypoints([target_block['location']])

            state_tracker.update(state)
            action = navigator.get_move_action(state_tracker=state_tracker)
            act: tuple = (action, {})
            if len(messages) > 0:
                self.send_msg(messages)
            self.received_messages = []
            return act

        closest_door = self.get_closest_door(curr_location, state)
        # If there isn't a block we can deliver to a target, we simply go to a room in which we can find more blocks.
        if closest_door is not None:
            closest_door_name = closest_door['obj_id']
            closest_door_location = closest_door['location']
            location_above_closest_door = (closest_door_location[0], closest_door_location[1] - 1)
            location_below_closest_door = (closest_door_location[0], closest_door_location[1] + 1)
            location_two_above_closest_door = (closest_door_location[0], closest_door_location[1] - 2)

            below_closest_door = closest_door_location[0] == curr_location[0] and curr_location[1] - 1 == \
                                 closest_door_location[1]

            # If we are below the closest door and the door isn't opened, we open it.
            if below_closest_door and not state[closest_door_name]['is_open']:
                if len(messages) > 0:
                    self.send_msg(messages)
                self.received_messages = []
                return OpenDoorAction.__name__, {'object_id': closest_door_name}

            # Else, if it is open, then we head towards the first location above the door.
            elif below_closest_door and state[closest_door_name]['is_open']:
                navigator.add_waypoints([location_above_closest_door])

            # Else, if we are on the door, we head towards the square above it.
            elif closest_door_location == curr_location:
                navigator.add_waypoints([location_above_closest_door])

            # Else, if we are above the door, we want to go one more square above, so that we have all
            # the information from the room.
            elif location_above_closest_door == curr_location:
                navigator.add_waypoints([location_two_above_closest_door])

            # Else, if we have already taken all information from this room, we remove it from the room_data list
            # so that the agent doesn't go in this room again.
            elif location_two_above_closest_door == curr_location:
                for room in self.room_data:
                    door = state.get_closest_room_door(room)
                    if door is None:
                        continue
                    if door[0]['location'] == closest_door['location']:
                        self.room_data = [x for x in self.room_data if x != room]
                        break
                next_door = self.get_closest_door(curr_location, state)
                # If there is another unexplored room, head towards it.
                if next_door is not None:
                    next_door_location = next_door['location']
                    location_below_next_door = (next_door_location[0], next_door_location[1] + 1)
                    navigator.add_waypoints([location_below_next_door])
                # Else, just stay (this probably shouldn't happen ever in a good case).
                else:
                    if len(messages) > 0:
                        self.send_msg(messages)
                    self.received_messages = []
                    # print("No next door found!")
                    return None, {}
            # Else, just leave the room.
            else:
                navigator.add_waypoints([location_below_closest_door])

            state_tracker.update(state)
            action = navigator.get_move_action(state_tracker=state_tracker)

        # In case nothing worked, just do a random move.
        else:
            action = random.choice(self._moves)

        act: tuple = (action, {})
        if len(messages):
            self.send_msg(messages)

        self.received_messages = []
        return act

    # Gets the doors nearby.
    def _nearby_doors(self, state: State):
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

    # Returns the closest door to curr_location.
    def get_closest_door(self, curr_location, state):
        min_distance = 290102381230
        closest_door = None
        for room in self.room_data:
            curr_door = state.get_closest_room_door(room)
            if curr_door is None:
                continue
            curr_distance = utils.get_distance(curr_location, curr_door[0]['location'])
            if curr_distance < min_distance:
                closest_door = curr_door[0]
                min_distance = curr_distance
        return closest_door

    # This method returns the closest block, for which we with certainty know that it can be put on a target.
    # If such a block doesn't exist, it returns None.
    def check_if_target_object_is_known(self, current_location, state, state_tracker: StateTracker,
                                        navigator: Navigator):
        possible_blocks = []
        for block in self.objects:
            if block['obj_id'] in self.taken_objects or 'shape' not in block.keys() or 'colour' not in block.keys():
                continue
            for target in self.target_visualizations:
                if target[0] == block['shape'] and target[1] == block['colour']:
                    navigator.reset_full()
                    navigator.add_waypoints([block['location']])
                    state_tracker.update(state)
                    action = navigator.get_move_action(state_tracker=state_tracker)
                    if action is not None or current_location == block['location']:
                        possible_blocks.append(block)
        navigator.reset_full()
        if not possible_blocks:
            # print("No blocks! :(")
            return None
        possible_blocks.sort(key=lambda bl: (bl['location'][0] - current_location[0]) ** 2
                                            + (bl['location'][1] - current_location[1]) ** 2)
        return possible_blocks[0]

    # This method is used to send a message, containing the parameter objects in it.
    def send_msg(self, objects):
        for obj in objects:
            msg = Message(content=obj, from_id=self.agent_id)
            self.send_message(msg)
