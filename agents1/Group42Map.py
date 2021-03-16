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
            'color': (string) color of the block(could be None)
            'visited': The block will be marked as visited(3) when both the shape info and the color
                info have been discovered. Otherwise, this attribute has value 1 for missing shape info,
                and 2 for missing color info.
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
            self._update_block(blocks)
        if message is not None:
            if message['type'] == 'BlockFound':
                self._update_block(message['blocks'])
            elif message['type'] == 'PickUp':
                self._pop_block(message['block'])
            elif message['type'] == 'Dropped':
                self._drop_block(message['drop_info'])


    def _drop_block(self, drop_info:dict):
        for drop_spot in self.drop_zone:
            if drop_spot['location'] == drop_info['location']:
                drop_spot['filled'] = drop_info['block']
        

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
        missing color = 2
        visited = 3
        '''
        visited = 0
        if block['visualization']['shape'] or block['visualization']['shape'] is None:
            visited |= 1 << 1
        if block['visualization']['colour'] or block['visualization']['colour'] is None:
            visited |= 1 
        return visited
        
    def _update_block(self, blocks):
        for block in blocks:
            to_be_updated = self._is_block_exist(block) # check if the block is already in the collection
            if to_be_updated is None: # add new entry into the collection
                to_be_updated = {
                    'id': block['obj_id'],
                    'location': block['location'],
                    'room': self._extract_room(block['name']),
                    'shape': block['visualization']['shape'] if block['visualization']['shape'] else None,
                    'color': block['visualization']['colour'] if block['visualization']['colour'] else None,
                    'visited': self._get_block_status(block)
                    }
            else: # update shape, color and status of the block if the block is in the collection
                self.blocks.remove(to_be_updated)
                to_be_updated['location'] = block['location']
                to_be_updated['shape'] = block['visualization']['shape'] if block['visualization']['shape'] else None
                to_be_updated['color'] = block['visualization']['colour'] if block['visualization']['colour'] else None
                to_be_updated['visited'] = self._get_block_status(block)
            # if the block discovered is in the drop zone then update the drop_zone
            for drop_zone_spot in self.drop_zone:
                if to_be_updated['location'] == drop_zone_spot['location']:
                    drop_zone_spot['filled'] = to_be_updated
            self.blocks.append(to_be_updated)


    def _is_block_exist(self, target:dict):
        '''
        @return if the block has been found before, then return the saved instance. Otherwise, return None.
        '''
        for block in self.blocks:
            if block['id'] == target['obj_id']:
                return block
        return None
        

    def _get_drop_zone(self, state):
        drop_zone_objs = state.get_with_property({'is_drop_zone': True})
        self.drop_zone = list(map(lambda d: {
            'location': d['location'], 
            'properties': {
                'shape': None, 
                'color': None
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

    def _get_goal_color_set(self):
        '''
        return a set of wanted colors. if the goal block has been filled, then its color is ignored.
        '''
        return set([x['properties']['color'] for x in self.blocks if x['properties']['color'] and x['filled'] is not None])

    def _get_goal_shape_set(self):
        '''
        return a set of wanted shapes, if the goal block has been filled, then its color is ignored.
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
            for door in room['doors']:
                dist.append([room['room_name'], matrx.utils.get_distance(loc, door['location'])])
        return min(dist, key = lambda x: x[1])[0]
            
    def get_candidate_blocks_shape(self):
        '''
        @return list of blocks which does not have color information but have matching shape with one
            of the goal blocks. If the agent is not color blind, then it may worth to go and confirm 
            the color of these blocks. RESULT COUBLE BE EMPTY.
        '''
        res = []
        for block in self.blocks:
            if block['visited'] == 2 and block['color'] in self._get_goal_color_set():
                res.append(block)
        return res
                

    def get_candidate_blocks_color(self):
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
        if len(self.get_candidate_blocks_color()) > 0 and len(self.get_candidate_blocks_shape) > 0:  
            for block in self.blocks:
                for i, g_block in enumerate(self.drop_zone):
                    if g_block['properties']['shape'] and g_block['properties']['color']:
                        if block['visited'] and block['color'] == g_block['properties']['color'] \
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
                drop_spot['properties']['color'] != drop_spot['filled']['color']:
                res.append(drop_spot)
        return res

    def visit_room(self, room_name):
        '''
        update the visiting status of a room. Should be called by the agent when a room has been traversed.
        '''
        for room in self.rooms:
            if room['name'] == room_name:
                room['visited'] = True
        
    
            

    


    
        
        
