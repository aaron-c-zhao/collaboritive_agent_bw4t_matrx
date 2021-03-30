from agents1.Team42Agent import Team42Agent
from agents1.human import Human
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics

"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""

if __name__ == "__main__":
    agents = [
        # {'name': 'agent1', 'botclass': RandomAgent, 'settings': {'slowdown': 1, 'colorblind': True}},
        # {'name':'agent2', 'botclass':RandomAgent, 'settings':{'slowdown':1, 'shapeblind':True}},
        # {'name': 'human1', 'botclass': Human, 'settings': {'slowdown': 1}},
        # {'name': 'human2', 'botclass': Human, 'settings': {'slowdown': 1, 'colorblind': True}},
        {'name': 'group42agent-normal', 'botclass': Team42Agent, 'settings': {'slowdown': 1}},
        {'name': 'group42agent-color_blind', 'botclass': Team42Agent,
         'settings': {'slowdown': 1, 'colorblind': True, 'shapeblind': False}},
        {'name': 'group42agent-shape_blind', 'botclass': Team42Agent,
         'settings': {'slowdown': 1, 'colorblind': False, 'shapeblind': True}},
        {'name': 'group42agent-totally_blind', 'botclass': Team42Agent,
         'settings': {'slowdown': 1, 'colorblind': True, 'shapeblind': True}}
    ]

    print("Started world...")
    world = BW4TWorld(agents).run()
    print("DONE!")
    print(Statistics(world.getLogger().getFileName()))
