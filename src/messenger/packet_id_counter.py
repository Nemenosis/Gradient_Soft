import random


# OopCompanion:suppressRename


class PacketId:
    def __init__(self):
        self.value = random.randint(0, 65535)

    def check_value(self):
        if self.value > 65535:
            self.value = random.randint(0, 65535)

    def __iadd__(self, other):
        if isinstance(other, int):
            self.value += other
        return self

    def __repr__(self):
        return self.get_hex()

    def get_hex(self):
        self.check_value()
        return hex(self.value)[2:].upper().rjust(4, "0")






