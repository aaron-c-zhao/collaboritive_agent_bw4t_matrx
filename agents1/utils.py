def match_blocks(block1, block2):
    return block1['shape'] == block2['shape'] and block1['colour'] == block2['colour']


def distance_manhattan(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
