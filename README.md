Group42 Collaborative Agents

[IA table](https://docs.google.com/spreadsheets/d/1jJ9YaJEvTy4c8VdAFFtzT1wfiKodmjdXUweT3ltVV0A/edit?usp=sharing)



## Message Definition 

Here only define the most critical attributes. The message could also contain attributes like 'from_id', etc. 

* BlockFound

  ```python
  {
       'type': "BlockFound",
       'blocks': [{
            'is_goal_block': False, 
            'is_collectable': True, 
            'obj_id': 'Block_in_room_2_318', 
            'location': (20, 5), 
            'visualization': {'size': 0.5, 'shape': 1, 'colour': '#0dff00', 'depth': 80, 'opacity': 1.0}
       }]
  }
  ```

* Pickup

  ```python
  {
      'type': 'PickUp',
      'block': {
          'id': 'Block_in_room_2_318' # only id is required here, but the message could contain other informations
      }
  }
  ```

* Dropped

  ```python
  {
      'type': 'Dropped',
      'drop_info': {
          'location': (x, y), # where the block is dropped
          'block': {
              'id': "Block_in_room_2_318", # unique id that can identify individual blocks
              'location': (x, y),
              'room': room_name, # see rooms above. Where the blocks resides
              'shape': 0 - 2,
              'color': "#ffffff",
            'visited:' 1 - 3 # 1 only shape, 2 only color, 3 has both shape & color 
          }
      }
  }
  ```
  
  




## API of class Map

### Attributes
* **drop_zone**: list of dicts  
```python
[
    {
        'lcoation': (x, y),
        'properties':{
            'shape': 0 - 2 # required shape at the spot
            'color': "#ffffff" # required color at the spot
        },
        'filled': Block # see blocks
	}
]
```

* rooms: list of dicts

```python
[
    {
        'room_name': "room_x",
        'indoor_area': [(x, y)..]
        'doors':[
            {
                'location':(x, y),
                'status': True/False # is the door open
            }
        ],
        'visited': True/False # has this room been traversed
      
    }
]
```

* blocks

```python
[
    {
        'id': "Block_in_room_2_318", # unique id that can identify individual blocks
        'location': (x, y),
        'room': room_name, # see rooms above. Where the blocks resides
        'shape': 0 - 2,
        'color': "#ffffff",
        'visited:' 1 - 3 # 1 only shape, 2 only color, 3 has both shape & color
    }
]
```

## Public Methods

**NOTE**: please follow the convention that prefix the "private" method with a single '_', since python does not officially support private methods.

* **update_map(self, message:dict, state)**

  this method should be called in *filter_bw4t_observations* method. It will update the internal state of the map

* **get_unvisited_rooms(self)**

  return a list of unvisited rooms. Could be used to determine the next traverse target

* **get_closest_unvisited_rooms(self)**

  Get the closest unvisited room. **NOTE**: this method could return *None* when all rooms have been visited. So always check the returned result.

* **get_candidate_blocks_shape(self)**

  return a list of blocks which has only the shape information, and its shape matches with one of the goal blocks. Could be used by shape blind agent or normal agent to decide next traverse target.

* **get_candidate_blocks_color(self)**

  return a list of blocks which has only the color information, and its color matches with one of the goal blocks. Could be used by color blind agent or normal agent to decide next traverse target.

* **get_matching_blocks(self)**

  return a list of available blocks which has matching shape and color with one of the goal blocks. Also, the return list includes the location and drop order of the corresponding drop spot.

* **get_mismatched_spots(self)**

  return a list of mismatched drop spots. Could be used to restore the order of delivery.

* **visit_room(self)**

  bookkeeping method. should be called whenever the agent has traversed a room to prevent repeat traversing.

  