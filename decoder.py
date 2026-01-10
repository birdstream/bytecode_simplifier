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
        extended_arg = 0
        size = 0

        while opcode == dis.opmap['EXTENDED_ARG']:
            if offset + 2 >= len(self.insBytes):
                return Instruction(opcode, 0, size + 3)

            ext_arg = (self.insBytes[offset + 2] << 8) | self.insBytes[offset + 1]
            extended_arg = (extended_arg << 16) | ext_arg
            offset += 3
            size += 3

            if offset >= len(self.insBytes):
                return Instruction(dis.opmap['EXTENDED_ARG'], 0, size)

            opcode = self.insBytes[offset]

        if opcode < dis.HAVE_ARGUMENT:
            return Instruction(opcode, None, size + 1)

        if opcode >= dis.HAVE_ARGUMENT:
            if offset + 2 >= len(self.insBytes):
                return Instruction(opcode, 0, size + 3)

            arg = (self.insBytes[offset + 2] << 8) | self.insBytes[offset + 1]
            if extended_arg:
                arg = (extended_arg << 16) | arg
            return Instruction(opcode, arg, size + 3)
