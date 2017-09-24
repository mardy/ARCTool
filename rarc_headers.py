from header import BaseHeader


class RARCHeader(BaseHeader):
    _structformat = ">IIIIIII"

    def __init__(self):
        BaseHeader.__init__(self)

        self.filesize = 0
        self.headersize = 0
        self.dataStartOffset = 0  # offset to data, relative to end of header

        self.filelength = 0
        self.unknown3 = 0
        self.filelength2 = 0
        self.unknown5 = 0

    def unpack(self, buf):
        (self.filesize,
         self.headersize,
         self.dataStartOffset,
         self.filelength,
         self.unknown3,
         self.filelength2,
         self.unknown5) = self._s.unpack_from(buf[:self.size()])

    def __str__(self):
        result = ''
        result += '*** RARC header ***\n'
        result += 'total size:\t0x%08x (%u)\n' % (
            self.filesize,
            self.filesize)
        result += 'header size:\t0x%08x\n' % (self.headersize)
        result += 'data start:\t0x%08x\n' % (self.dataStartOffset)
        result += 'files size:\t0x%08x\n' % (self.filelength)
        result += 'unknown 3:\t0x%08x\n' % (self.unknown3)
        result += 'files size2:\t0x%08x\n' % (self.filelength2)
        result += 'unknown 5:\t0x%08x' % (self.unknown5)
        return result


class RARCInfoBlock(BaseHeader):

    _structformat = ">IIIIIIHHI"

    def __init__(self):
        BaseHeader.__init__(self)

        self.numNodes = 0
        self.nodeEntriesOffset = 0  # offset to node, relative to info block
        self.numEntries = 0
        self.fileEntriesOffset = 0

        self.stringTableLength = 0
        self.stringTableOffset = 0  # where is the string table stored? add 0x20

        self.numFiles = 0
        self.unknown10 = 0
        self.unknown11 = 0

    def unpack(self, buf):
        (self.numNodes,
         self.nodeEntriesOffset,
         self.numEntries,
         self.fileEntriesOffset,
         self.stringTableLength,
         self.stringTableOffset,
         self.numFiles,
         self.unknown10,
         self.unknown11) = self._s.unpack_from(buf)

    def __str__(self):
        result = ''
        result += '*** INFO BLOCK ***\n'
        result += '# nodes:\t0x%08x (%u)\n' % (self.numNodes, self.numNodes)
        result += 'node offset:\t0x%08x\n' % (self.nodeEntriesOffset)
        result += '# entries:\t0x%08x (%u)\n' % (
            self.numEntries, self.numEntries)
        result += 'file start:\t0x%08x\n' % (self.fileEntriesOffset)
        result += 'strings length:\t0x%08x\n' % (self.stringTableLength)
        result += 'string start:\t0x%08x\n' % (self.stringTableOffset)
        result += 'num files:\t0x%04x (%u)\n' % (self.numFiles, self.numFiles)
        result += 'unknown 10-11:\t0x%04x 0x%08x' % (
            self.unknown10, self.unknown11)
        return result


class RARCNode(BaseHeader):
    _structformat = ">IIHHI"

    def __init__(self):
        BaseHeader.__init__(self)

        self.type = 0
        self.filenameOffset = 0  # directory name, offset into string table
        self.filenameHash = 0
        self.numFileEntries = 0  # how manu files belong to this node?
        self.firstFileEntryOffset = 0

    def unpack(self, buf):
        (self.type,
         self.filenameOffset,
         self.filenameHash,
         self.numFileEntries,
         self.firstFileEntryOffset) = self._s.unpack_from(buf)


class RARCFileEntry(BaseHeader):
    _structformat = ">H4xHII4x"

    def __init__(self):
        BaseHeader.__init__(self)

        self.id = 0    # file id. if 0xFFFF, this entry is a subdir link
        # 4 bytes unknown
        self.filenameOffset = 0  # file/subdir name, offset into string table
        self.dataOffset = 0    # offset to file data (for subdirs: index of node representing subdir)
        self.dataSize = 0  # size of data

    def unpack(self, buf):
        (self.id,
         self.filenameOffset,
         self.dataOffset,
         self.dataSize) = self._s.unpack_from(buf)
