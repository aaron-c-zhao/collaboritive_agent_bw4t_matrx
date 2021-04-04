from itertools import combinations, combinations_with_replacement

from agents1.Team42Agent import Team42Agent
from agents_cluster.Team13Agent import Team13Agent  # tested
from agents_cluster.Team33Agent import Team33Agent
from agents_cluster.team22agent import Team22Agent
from bw4t.BW4TWorld import BW4TWorld, DEFAULT_WORLDSETTINGS
from bw4t.statistics import Statistics

"""
This runs a single session. You have to log in on localhost:3000 and 
press the start button in god mode to start the session.
"""


def checkNoDuplicates(names: list):
    '''
    @raise ValueError if there is a duplicate in names list: 
    '''
    duplicates = [name for name in names if names.count(name) > 1]
    if len(duplicates) > 0:
        raise ValueError(f"Found duplicate agent names {duplicates}!")


if __name__ == "__main__":
    agent_settings = [
        {'slowdown': 1, 'shapeblind': True, 'colourblind': True},
        {'slowdown': 3, 'shapeblind': False, 'colourblind': False},
        {'slowdown': 1, 'shapeblind': False, 'colourblind': False},
        {'slowdown': 1, 'shapeblind': True, 'colourblind': False},
        {'slowdown': 1, 'shapeblind': False, 'colourblind': True},
    ]

    agents = [
        {'name': 'agent42', 'botclass': Team42Agent, 'settings': None},
        {'name': 'agent13', 'botclass': Team13Agent, 'settings': None},
        {'name': 'agent22', 'botclass': Team22Agent, 'settings': None},
        {'name': 'agent33', 'botclass': Team33Agent, 'settings': None},
    ]

    teamsize = 3

    # safety check: all names should be unique 
    # This is to avoid failures halfway the run.
    checkNoDuplicates(list(map(lambda agt: agt['name'], agents)))

    settings = DEFAULT_WORLDSETTINGS.copy()
    settings['matrx_paused'] = False
    settings['deadline'] = 500
    settings['tick_duration'] = 0
    settings['random_seed'] = 1

    res = []

    our_count = 0
    our_total = 0
    our_ticks = 0

    for i, team in enumerate(combinations(agents, teamsize)):
        print(f"Started with team permutation: {team}")
        successes = 0
        ticks = 0
        total = 0

        contains_our = ('agent42' in [t['name'] for t in team])

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
                continue  # not solvable

            our_total += contains_our

            print(f"-- Started session with sessioncombi {settingcombi}")
            total += 1

            # assign settings to agents
            for i, agent in enumerate(team):
                agent['settings'] = settingcombi[i]

            world = BW4TWorld(list(team), settings).run()
            stats = Statistics(world.getLogger().getFileName())
            if stats.isSucces() == 'True':
                successes += 1
                our_count += contains_our
                our_ticks += contains_our * int(stats.getLastTick())
                ticks += int(stats.getLastTick())

            print("---> results:", "success:", stats.isSucces(), "  ticks:", stats.getLastTick())

        print("=-=-=-=-=-=-=-=-=-=", "done with team permutation {team}", "succesrate:", successes / total, "avg ticks",
              ticks / total)

        data = {
            'agents': team,
            'success_rate': str(successes) + '/' + str(total),
            'avg_ticks': str(ticks / total),
        }
        res.append(data)

    print("DONE")
    print(res)
    print("our success: " + str(our_count) + '/' + str(our_total))
    print('our average tick: ' + str(our_ticks / our_count))

    # with open('tournament.txt', 'w') as outfile:
    #     json.dump(res, outfile)
