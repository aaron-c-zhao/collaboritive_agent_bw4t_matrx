import operator

import matrx.utils
from matrx.messages import Message

class MapState:
    '''
    Useful information extracted from the world, organised
    in a way that is much easier to understand for the agent.
    Also, support the agent by providing handy utility functions.
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
        }

        '''
        self._get_drop_zone(state)
        self._get_rooms(state)
        self.blocks = {}
        self.carried_blocks = {}
        self.messageQueue = []
        self.agent_id = state.get_self()['obj_id']
        self.blocks_carried_by_agents = {}
        self.agent_locations = {}

        for agentId in state['World']['team_members']:
            self.blocks_carried_by_agents[agentId] = []

    def _update_ghost_block(self, ghost_blocks, is_parsed):
        if ghost_blocks is not None:
            ghost_blocks_parsed = ghost_blocks
            if not is_parsed:
                ghost_blocks_parsed = self._parse_blocks(ghost_blocks)
            for ghost_block in ghost_blocks_parsed:
                for drop_spot in self.drop_zone:
                    if ghost_block['location'] == drop_spot['location']:
                        if ghost_block['colour'] is not None:
                            drop_spot['properties']['colour'] = ghost_block['colour']
                        if ghost_block['shape'] is not None:
                            drop_spot['properties']['shape'] = ghost_block['shape']

    def _extract_room(self, room):
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
        visited = 0
        has_shape = False
        has_color = False
        if is_parsed:
            has_shape = block['shape'] is not None
            has_color = block['colour'] is not None
        else:
            has_shape = True if 'shape' in block['visualization'].keys() else False
            has_color = True if 'colour' in block['visualization'].keys() else False
        if has_shape:
            visited |= 1
        if has_color:
            visited |= 1 << 1
        return visited

    def _update_block(self, blocks, queue=True):
        '''
        assert (blocks) are parsed
        '''
        res = []
        for block in blocks:
            to_be_updated = self.blocks.pop(block['id'], None)  # check if the block is already in the collection
            updated = False
            if to_be_updated is None:  # add new entry into the collection
                to_be_updated = block
                updated = True
            else:  # update shape, colour and status of the block if the block is in the collection
                if to_be_updated['location'] != block['location'] or to_be_updated['shape'] != block['shape'] or \
                        to_be_updated['colour'] != block['colour']:
                    updated = True
                to_be_updated['location'] = block['location']
                to_be_updated['shape'] = block['shape'] if block['shape'] is not None else None
                to_be_updated['colour'] = block['colour'] if block['colour'] is not None else None
                to_be_updated['visited'] = self._get_block_status(block, True)

            # if the block discovered is in the drop zone then update the drop_zone
            for drop_spot in self.drop_zone:
                if to_be_updated['location'] == drop_spot['location']:
                    if to_be_updated['is_collectable']:
                        drop_spot['filled'] = to_be_updated
                    else:
                        self._update_ghost_block([to_be_updated], True)
            self.blocks[block['id']] = to_be_updated  # only update the blocks when the block is collectable
            if updated is True:
                res.append(to_be_updated)  # return list of updated blocks

        # queue a message with all updated blocks
        if len(res) > 0 and queue:        
            self._queue_message('BlockFound', res)

    def _queue_message(self, type, data):
        content = {}

        if type == 'BlockFound':
            content = {
                        'agentId': self.agent_id,
                        'type': type,
                        'blocks': data
                        }
        elif type == 'PickUp':
            content = {
                        'agentId': self.agent_id,
                        'type': type,
                        'block': data
                        }
        elif type == 'Dropped':
            content = {
                        'agentId': self.agent_id,
                        'type': type,
                        'drop_info': data
                        }

        # add nessage to queue
        self.messageQueue.append((Message(content=content,
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
                'room': self._extract_room(block['name']),
                'shape': block['visualization']['shape'] if 'shape' in block['visualization'].keys() else None,
                'colour': block['visualization']['colour'] if 'colour' in block['visualization'].keys() else None,
                'is_collectable': block['is_collectable'],
                'visited': self._get_block_status(block, False)
            })
        return parsed_blocks

    def _get_drop_zone(self, state):
        drop_zone_objs = state.get_with_property({'is_drop_zone': True})
        self.drop_zone = list(map(lambda d: {
            'location': d['location'],
            'properties': {
                'shape': None,
                'colour': None
            },
            'filled': None  # block which has been dropped on this spot 
        }, drop_zone_objs))
        self.drop_zone.reverse()

    def _get_rooms(self, state):
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
        return set([x['properties']['colour'] for x in self.drop_zone if
                    x['properties']['colour'] is not None and x['filled'] is None])

    def _get_goal_shape_set(self):
        '''
        return a set of wanted shapes, if the goal block has been filled, then its colour is ignored.
        '''
        return set([x['properties']['shape'] for x in self.drop_zone if
                    x['properties']['shape'] is not None and x['filled'] is None])

    def _get_dist(self, loc1: tuple, loc2: tuple):
        return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

    #################################################################################################
    #                                         public methods                                        #
    #################################################################################################

    def update_map(self, message: dict, state):
        '''
        update the internal state of the agent. The information could from the agent's
        own discovery or from messages. Message should be passed as dict.
        Depending on the type attribute of message, this function react differently.
        '''
        # update block info according to agent's own discovery
        blocks = state.get_with_property({'is_collectable': True})
        if blocks is not None:
            self.visible_blocks = self._parse_blocks(blocks)
            self._update_block(self.visible_blocks)

        # update drop zone information if ghost block found
        ghost_blocks = state.get_with_property({'is_goal_block': True})
        self._update_ghost_block(ghost_blocks, False)

        self.agent_locations['self'] = state.get_self()['location']
        # TODO update other agents position based on messaging and not only on what we see
        agents = state.get_agents()
        for agent in agents:
            self.agent_locations[agent['obj_id']] = agent['location']

        if message is not None:
            if message['type'] == 'BlockFound':
                self._update_block(message['blocks'], queue=False)
            elif message['type'] == 'PickUp':
                self.pop_block(message['block'], queue=False)

                # not sure if this is the way to do this
                carried_blocks = self.blocks_carried_by_agents[message['agentId']]
                carried_blocks.append(message['block'])
                self.blocks_carried_by_agents[message['agentId']] = carried_blocks
                # print("carried blocks after pickup:", self.blocks_carried_by_agents)

            elif message['type'] == 'Dropped':
                self.drop_block(message['drop_info'], queue=False)

                carried_blocks = self.blocks_carried_by_agents[message['agentId']]
                carried_blocks.remove(message['drop_info']['block'])
                self.blocks_carried_by_agents[message['agentId']] = carried_blocks
                # print("carried blocks after drop:", self.blocks_carried_by_agents)

    def get_message_queue(self):
        res = self.messageQueue.copy()
        self.messageQueue.clear()
        
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

    def get_closest_unvisited_room(self, loc):
        '''
        @return name of the nearest unvisited room
        '''
        dist = []
        rooms = self.get_unvisited_rooms()
        for room in rooms:
            # if room['visited']:
            #     continue
            for door in room['doors']:
                dist.append([room['room_id'], (abs(loc[2]-door['location'][2]), matrx.utils.get_distance(loc, door['location']))])
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

    def get_matching_blocks(self, blocks=None):
        '''
        @return [{x, y, z}]
            x: drop order
            y: location of the corresponding drop spot
            z: block info

            could return empty list
        '''
        res = []
        if blocks is None:
            blocks = self.blocks.values()
        # check if all goal blocks has been filled or none of them has been discovered
        for block in blocks:
            if block['visited'] != 3:
                continue
            for i, g_block in enumerate(self.drop_zone):
                if g_block['properties']['shape'] is not None and g_block['properties']['colour'] is not None:
                    if block['colour'] == g_block['properties']['colour'] \
                            and block['shape'] == g_block['properties']['shape']:
                        res.append([
                            i,
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
        for drop_spot in self.drop_zone:
            if drop_spot['properties']['shape'] != drop_spot['filled']['shape'] or \
                    drop_spot['properties']['colour'] != drop_spot['filled']['colour']:
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
        if agent_id == None:
            return self.agent_locations['self']
        else:
            return self.agent_locations[agent_id] if agent_id in self.agent_locations else None

    def get_room(self, room_id):
        if room_id in self.rooms.keys():
            return self.rooms[room_id]
        else:
            return None

    def filter_blocks_within_range(self, rag, loc: tuple):
        '''
        @param rag the range wrt which the blocks to be filtered
        @param loc the location of the center
        @return list of blocks if any blocks exists within that range or []
        '''
        res = []
        if rag <= 0:
            return res
        for block in self.blocks.values():
            if self._get_dist(loc, block['location']) <= rag:
                res.append(block)
        return res

    def pop_block(self, block, queue=True):
        '''
        Remove a block from interal collection. Note, the block must be a SINGLE block.
        '''
        if isinstance(block, dict):
            if queue:
                self._queue_message('PickUp', block)
            self.blocks.pop(block['id'], None)
            self.carried_blocks[block['id']] = None
            return
        if isinstance(block, str):
            if queue:
                self._queue_message('PickUp', self.blocks.get(block))
            self.blocks.pop(block, None)
            self.carried_blocks[block] = None

    def get_matching_blocks_within_range(self, loc: tuple, rag=2):
        blocks = self.filter_blocks_within_range(rag, loc)
        if len(blocks) > 0:
            return self.get_matching_blocks(blocks)
        return []
    
    def drop_block(self, drop_info:dict, queue=True):
        block_id = self.carried_blocks.pop(drop_info['block']['id'], None)
        if queue:
            self._queue_message('Dropped', drop_info)
        if block_id is not None: 
            for drop_spot in self.drop_zone:
                if drop_spot['location'] == drop_info['location']:
                    drop_spot['filled'] = drop_info['block']
                    return
            self.blocks[block_id] = drop_info['block']  # if the agent drop the block outside of the dropzone, then add the block back to collection
