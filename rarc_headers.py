import binascii
import struct
import os
from header import BaseHeader


def makedir(dirname):
    try:
        os.mkdir(dirname)
    except OSError, e:
        print e


def hash_string(string):
    '''Hash of string inserted into string table'''

    string = string.rstrip('\x00')

    result = 0
    for c in string:
        result *= 3
        result += ord(c)
        result %= 0x10000

    return result


def next_boundary(offset):
    while offset % 0x20 != 0:
        offset += 1

    return offset


class RARCFile:

    def __init__(self, quiet=False, list_mode=False, verbose=False):
        self.quiet = quiet
        self.list_mode = list_mode
        self.verbose = verbose

        self.header = RARCHeader()
        self.info_block = RARCInfoBlock()
        self.nodes = []
        self.file_entries = []
        self.string_table = ''
        self.string_lookup = {}
        self.file_data = ''

    def read_node(self, index):
        node = RARCNode()

        node_offset = self.header.size()
        node_offset += self.info_block.size()
        node_offset += index * node.size()

        self.in_file.seek(node_offset)

        node.unpack(self.in_file.read(node.size()))

        node.name = self.read_string(node.filenameOffset)
        if hash_string(node.name) != node.filenameHash:
            print 'WARNING: Incorrect hash for "%s"' % (node.name)
            print '%u != %u' % (hash_string(node.name),
                                node.filenameHash)

        return node

    def read_file_entry(self, index):
        file_ent = RARCFileEntry()

        file_offset = self.header.size()
        file_offset += self.info_block.fileEntriesOffset
        file_offset += file_ent.size() * index

        self.in_file.seek(file_offset)

        file_ent.unpack(self.in_file.read(file_ent.size()))

        file_ent.name = self.read_string(file_ent.filenameOffset)
        if hash_string(file_ent.name) != file_ent.filenameHash:
            print 'WARNING: Incorrect hash for "%s"' % (file_ent.name)
            print '%u != %u' % (hash_string(file_ent.name),
                                file_ent.filenameHash)

        return file_ent

    def read_file_content(self, file_ent):
        content_offset = self.header.size()
        content_offset += self.header.dataOffset
        content_offset += file_ent.dataOffset

        self.in_file.seek(content_offset)

        return self.in_file.read(file_ent.dataSize)

    def read_string(self, offset):
        # orig_offset = self.in_file.tell()

        full_offset = self.header.size()
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

        # self.in_file.seek(orig_offset)

        return result

    def insert_string(self, string):
        '''Return (offset, hash) of string inserted into table'''

        try:
            return self.string_lookup[string]
        except KeyError:
            pass

        hashed = hash_string(string)
        offset = len(self.string_table)
        self.string_table += string + '\x00'

        self.string_lookup[string] = (offset, hashed)

        return (offset, hashed)

    def process_node(self, node, depth=0):
        '''Traverse a node, extracting subdirectories and files'''
        if self.verbose:
            print node

        if not self.list_mode:
            if not self.quiet:
                print 'Processing node "%s"' % (node.name)
            makedir(node.name)
            os.chdir(node.name)
        else:
            print '%s%s/' % (' ' * depth, node.name)

        for i in range(node.numFileEntries):
            cur_file = self.read_file_entry(node.firstEntryIndex + i)

            if self.verbose:
                print cur_file
                print 'filename: %s' % (cur_file.name)

            # process subdirectory
            if cur_file.id == 0xFFFF:
                if cur_file.name in ['.', '..']:
                    continue

                next_node = self.read_node(cur_file.dataOffset)
                self.process_node(next_node, depth + 1)
            # process file
            else:
                if self.list_mode:
                    print '%s%s - %u' % (' ' * (depth + 1),
                                         cur_file.name,
                                         cur_file.dataSize)
                else:
                    # if not self.quiet:
                    #     print 'Dumping %s/%s' % (node.name, cur_file.name)

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
        self.out_file = open(out_path, 'wb')

        in_path = in_path.rstrip('/\\')
        print 'root directory: %s' % (os.path.basename(in_path))

        self.insert_string('.')
        self.insert_string('..')
        self.insert_node(in_path, 'ROOT')

        # Header and info block
        self.update_header()
        if self.verbose:
            print self.header

        self.out_file.write(self.header.pack())
        self.out_file.write(self.info_block.pack())

        # Nodes
        for node in self.nodes:
            self.out_file.write(node.pack())
        self.pad_to_boundary()

        # File entries
        for file_entry in self.file_entries:
            self.out_file.write(file_entry.pack())
        self.pad_to_boundary()

        # String table
        self.out_file.write(self.string_table)
        self.pad_to_boundary()

        # File data
        self.out_file.write(self.file_data)

        self.out_file.close()

    def insert_node(self, node_path, node_type, parent_index=None):
        node = RARCNode()

        node_path = node_path.rstrip('/\\')

        node.name = os.path.basename(node_path)

        if not self.quiet:
            print 'inserting node "%s/"' % (node.name)

        # Get index for current node and then insert it
        node_index = len(self.nodes)
        self.nodes.append(node)

        # Node type
        if type(node_type) == int:
            if (node_type > 0xFFFF):
                raise Exception('node type must be 16 bit')
            node.type = node_type
        elif type(node_type) == str:
            if len(node_type) != 4:
                raise Exception('node type must be 4 characters')
            node.type = struct.unpack('>I', node_type)[0]
        else:
            raise Exception('invalid node type argument')

        # Node entries
        node.firstEntryIndex = len(self.file_entries)

        (node.filenameOffset,
         node.filenameHash) = self.insert_string(node.name)

        dir_list = sorted(os.listdir(node_path))
        subdir_files = []
        for filename in dir_list:
            if filename in ['.', '..']:
                continue

            full_filename = os.path.join(node_path, filename)

            # Insert sub-directory node
            if os.path.isdir(full_filename):
                subdir_file_index = self.insert_file(full_filename,
                                                     node_link=0xBEEF)
                subdir_files.append(subdir_file_index)
            # Insert file
            else:
                print 'insert file "%s"' % (full_filename)
                self.insert_file(full_filename)

            node.numFileEntries += 1

        # insert '.' and '..' links
        if parent_index is None:
            parent_index = 0xFFFFFFFF

        self.insert_file('.', node_link=node_index)
        self.insert_file('..', node_link=parent_index)
        node.numFileEntries += 2

        # Insert subdirectory nodes and update file entry links
        for subdir_file_index in subdir_files:
            subdir_entry = self.file_entries[subdir_file_index]
            full_filename = os.path.join(node_path, subdir_entry.name)

            sub_node_index = self.insert_node(full_filename,
                                              'DATA',
                                              parent_index=node_index)
            subdir_entry.dataOffset = sub_node_index

        return node_index

    def insert_file(self, file_path, node_link=None):
        file_entry = RARCFileEntry()

        file_index = len(self.file_entries)
        self.file_entries.append(file_entry)

        file_entry.name = os.path.basename(file_path)

        (file_entry.filenameOffset,
         file_entry.filenameHash) = self.insert_string(file_entry.name)

        # This is a directory
        if node_link is not None:
            file_entry.id = 0xFFFF
            file_entry.type = 0x200
            file_entry.dataOffset = node_link
            file_entry.dataSize = 0x10
        # This is regular file
        else:
            file_entry.id = file_index
            file_entry.type = 0x2100

            # Insert file data
            file_handle = open(file_path, 'rb')
            file_contents = file_handle.read()
            file_handle.close()

            file_entry.dataSize = len(file_contents)
            file_entry.dataOffset = self.insert_file_data(file_contents)

        return file_index

    def insert_file_data(self, data):
        offset = len(self.file_data)
        end = offset + len(data)
        padding = '\x00' * (next_boundary(end) - end)
        self.file_data += data + padding
        return offset

    def update_info_block(self):
        self.info_block.numNodes = len(self.nodes)
        self.info_block.nodeEntriesOffset = next_boundary(
            self.info_block.size()
        )

        self.info_block.numEntries = len(self.file_entries)
        self.info_block.fileEntriesOffset = next_boundary(
            self.info_block.nodeEntriesOffset +
            (RARCNode().size() * self.info_block.numNodes)
        )

        self.info_block.stringTableLength = next_boundary(len(self.string_table))
        self.info_block.stringTableOffset = next_boundary(
            self.info_block.fileEntriesOffset +
            (RARCFileEntry().size() * self.info_block.numEntries)
        )

        # number of file entries that are files, not directories
        # though in some RARCs this is the same as # of entries
        self.info_block.numFiles = self.info_block.numEntries

        self.info_block.unknown10 = 0x0100

    def update_header(self):
        self.update_info_block()

        self.header.dataLength = len(self.file_data)
        self.header.dataLength2 = self.header.dataLength

        self.header.dataOffset = next_boundary(
            self.info_block.stringTableOffset +
            self.info_block.stringTableLength
        )

        self.header.fileSize = \
            self.header.size() + \
            self.header.dataOffset + \
            self.header.dataLength

    def pad_to_boundary(self, target=None):
        cur_pos = self.out_file.tell()

        if target is not None:
            next_pos = target
        else:
            next_pos = next_boundary(cur_pos)

        zero_pad = '\x00' * (next_pos - cur_pos)
        self.out_file.write(zero_pad)


