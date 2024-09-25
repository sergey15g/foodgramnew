# utils.py
import random
import string


def generate_short_code(length=3):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
