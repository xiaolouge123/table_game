import uuid


def get_random():
    return str(uuid.uuid4())[:8]