class RARCHeader(BaseHeader):
    _structformat = ">IIIIIIII"

    def __init__(self):
        BaseHeader.__init__(self)

        # 4 bytes for magic "RARC"
        self.magic = 0x52415243

        self.fileSize = 0
        self.headerSize = self.size()

        self.dataOffset = 0  # offset to data, relative to end of header
        self.dataLength = 0
        self.unknown3 = 0
        self.dataLength2 = 0
        self.unknown5 = 0

    def unpack(self, buf):
        (self.magic,
         self.fileSize,
         self.headerSize,
         self.dataOffset,
         self.dataLength,
         self.unknown3,
         self.dataLength2,
         self.unknown5) = self._s.unpack_from(buf[:self.size()])

    def pack(self):
        return self._s.pack(
            self.magic,
            self.fileSize,
            self.headerSize,
            self.dataOffset,
            self.dataLength,
            self.unknown3,
            self.dataLength2,
            self.unknown5)

    def __str__(self):
        result = ''
        result += '*** RARC header ***\n'
        result += 'total size:\t0x%08x (%u)\n' % (
            self.fileSize,
            self.fileSize)
        result += 'header size:\t0x%08x\n' % (self.headerSize)
        result += 'data start:\t0x%08x\n' % (self.dataOffset)
        result += 'files size:\t0x%08x\n' % (self.dataLength)
        result += 'unknown 3:\t0x%08x\n' % (self.unknown3)
        result += 'files size2:\t0x%08x\n' % (self.dataLength2)
        result += 'unknown 5:\t0x%08x' % (self.unknown5)
        return result


