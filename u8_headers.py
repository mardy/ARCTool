from header import BaseHeader


class U8ArchiveHeader(BaseHeader):
    _structformat = ">III16x"

    def __init__(self):
        BaseHeader.__init__(self)

        self.rootnode_offset = 0  # offset to root_node, always 0x20
        self.header_size = 0     # size of header from root_node to end of string table
        self.data_offset = 0     # offset to data: rootnode_offset + header_size aligned to 0x40
        # 16 bytes zeros

    def unpack(self, buf):
        (self.rootnode_offset,
         self.header_size,
         self.data_offset) = self._s.unpack_from(buf)


class U8Node(BaseHeader):
    _structformat = ">HHII"

    def __init__(self):
        BaseHeader.__init__(self)

        self.type = 0  # really u8, normal files = 0x0000, directories = 0x0100
        self.name_offset = 0     # really 'u24'
        self.data_offset = 0
        self.fsize = 0  # files: filesize, dirs: last included file with rootnode as 1

    def unpack(self, buf):
        s = self
        (s.type,
         s.name_offset,
         s.data_offset,
         s.fsize) = s._s.unpack_from(buf)


class U8Globals:
    pass
