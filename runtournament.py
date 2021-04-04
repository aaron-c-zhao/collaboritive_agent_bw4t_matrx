import os
from itertools import combinations, combinations_with_replacement
from agents_cluster.Team13Agent import Team13Agent # tested
from agents_cluster.team22agent import Team22Agent
from agents_cluster.Team33Agent import Team33Agent

from bw4t.bw4tlogger import BW4TLogger
from bw4t.BW4TWorld import BW4TWorld, DEFAULT_WORLDSETTINGS
from bw4t.statistics import Statistics

from agents1.human import Human
from agents1.randomagent import RandomAgent
from agents1.Team42Agent import Team42Agent


"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""


def checkNoDuplicates(names:list):
    '''
    @raise ValueError if there is a duplicate in names list: 
    '''
    duplicates=[name for name in names if names.count(name) > 1]
    if len(duplicates) >0:
        raise ValueError(f"Found duplicate agent names {duplicates}!")

if __name__ == "__main__":
    agent_settings = [
        {'slowdown':1, 'shapeblind': True, 'colourblind': True},
        {'slowdown':3, 'shapeblind': False, 'colourblind': False},
        {'slowdown':1, 'shapeblind': False, 'colourblind': False},
        {'slowdown':1, 'shapeblind': True, 'colourblind': False},
        {'slowdown':1, 'shapeblind': False, 'colourblind': True},
    ]



    agents = [
        {'name':'agent1', 'botclass': Team42Agent, 'settings':None},
        {'name':'agent2', 'botclass': Team13Agent, 'settings':None},
        {'name':'agent3', 'botclass': Team22Agent, 'settings':None},
        {'name':'agent4', 'botclass': Team33Agent, 'settings':None},
        ]

    teamsize=3

    # safety check: all names should be unique 
    # This is to avoid failures halfway the run.
    checkNoDuplicates(list(map(lambda agt:agt['name'], agents)))

    settings = DEFAULT_WORLDSETTINGS.copy()
    settings['matrx_paused']=False
    settings['deadline']=400
    settings['tick_duration']=0
    
    res = []


    for i, team in enumerate(combinations(agents,teamsize)):
        print(f"Started with team permutation: {team}")
        successes = 0
        ticks = 0
        total = 0
        
        # for settingcombi in agent_settings_permutations:
        for settingcombi in combinations_with_replacement(agent_settings, teamsize):
            # check if there is at least 1 agent that can see colors and 1 that can see shapes
            color_visible = False
            shape_visible = False
            for setting in settingcombi:
                if not setting['shapeblind']:
                    shape_visible = True
                if not setting['colourblind']:
                    color_visible = True

            if not (color_visible and shape_visible):
                continue # not solvable

            print(f"-- Started session with sessioncombi {settingcombi}")
            total += 1

            # assign settings to agents
            for i, agent in enumerate(team):
                agent['settings'] = settingcombi[i]

            world=BW4TWorld(list(team),settings).run()
            stats = Statistics(world.getLogger().getFileName())
            if stats.isSucces():
                successes += 1
                ticks += int(stats.getLastTick())

            print("---> results:", "succes:", stats.isSucces(), "  ticks:", stats.getLastTick())

            
        print("=-=-=-=-=-=-=-=-=-=", "done with team permutation {team}", "succesrate:", successes / total, "avg ticks", ticks / total)

        data = {
            'agents': team,
            'succes_rate': successes / total,
            'avg_ticks': ticks / total,
        }
        res.append(data)

    print("DONE")
    print(data)
