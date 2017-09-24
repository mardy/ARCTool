import struct


class BaseHeader:

    def __init__(self):
        try:
            self._s = struct.Struct(self._structformat)
        except AttributeError:
            print 'Struct format not set'

    def size(self):
        return self._s.size
