import struct


class RARCHeader:
    _structformat = ">IIIIIIIIIIIIIHHI"

    def __init__(self):
        self.filesize = 0
        self.headersize = 0
        self.dataStartOffset = 0  # offset to data, relative to end of header

        self.filelength = 0
        self.unknown3 = 0
        self.filelength2 = 0
        self.unknown5 = 0

        # begin info block
        self.numNodes = 0
        self.nodeEntriesOffset = 0  # offset to node, relative to info block
        self.numEntries = 0
        self.fileEntriesOffset = 0

        self.stringTableLength = 0
        self.stringTableOffset = 0  # where is the string table stored? add 0x20

        self.numFiles = 0
        self.unknown10 = 0
        self.unknown11 = 0

        self._s = struct.Struct(self._structformat)

    def unpack(self, buf):
        (self.filesize,
         self.headersize,
         self.dataStartOffset,
         self.filelength,
         self.unknown3,
         self.filelength2,
         self.unknown5,
         self.numNodes,
         self.nodeEntriesOffset,
         self.numEntries,
         self.fileEntriesOffset,
         self.stringTableLength,
         self.stringTableOffset,
         self.numFiles,
         self.unknown10, self.unknown11) = self._s.unpack_from(buf)

    def size(self):
        # print self._s.size, "ohai"
        return self._s.size


class RARCNode:
    _structformat = ">IIHHI"

    def __init__(self):
        self.type = 0
        self.filenameOffset = 0  # directory name, offset into string table
        self.filenameHash = 0
        self.numFileEntries = 0  # how manu files belong to this node?
        self.firstFileEntryOffset = 0
        self._s = struct.Struct(self._structformat)

    def unpack(self, buf):
        (self.type,
         self.filenameOffset,
         self.filenameHash,
         self.numFileEntries,
         self.firstFileEntryOffset) = self._s.unpack_from(buf)

    def size(self):
        # print self._s.size
        return self._s.size


class RARCFileEntry:
    _structformat = ">H4xHII4x"

    def __init__(self):
        self.id = 0    # file id. if 0xFFFF, this entry is a subdir link
        # 4 bytes unknown
        self.filenameOffset = 0  # file/subdir name, offset into string table
        self.dataOffset = 0    # offset to file data (for subdirs: index of node representing subdir)
        self.dataSize = 0  # size of data

        self._s = struct.Struct(self._structformat)

    def unpack(self, buf):
        (self.id,
         self.filenameOffset,
         self.dataOffset,
         self.dataSize) = self._s.unpack_from(buf)

    def size(self):
        return self._s.size
