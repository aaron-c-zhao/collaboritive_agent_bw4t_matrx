from matrx.messages import Message
import matrx.utils
import numpy as np


class Map:
    '''
    Useful information extracted from the world, organised
    in a way that is much easier to understand for the agent.
    Also, support the agent by providing handy utility functions.
    '''
    def __init__(self, state):
        self._get_drop_zone(state)
        self._get_rooms(state)
        '''
        block = {
            'id' : (string)unique id of the block. Can be used to distinguish different blocks.
            'location': (x, y) location of the block
            'room': room_x room name in where the block resides
            'shape': 0|1|2 shape of the block(could be None)
            'colour': (string) colour of the block(could be None)
            'visited': The block will be marked as visited(3) when both the shape info and the colour
                info have been discovered. Otherwise, this attribute has value 1 for missing shape info,
                and 2 for missing colour info.
        }

        '''
        self.blocks = [] 
        

    def update_map(self, message:dict, state):
        '''
        update the internal state of the agent. The information could from the agent's
        own discovery or from messages. Message should be passed as dict.
        Depending on the type attribute of message, this function react differently.
        '''
        # update block info according to agent's own discovery
        blocks = state.get_with_property({'is_collectable': True})
        if blocks is not None: 
            parsed_blocks = []

            

            for block in blocks:
                parsed_blocks.append(self._parse_block(block))
                return self._update_block(parsed_blocks)
            
        if message is not None:
            if message['type'] == 'BlockFound':
                self._update_block(message['blocks'])
            elif message['type'] == 'PickUp':
                self._pop_block(message['block'])
            elif message['type'] == 'Dropped':
                self._drop_block(message['drop_info'])

        return None

    def _is_block_exist(self, target:dict):
        '''
        @return if the block has been found before, then return the saved instance. Otherwise, return None.
        '''
        for block in self.blocks:
            if block['id'] == target['id']:
                return block
        return None




    def _drop_block(self, drop_info:dict):
        for drop_spot in self.drop_zone:
            if drop_spot['location'] == drop_info['location']:
                drop_spot['filled'] = drop_info['block']
                return
        self.blocks.append(drop_info['block']) # if the agent drop the block outside of the dropzone, then add the block back to collection
        
        

    def _pop_block(self, block:dict):
        '''
        Remove a block from interal collection. Note, the block must be a SINGLE block.
        '''
        for cur in self.blocks:
            if cur['id'] == block['obj_id']:
                self.blocks.remove(cur)
        

        
    def _extract_room(self, room):
        if isinstance(room, str):
            words = room.split()
            return words[len(words) - 1]
        else: 
            return None

    def _get_block_status(self, block):
        '''
        missing shape = 1
        missing colour = 2
        visited = 3
        '''
        visited = 0
        if block['visualization']['shape'] or block['visualization']['shape'] is None:
            visited |= 1 << 1
        if block['visualization']['colour'] or block['visualization']['colour'] is None:
            visited |= 1 
        return visited

    def _get_block_status_parsed(self, block): # todo: improve this if in the mood
        '''
        missing shape = 1
        missing colour = 2
        visited = 3
        '''
        visited = 0
        if block['shape'] or block['shape'] is None:
            visited |= 1 << 1
        if block['colour'] or block['colour'] is None:
            visited |= 1 
        return visited
        
    def _update_block(self, blocks):
        res = []
        for block in blocks:
            to_be_updated = self._is_block_exist(block) # check if the block is already in the collection
            updated = False
            if to_be_updated is None: # add new entry into the collection
                to_be_updated = block
                updated = True
            else: # update shape, colour and status of the block if the block is in the collection
                self.blocks.remove(to_be_updated)
                if to_be_updated['location'] != block['location'] or to_be_updated['shape'] != block['shape'] or to_be_updated['colour'] != block['colour']:
                    updated = True
                to_be_updated['location'] = block['location']
                to_be_updated['shape'] = block['shape'] if block['shape'] is not None else None
                to_be_updated['colour'] = block['colour'] if block['colour'] else None
                to_be_updated['visited'] = self._get_block_status_parsed(block)
            # if the block discovered is in the drop zone then update the drop_zone

            # if block['is_collectable']: now implemented in update_map, check if thats ok
            for drop_spot in self.drop_zone:
                if to_be_updated['location'] == drop_spot['location']:
                    drop_spot['filled'] = to_be_updated

            self.blocks.append(to_be_updated) # only update the blocks when the block is collectable
            if updated is True:
                res.append(to_be_updated) # return list of updated blocks

            # TODO reimplement
            # if block['is_goal_block']: # for ghost block which can not be collected, so only update the drop zone
            #     for drop_spot in self.drop_zone:
            #         if to_be_updated['location'] == drop_spot['location']:
            #             if to_be_updated['colour']:
            #                 drop_spot['colour'] = to_be_updated['colour']
            #             if to_be_updated['shape']:
            #                 drop_spot['shape'] = to_be_updated['shape'] 
            
        return res

    def _parse_block(self, block):
        res = {
            'id': block['obj_id'],
            'location': block['location'],
            'room': self._extract_room(block['name']),
            'shape': block['visualization']['shape'] if block['visualization']['shape'] is not None else None,
            'colour': block['visualization']['colour'] if block['visualization']['colour'] else None,
            'visited': self._get_block_status(block)
        }
        return res

    def _is_block_exist(self, target:dict):
        '''
        @return if the block has been found before, then return the saved instance. Otherwise, return None.
        '''
        for block in self.blocks:
            if block['id'] == target['id']:
                return block
        return None
        

    def _get_drop_zone(self, state):
        drop_zone_objs = state.get_with_property({'is_drop_zone': True})
        self.drop_zone = list(map(lambda d: {
            'location': d['location'], 
            'properties': {
                'shape': None, 
                'colour': None
                },
            'filled': None  # whether it has been filled with correct block
            }, drop_zone_objs)) 
        self.drop_zone.reverse()


    def _get_rooms(self, state):
        self.rooms = []
        room_names = state.get_all_room_names()
        for room in room_names:
            self.rooms.append({
                'room_name': room,
                'indoor_area': list(map(lambda x: x['location'], state.get_room_objects(room))),
                'doors': list(map(lambda x: {
                    'location': x['location'],  
                    'status': x['is_open']  # whether the door is open, if not, then the agent should first navi to the front of the door
                    }, state.get_room_doors(room))),
                'visited': False
            })

    def _get_goal_colour_set(self):
        '''
        return a set of wanted colours. if the goal block has been filled, then its colour is ignored.
        '''
        return set([x['properties']['colour'] for x in self.blocks if x['properties']['colour'] and x['filled'] is not None])

    def _get_goal_shape_set(self):
        '''
        return a set of wanted shapes, if the goal block has been filled, then its colour is ignored.
        '''
        return set([x['properties']['shape'] for x in self.blocks if x['properties']['shape'] and x['filled'] is not None])

    def get_unvisited_rooms(self):
        '''
        @return list of unvisited rooms
        '''
        unvisited_rooms = []
        for room in self.rooms:
            if room['visited']:
                continue
            unvisited_rooms.append(room)
        return unvisited_rooms
    

    def get_closest_unvisited_room(self, state, loc):
        '''
        @return name of the nearest unvisited room
        '''
        dist = []
        rooms = self.get_unvisited_rooms()
        for room in rooms:
            if room['visited']:
                continue
            for door in room['doors']:
                dist.append([room['room_name'], matrx.utils.get_distance(loc, door['location'])])
        if len(dist) == 0:
            return None
        return min(dist, key = lambda x: x[1])[0]
            
    def get_candidate_blocks_shape(self):
        '''
        @return list of blocks which does not have colour information but have matching shape with one
            of the goal blocks. If the agent is not colour blind, then it may worth to go and confirm 
            the colour of these blocks. RESULT COUBLE BE EMPTY.
        '''
        res = []
        for block in self.blocks:
            if block['visited'] == 2 and block['colour'] in self._get_goal_colour_set():
                res.append(block)
        return res
                

    def get_candidate_blocks_colour(self):
        '''
        @return list of blocks which does not have shape information but have matching shape with one
            of the goal blocks. If the agent is not shape blind, then it may worth to go and confirm 
            the shape of these blocks. RESULT COULD BE EMPTY.
        '''
        res = []
        for block in self.blocks:
            if block['visited'] == 2 and block['shape'] in self._get_goal_shape_set():
                res.append(block)
        return res

    def get_matching_blocks(self):
        '''
        @return [[x, y, z]]
            x: drop order
            y: location of the corresponding drop spot
            z: block info
            could return empty list
        '''
        res = []
        # check if all goal blocks has been filled or none of them has been discovered
        if len(self.get_candidate_blocks_colour()) > 0 and len(self.get_candidate_blocks_shape) > 0:  
            for block in self.blocks:
                for i, g_block in enumerate(self.drop_zone):
                    if g_block['properties']['shape'] and g_block['properties']['colour']:
                        if block['visited'] and block['colour'] == g_block['properties']['colour'] \
                            and block['shape'] == g_block['properties']['shape']:
                            res.append([i, g_block['location'], block])
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

    def visit_room(self, room_name):
        '''
        update the visiting status of a room. Should be called by the agent when a room has been traversed.
        '''
        for room in self.rooms:
            if room['name'] == room_name:
                room['visited'] = True
