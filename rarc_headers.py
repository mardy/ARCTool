import binascii
import os
from header import BaseHeader


def makedir(dirname):
    try:
        os.mkdir(dirname)
    except OSError, e:
        print e


class RARCFile:

    def __init__(self, quiet=False, list_mode=False, verbose=False):
        self.quiet = quiet
        self.list_mode = list_mode
        self.verbose = verbose

        self.magic_size = len('RARC')

        self.header = RARCHeader()
        self.info_block = RARCInfoBlock()
        self.nodes = []

    def read_node(self, index):
        node = RARCNode()

        node_offset = self.magic_size
        node_offset += self.header.size()
        node_offset += self.info_block.size()
        node_offset += index * node.size()

        self.in_file.seek(node_offset)

        node.unpack(self.in_file.read(node.size()))

        node.name = self.read_string(node.filenameOffset)

        return node

    def read_file_entry(self, index):
        file_ent = RARCFileEntry()

        file_offset = self.magic_size
        file_offset += self.header.size()
        file_offset += self.info_block.fileEntriesOffset
        file_offset += file_ent.size() * index

        self.in_file.seek(file_offset)

        file_ent.unpack(self.in_file.read(file_ent.size()))

        file_ent.name = self.read_string(file_ent.filenameOffset)

        return file_ent

    def read_file_content(self, file_ent):
        content_offset = self.magic_size
        content_offset += self.header.size()
        content_offset += self.header.dataStartOffset
        content_offset += file_ent.dataOffset

        self.in_file.seek(content_offset)

        return self.in_file.read(file_ent.dataSize)

    def read_string(self, offset):
        orig_offset = self.in_file.tell()

        full_offset = self.magic_size
        full_offset += self.header.size()
        full_offset += self.info_block.stringTableOffset
        full_offset += offset

        self.in_file.seek(full_offset)

        result = []
        while True:
            char = self.in_file.read(1)
            if char == "\0":
                break
            result.append(char)

        result = ''.join(result)

        self.in_file.seek(orig_offset)

        return result

    def process_node(self, node, depth=0):
        if not self.list_mode:
            if self.verbose:
                print 'Processing node "%s"' % (node.name)
            makedir(node.name)
            os.chdir(node.name)
        else:
            pass

        for i in range(node.numFileEntries):
            cur_file = self.read_file_entry(node.firstFileEntryOffset + i)

            if cur_file.name not in ['.', '..']:
                print '%s %s' % ('-' * (depth + 1), cur_file.name)

            # process subdirectory
            if cur_file.id == 0xFFFF:
                if cur_file.name in ['.', '..']:
                    continue

                next_node = self.read_node(cur_file.dataOffset)
                self.process_node(next_node, depth + 1)
            # process file
            else:
                if self.list_mode:
                    continue

                out_file = open(cur_file.name, 'wb')
                out_file.write(self.read_file_content(cur_file))
                out_file.close()

        if not self.list_mode:
            os.chdir('..')

    def unpack(self, in_file, out_path):
        self.in_file = in_file
        self.out_path = out_path

        self.header.unpack(in_file.read(self.header.size()))
        self.info_block.unpack(in_file.read(self.info_block.size()))

        if self.verbose:
            print self.header
            print self.info_block

        if not self.list_mode:
            try:
                makedir(out_path)
            except:
                pass
            os.chdir(out_path)

        # Recurse root nodes
        for i in range(self.info_block.numNodes):
            cur_node = self.read_node(i)

            if cur_node.typeString == 'ROOT':
                print 'root node "%s"' % (cur_node.name)
                self.process_node(cur_node)

    def pack(self, in_path, out_path):
        pass


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
        self.typeString = ''
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

        self.typeString = binascii.unhexlify(('%08x' % (self.type)))

    def __str__(self):
        result = ''
        result += '*** node ***\n'
        result += 'type:\t\t%s (0x%08x)\n' % (self.typeString, self.type)
        result += 'name offset:\t0x%08x\n' % (self.filenameOffset)
        result += 'name hash:\t0x%04x\n' % (self.filenameHash)
        result += '# entries:\t0x%04x (%u)\n' % (
            self.numFileEntries, self.numFileEntries)
        result += 'file offset:\t0x%08x' % (self.firstFileEntryOffset)


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
