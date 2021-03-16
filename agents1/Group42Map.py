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
        self.blocks = [] # block = {'id', 'location', 'shape', 'color', 'is_candidate'}
        


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
        if message is not None and message['type'] is 'BlockFound':
            self._update_block(message['blocks'])

        
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
                to_be_updated['shape'] = block['visualization']['shape'] if block['visualization']['shape'] else None
                to_be_updated['color'] = block['visualization']['colour'] if block['visualization']['colour'] else None
                to_be_updated['visited'] = self._get_block_status(block)
            self.blocks.append(to_be_updated)
    def _is_block_exist(self, target:dict):
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
            'filled': False 
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
            
            

    


    
        
        
