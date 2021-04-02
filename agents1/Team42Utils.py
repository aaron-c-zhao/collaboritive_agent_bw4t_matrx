def match_blocks(block1, block2):
    return block1['shape'] == block2['shape'] and block1['colour'] == block2['colour']


def distance_manhattan(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def reduce(function, iterable, initializer=None):
    it = iter(iterable)
    if initializer is None:
        value = next(it)
    else:
        value = initializer
    for element in it:
        value = function(value, element)
    return value

def more_than(block1, block2):
    if block2['shape'] is None and block1['shape'] is not None:
        return True
    if block2['colour'] is None and block1['colour'] is not None:
        return True
    return False