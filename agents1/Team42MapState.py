import operator

import matrx.utils
from matrx.messages import Message


class MapState:
    '''
    Aid the agents during the process. Preserve information gained from state or messages since those get
    lost very soon. Represents the internal state of the agent.

    This class also implements utility functions related to map data. See public methods for the API.
    '''

    def __init__(self, state):
        '''
        block = {
            'id' : (string)unique id of the block. Can be used to distinguish different blocks.
            'location': (x, y) location of the block
            'room': room_x room name in where the block resides
            'shape': 0|1|2 shape of the block(could be None)
            'colour': (string) colour of the block(could be None)
            'visited': The block will be marked as visited(3) when both the shape info and the colour
                info have been discovered. Otherwise, this attribute has value 1 for having shape info only,
                and 2 for having colour info only.
            'is_collectable': this attribute is mainly used to distinguish ghost_blocks from normal block. When a ghost
                is discovered, it only updates the drop_zone information and leave the blocks alone.
        }

        '''
        self.message_queue = []  # message to be sent
        self.agent_id = state.get_self()['obj_id']  # id of the agent
        self.blocks = {}  # all the blocks that has been discovered by the agents exclude the ones that is carried by agents.
        self.carried_blocks = {}  # the blocks that have been confiremed carried by the agent
        self.team_members = {}
        self.agent_location = None
        self._queue_message('Hello', None)
        self._get_drop_zone(state)  # retrieve the information about drop zone
        self._get_rooms(state)  # retrieve the map information
        self.received_blocks = {}
        self.agent_ability = None

        for agent_id in state['World']['team_members']:
            self.team_members[agent_id] = {}
            self.team_members[agent_id]['carried_blocks'] = []
            self.team_members[agent_id]['ability'] = None

    def _update_ghost_block(self, ghost_blocks, is_parsed):
        '''
        When a non-collectable block is discovered, its information is used to update
        the drop_zone knowledge of the agent.
        '''
        if ghost_blocks is not None:
            ghost_blocks_parsed = ghost_blocks
            if not is_parsed:
                ghost_blocks_parsed = self._parse_blocks(ghost_blocks)
            for ghost_block in ghost_blocks_parsed:
                for drop_spot in self.goal_blocks:
                    if ghost_block['location'] == drop_spot['location']:
                        if ghost_block['colour'] is not None:
                            drop_spot['properties']['colour'] = ghost_block['colour']
                        if ghost_block['shape'] is not None:
                            drop_spot['properties']['shape'] = ghost_block['shape']

    def _extract_room(self, room):
        '''
        Extract the room id.
        '''
        if isinstance(room, str):
            words = room.split()
            return words[len(words) - 1]
        else:
            return None

    def _get_block_status(self, block, is_parsed):
        '''
        only has shape = 1
        only has colour = 2
        visited = 3
        '''
        has_shape = (is_parsed and (block['shape'] is not None)) or \
                    (not is_parsed and 'shape' in block['visualization'].keys())

        has_color = (is_parsed and (block['colour'] is not None)) or \
                    (not is_parsed and 'colour' in block['visualization'].keys())

        return (has_color << 1) | has_shape

    def _update_block(self, blocks):
        '''
        assert (blocks) are parsed
        '''
        res = []
        for block in blocks:
            # if it's a goal block
            if not block['is_collectable']:
                self._update_ghost_block([block], True)
                continue
            # if it's a normal block
            updated, to_be_updated = self._update_collectable_blocks(self.blocks, block)

            for drop_spot in self.goal_blocks:
                # if the block discovered is in the drop zone then update the drop_zone
                if to_be_updated['location'] == drop_spot['location']:
                    if to_be_updated['is_collectable']:
                        drop_spot['filled'] = to_be_updated['id']
                    else:
                        self._update_ghost_block([to_be_updated], True)

            self.blocks[block['id']] = to_be_updated  # only update the blocks when the block is collectable
            if updated:
                res.append(to_be_updated)  # return list of updated blocks

        # queue a message with all updated blocks
        if len(res) > 0:
            return res

    def _blocks_to_message_format(self, blocks):
        '''
        raw blocks to message format
        '''
        res = []
        for raw_block in blocks:
            message_block = {
                'is_goal_block': raw_block['is_goal_block'],
                'is_collectable': raw_block['is_collectable'],
                'obj_id': raw_block['obj_id'],
                'location': raw_block['location'],
                'visualization': raw_block['visualization']
            }
            res.append(message_block)
        return res

    def _update_collectable_blocks(self, blocks_container, candidate):
        to_be_updated = blocks_container.pop(candidate['id'], None)  # check if the block is already in the collection
        updated = False
        if to_be_updated is None:  # add new entry into the collection
            to_be_updated = candidate
            updated = True
        else:  # update shape, colour and status of the block if the block is in the collection
            if to_be_updated['location'] != candidate['location']:
                to_be_updated['location'] = candidate['location']
                updated = True
            if candidate['shape'] is not None and to_be_updated['shape'] != candidate['shape']:
                to_be_updated['shape'] = candidate['shape']
                updated = True
            if candidate['colour'] is not None and to_be_updated['colour'] != candidate['colour']:
                to_be_updated['colour'] = candidate['colour']
                updated = True
            to_be_updated['visited'] = self._get_block_status(to_be_updated, True)
        return updated, to_be_updated

    def _queue_message(self, type, data):
        content = {}
        if type == 'BlockFound':
            content = {
                'agent_id': self.agent_id,
                'type': type,
                'data': {
                    'blocks': data  # data is dict of blocks in message format
                }
            }
        elif type == 'PickUp':
            content = {
                'agent_id': self.agent_id,
                'type': type,
                'data': {
                    'obj_id': data['id']  # data is block
                }
            }
        elif type == 'Dropped':
            content = {
                'agent_id': self.agent_id,
                'type': type,
                'data': {
                    'obj_id': data['block']['id'],  # data is block_info
                    'location': data['location']
                }
            }
        elif type == 'Hello':
            content = {
                'agent_id': self.agent_id,
                'type': type
            }

        # add nessage to queue
        self.message_queue.append((Message(content=content,
                                           from_id=self.agent_id,
                                           to_id=None)))

    def _parse_blocks(self, blocks):
        '''
        Parse the blocks from the agent's own discovery
        '''
        parsed_blocks = []
        for block in blocks:
            parsed_blocks.append({
                'id': block['obj_id'],
                'location': block['location'],
                'shape': block['visualization']['shape'] if 'shape' in block['visualization'].keys() else None,
                'colour': block['visualization']['colour'] if 'colour' in block['visualization'].keys() else None,
                'is_collectable': block['is_collectable'],
                'visited': self._get_block_status(block, False)
            })
        return parsed_blocks

    def _get_drop_zone(self, state):
        goal_blocks = state.get_with_property({'is_goal_block': True})

        # send to other agents about what we know of the drop_zones
        self._queue_message('BlockFound', self._blocks_to_message_format(goal_blocks))

        goal_blocks.sort(key=lambda d: d['location'][1], reverse=True)
        self.goal_blocks = [{
            'priority': i,
            'location': d['location'],
            'found_blocks': {},
            'plausible_blocks': {'colour': {}, 'shape': {}},
            'properties': {
                'shape': d['visualization']['shape'] if 'shape' in d['visualization'] else None,
                'colour': d['visualization']['colour'] if 'colour' in d['visualization'] else None
            },
            'filled': None,  # block which has been dropped on this spot
        } for i, d in enumerate(goal_blocks)]

    def _get_rooms(self, state):
        '''
        retrive information of the rooms from state. Only called once when MapState is initialized.
        '''
        self.rooms = {}
        room_names = state.get_all_room_names()
        for room in room_names:
            self.rooms[room] = {
                'room_id': room,
                'indoor_area': list(map(lambda x: x['location'], state.get_room_objects(room))),
                'doors': list(map(lambda x: {
                    'location': x['location'],
                    'status': x['is_open'],
                    # whether the door is open, if not, then the agent should first navi to the front of the door
                    'door_id': x['obj_id']
                }, state.get_room_doors(room))),
                'visited': False
            }

    def _get_goal_colour_set(self):
        '''
        return a set of wanted colours. if the goal block has been filled, then its colour is ignored.
        '''
        return set([x['properties']['colour'] for x in self.goal_blocks if
                    x['properties']['colour'] is not None and x['filled'] is None])

    def _get_goal_shape_set(self):
        '''
        return a set of wanted shapes, if the goal block has been filled, then its colour is ignored.
        '''
        return set([x['properties']['shape'] for x in self.goal_blocks if
                    x['properties']['shape'] is not None and x['filled'] is None])

    def _get_dist(self, loc1: tuple, loc2: tuple):
        '''
        Calculate for manhattan distance.
        '''
        return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

    #################################################################################################
    #                                         public methods                                        #
    #################################################################################################

    def contains_block(self, block, parsed_blocks: dict):
        for parsed_block in parsed_blocks:
            if parsed_block['id'] == block['obj_id']:
                return True
        return False

    def update_map(self, message: dict, state):
        '''
        update the internal state of the agent. The information could from the agent's
        own discovery or from messages. Message should be passed as dict.
        Depending on the type attribute of message, this function react differently.
        '''
        if state is not None:
            # update block info according to agent's own discovery
            blocks = state.get_with_property({'is_collectable': True})
            if blocks is not None:
                self.visible_blocks = self._parse_blocks(blocks)
                if self.agent_ability is None:
                    self.agent_ability = self._get_block_status(self.visible_blocks[0], True)
                parsed_blocks_to_send = self._update_block(self.visible_blocks)

                # match parsed with unparsed blocks, queue unparsed
                if parsed_blocks_to_send is not None:
                    to_send = []
                    for raw_block in blocks:
                        if self.contains_block(raw_block, parsed_blocks_to_send):
                            to_send.append(raw_block)
                    self._queue_message('BlockFound', self._blocks_to_message_format(to_send))
            else:
                self.visible_blocks = []

            #  update drop zone information if ghost block found
            ghost_blocks = state.get_with_property({'is_goal_block': True})
            self._update_ghost_block(ghost_blocks, False)
            self.agent_location = state.get_self()['location']

        if message is not None:
            if message['type'] == 'BlockFound':
                blocks = self._parse_blocks(message['data']['blocks'])
                self._update_block(blocks)
                for block in blocks:
                    if block['is_collectable']:
                        _, to_be_updated = self._update_collectable_blocks(self.received_blocks, block)
                        self.received_blocks[block['id']] = to_be_updated
                        if self.team_members[message['agent_id']]['ability'] is None:
                            self.team_members[message['agent_id']]['ability'] = self._get_block_status(block, True)

            elif message['type'] == 'PickUp':
                # print(self.agent_id, "-- received pickup message", message)
                block = self.blocks.get(message['data']['obj_id'])
                self.pop_block(block, queue=False)
                self.team_members[message['agent_id']]['carried_blocks'].append(block)

            elif message['type'] == 'Dropped':
                # print("handling message drop", message)
                drop_info = {
                    'block': {
                        'id': message['data']['obj_id']
                    },
                    'location': message['data']['location']
                }

                block = self.blocks.get(message['data']['obj_id'])

                self.drop_block(drop_info, queue=False)
                for block in self.team_members[message['agent_id']]['carried_blocks']:
                    if block['id'] == message['data']['obj_id']:
                        self.team_members[message['agent_id']]['carried_blocks'].remove(block)

    def get_message_queue(self):
        res = self.message_queue.copy()
        self.message_queue.clear()

        return res

    def get_unvisited_rooms(self):
        '''
        @return list of unvisited rooms
        '''
        unvisited_rooms = []
        for room in self.rooms.values():
            if room['visited']:
                continue
            unvisited_rooms.append(room)
        return unvisited_rooms

    def get_closest_unvisited_room(self, loc, traverse_order):
        '''
        @return name of the nearest unvisited room
        '''
        dist = []
        rooms = self.get_unvisited_rooms()
        for room in rooms:
            for door in room['doors']:
                dist.append([room['room_id'],
                             (abs(loc[traverse_order] - door['location'][traverse_order]),
                              matrx.utils.get_distance(loc, door['location']))])
        if len(dist) == 0:
            return None
        return min(dist, key=operator.itemgetter(1))[0]

    def get_candidate_blocks_shape(self):
        '''
        @return list of blocks which does not have colour information but have matching shape with one
            of the goal blocks. If the agent is not colour blind, then it may worth to go and confirm 
            the colour of these blocks. RESULT COUBLE BE EMPTY.
        '''
        res = []
        for block in self.blocks.values():
            if block['visited'] == 1 and block['colour'] in self._get_goal_colour_set():
                res.append(block)
        return res

    def get_candidate_blocks_colour(self):
        '''
        @return list of blocks which does not have shape information but have matching shape with one
            of the goal blocks. If the agent is not shape blind, then it may worth to go and confirm 
            the shape of these blocks. RESULT COULD BE EMPTY.
        '''
        res = []
        for block in self.blocks.values():
            if block['visited'] == 2 and block['shape'] in self._get_goal_shape_set():
                res.append(block)
        return res

    def get_matching_blocks(self):
        '''
        @return [{x, y, z}]
            x: drop order
            y: location of the corresponding drop spot
            z: block info

            could return empty list
        '''
        res = []
        blocks = self.blocks.values()
        # check if all goal blocks has been filled or none of them has been discovered
        for block in blocks:
            # if (block['visited'] & filtering_criteria) == 0:
            if block['visited'] != 3:
                continue
            for i, g_block in enumerate(self.goal_blocks):
                # if this goal has already been found a block, no need to check with it
                if bool(g_block['found_blocks']):
                    continue
                is_matching = g_block['properties']['colour'] is not None and \
                              block['colour'] == g_block['properties']['colour'] and \
                              g_block['properties']['shape'] is not None and \
                              block['shape'] == g_block['properties']['shape']
                if is_matching:
                    res.append([
                        i,  # priority(order)
                        g_block['location'],
                        block,
                        True if block['id'] in self.carried_blocks.keys() else False
                        # whether the block has been picked up
                    ])
        return res

    def get_mismatched_spots(self):
        '''
        @return the dicts of mismatched drop spots
        '''
        res = []
        for drop_spot in self.goal_blocks:
            if drop_spot['filled'] is None:
                return []
            drop_spot_block = self.blocks.get(drop_spot['filled'])
            if drop_spot['properties']['shape'] != drop_spot_block['shape'] or \
                    drop_spot['properties']['colour'] != drop_spot_block['colour']:
                res.append(drop_spot)
        return res

    def visit_room(self, room_id):
        '''
        update the visiting status of a room. Should be called by the agent when a room has been traversed.
        '''
        self.rooms[room_id]['visited'] = True

    def get_agent_location(self, agent_id=None):
        '''
        @return (x, y) the location of agent with id:agent_id(default to None, return own location)
        '''
        return self.agent_location

    def get_room(self, room_id):
        if room_id in self.rooms.keys():
            return self.rooms[room_id]
        else:
            return None

    def get_next_drop_zone(self):
        for dz in self.goal_blocks:
            #  if this goal has already been filled, then check the next one
            if dz['filled'] != None:
                continue
            return dz

    def filter_blocks_within_range(self, loc: tuple, blocks=None, rag=2):
        '''
        @param rag the range wrt which the blocks to be filtered
        @param loc the location of the center
        @return list of blocks if any blocks exists within that range or []
        '''
        if blocks is None:
            blocks = self.blocks
        res = []
        if rag <= 0:
            return res
        for block in blocks:
            if self._get_dist(loc, block[2]['location']) <= rag:
                res.append(block)
        return res

    def pop_block(self, block, queue=True):
        '''
        Remove a block from interal collection. Note, the block must be a SINGLE block.
        '''
        if isinstance(block, str):
            block = self.blocks.get(block)
        # add to goal block's found list
        for gb in self.goal_blocks:
            # if this goal block has already been assigned a block, then skip it. This ensures that if there are
            # multiple goals that have the same block, we won't assign the same block to two of them.
            if gb['filled'] is not None and gb['filled'] == block['id']:
                gb['filled'] = None
                break
            if bool(gb['found_blocks']):
                continue
            if gb['properties']['shape'] == block['shape'] and gb['properties']['colour'] == block['colour']:
                gb['found_blocks'][block['id']] = block
                # once we assign this block to a goal, we cannot assign it to any other ones
                break

        # if it called by ourselves, tell other people and save it into our blocks
        if queue:
            self._queue_message('PickUp', block)
            self.carried_blocks[block['id']] = block
        # otherwise it's a message from other people, so delete from our blocks
        self.blocks.pop(block['id'], None)

    def drop_block(self, drop_info: dict, queue=True):
        block_id = self.carried_blocks.pop(drop_info['block']['id'], None)
        if queue:
            self._queue_message('Dropped', drop_info)
        if block_id is not None:
            for drop_spot in self.goal_blocks:
                if drop_spot['location'] == drop_info['location']:
                    drop_spot['filled'] = drop_info['block']['id']
                    return
            # if the agent drop the block outside of the dropzone, then add the block back to collection
            self.blocks[block_id] = drop_info['block']

    def are_nearby_blocks_visited(self):
        if len(self.visible_blocks) == 0 or len(self.received_blocks) == 0:
            return False
        res = True
        for block in self.visible_blocks:
            received_block = self.received_blocks.pop(block['id'], None)
            if received_block is None:
                return False
            res = res and (received_block['visited'] == 3 or received_block['visited'] == self.agent_ability)
        return res

    def get_nearby_agent(self, state):
        res = []
        self_loc = self.get_agent_location()
        for team_mate in state.get_with_property({'isAgent': True}):
            if self._get_dist(self_loc, team_mate['location']) <= 2:
                res.append(team_mate['obj_id'])
        return list(map(lambda x: self.team_members[x], res))
