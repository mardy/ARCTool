import struct


class U8ArchiveHeader:
    _structformat = ">III16x"

    def __init__(self):
        self.rootnode_offset = 0  # offset to root_node, always 0x20
        self.header_size = 0     # size of header from root_node to end of string table
        self.data_offset = 0     # offset to data: rootnode_offset + header_size aligned to 0x40
        # 16 bytes zeros

        self._s = struct.Struct(self._structformat)

    def unpack(self, buf):
        (self.rootnode_offset,
         self.header_size,
         self.data_offset) = self._s.unpack_from(buf)

    def size(self):
        return self._s.size


class U8Node:
    _structformat = ">HHII"

    def __init__(self):
        self.type = 0  # really u8, normal files = 0x0000, directories = 0x0100
        self.name_offset = 0     # really 'u24'
        self.data_offset = 0
        self.fsize = 0  # files: filesize, dirs: last included file with rootnode as 1

        self._s = struct.Struct(self._structformat)

    def unpack(self, buf):
        s = self
        (s.type,
         s.name_offset,
         s.data_offset,
         s.fsize) = s._s.unpack_from(buf)

    def size(self):
        return self._s.size


class U8Globals:
    pass
