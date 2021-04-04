import json

from matrx.messages.message import Message


def map_location(location):
    """
    Maps a location to a pair
    """
    x, y = location
    return (x, y)


def send_message(agent, m_type, m_data, receiver=None):
    """
    Sends a message between agents
    """
    if not m_data:
        return
    content = {'agent_id': agent.agent_id, 'type': m_type, 'data': m_data}
    msg = Message(content=content, from_id=agent.agent_name, to_id=receiver)
    agent.send_message(msg)


def broadcast_collect_blocks(agent):
    """
    Broadcasts knowledge about the shape/color of drop zones
    """
    data = {'blocks': [agent.state[obj] for obj in agent.state if 'Collect' in obj]}
    send_message(agent, 'BlockFound', data)


def broadcast_hello_message(agent):
    """
    Broadcasts a "hello" message to help identify with other agents in the cluster
    """
    send_message(agent, 'Hello', {})


def broadcast_knowledge(agent, blocks):
    """
    Broadcasts knowledge about shape/color/location of blocks
    """
    data = {'blocks': blocks}
    send_message(agent, 'BlockFound', data)


def picked_up(agent, block):
    send_message(agent, 'PickUp', {'obj_id': block['obj_id']})


def dropped(agent, block, location):
    send_message(agent, 'Dropped', {'location': location, 'obj_id': block['obj_id']})


def handle_messages(agent):
    """
    This function handles any message the agent receives.
    Checks the type of the message and performs an action accordingly
    """
    for msg in agent.received_messages:
        msg_object = msg
        if isinstance(msg, str):
            msg_object = json.loads(msg)
        msg_type = msg_object['type'] if 'type' in msg_object else None
        data = msg_object['data'] if 'data' in msg_object else None

        if msg_type == 'PickUp' and data:
            agent.assign_block(data['obj_id'])
        elif msg_type == 'Dropped' and data:
            agent.dropped[(data['location'][0], data['location'][1])] = data['obj_id']
        elif msg_type == 'BlockFound' and data:
            blocks = data['blocks']
            for block in blocks:
                if block['is_goal_block']:
                    agent.update_drops(block)
                else:
                    agent.update_knowledge(block)
    # Necessary to reset the list
    agent.received_messages = []
