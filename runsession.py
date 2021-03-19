from agents1.Group42Agent import Group42Agent
from agents1.human import Human
from agents1.randomagent import RandomAgent
from bw4t.BW4TWorld import BW4TWorld
from bw4t.statistics import Statistics

"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""

if __name__ == "__main__":
    agents = [
        {'name': 'agent1', 'botclass': RandomAgent, 'settings': {'slowdown': 1, 'colorblind': True}},
        # {'name':'agent2', 'botclass':RandomAgent, 'settings':{'slowdown':1, 'shapeblind':True}},
        {'name':'human1', 'botclass':Human, 'settings':{'slowdown':1}},
        # {'name': 'human2', 'botclass': Human, 'settings': {'slowdown': 1}},
        {'name': 'group42agent', 'botclass': Group42Agent, 'settings': {'slowdown': 1}}
    ]

    print("Started world...")
    world = BW4TWorld(agents).run()
    print("DONE!")
    print(Statistics(world.getLogger().getFileName()))
