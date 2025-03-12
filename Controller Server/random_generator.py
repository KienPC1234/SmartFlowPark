import random
import string

class RandomGenerator:
    @staticmethod
    def generate_key(length=16):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    @staticmethod
    def generate_name(length=8):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))