class RARCInfoBlock(BaseHeader):

    _structformat = ">IIIIIIHHI"

    def __init__(self):
        BaseHeader.__init__(self)

        self.numNodes = 0
        self.nodeEntriesOffset = self.size()  # offset to node, relative to info block
        self.numEntries = 0
        self.fileEntriesOffset = 0

        self.stringTableLength = 0
        self.stringTableOffset = 0  # where is the string table stored? add 0x20

        # number of file entries that are files, not directories
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

    def pack(self):
        return self._s.pack(
            self.numNodes,
            self.nodeEntriesOffset,
            self.numEntries,
            self.fileEntriesOffset,
            self.stringTableLength,
            self.stringTableOffset,
            self.numFiles,
            self.unknown10,
            self.unknown11)

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
        self.firstEntryIndex = 0

        self.name = None

    def unpack(self, buf):
        (self.type,
         self.filenameOffset,
         self.filenameHash,
         self.numFileEntries,
         self.firstEntryIndex) = self._s.unpack_from(buf)

        self.typeString = binascii.unhexlify(('%08x' % (self.type)))

    def pack(self):
        return self._s.pack(
            self.type,
            self.filenameOffset,
            self.filenameHash,
            self.numFileEntries,
            self.firstEntryIndex)

    def __str__(self):
        result = ''
        result += '*** node ***\n'
        result += 'type:\t\t%s (0x%08x)\n' % (self.typeString, self.type)
        result += 'name offset:\t0x%08x\n' % (self.filenameOffset)
        result += 'name hash:\t0x%04x\n' % (self.filenameHash)
        result += '# entries:\t0x%04x (%u)\n' % (
            self.numFileEntries, self.numFileEntries)
        result += 'entries index:\t0x%08x' % (self.firstEntryIndex)

        return result


class RARCFileEntry(BaseHeader):
    _structformat = ">HHHHIII"

    def __init__(self):
        BaseHeader.__init__(self)

        self.id = 0  # file id. if 0xFFFF, this entry is a subdir link
        self.filenameHash = 0
        self.type = 0
        self.filenameOffset = 0  # file/subdir name, offset into string table
        self.dataOffset = 0  # offset to file data, or index of directory node
        self.dataSize = 0  # size of data
        self.unknown1 = 0  # always 0?

        self.name = None

    def unpack(self, buf):
        (self.id,
         self.filenameHash,
         self.type,
         self.filenameOffset,
         self.dataOffset,
         self.dataSize,
         self.unknown1) = self._s.unpack_from(buf)

    def pack(self):
        return self._s.pack(
            self.id,
            self.filenameHash,
            self.type,
            self.filenameOffset,
            self.dataOffset,
            self.dataSize,
            self.unknown1)

    def __str__(self):
        result = '*** file ***\n'
        result += 'id:\t0x%04x\n' % (self.id)
        result += 'type:\t0x%04x\n' % (self.type)
        result += 'name hash:\t0x%04x\n' % (self.filenameHash)
        result += 'name offset:\t0x%04x\n' % (self.filenameOffset)
        result += 'data offset:\t0x%08x\n' % (self.dataOffset)
        result += 'data size:\t0x%08x\n' % (self.dataSize)
        result += 'unknown:\t0x%08x' % (self.unknown1)
        return result
