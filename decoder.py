import dis

from instruction import Instruction


class Decoder:
    """
    Class to decode raw bytes into instruction.
    """

    def __init__(self, insBytes):
        self.insBytes = insBytes

    def decode_at(self, offset):
        assert offset < len(self.insBytes)

        opcode = self.insBytes[offset]

        # Invalid instruction
        if opcode not in dis.opmap.values():
            return Instruction(-1, None, 1)

        if opcode < dis.HAVE_ARGUMENT:
            return Instruction(opcode, None, 1)

        if opcode >= dis.HAVE_ARGUMENT:
            if opcode == dis.opmap.get('EXTENDED_ARG'):
                raise Exception('EXTENDED_ARG not yet implemented')
            arg = (self.insBytes[offset + 2] << 8) | self.insBytes[offset + 1]
            return Instruction(opcode, arg, 3)
