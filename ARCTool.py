#!/usr/bin/env python
import binascii
import struct
import sys
import os
from optparse import OptionParser
from rarc_headers import (RARCHeader, RARCInfoBlock, RARCNode, RARCFileEntry)
from u8_headers import (U8ArchiveHeader, U8Node, U8Globals)


def openOutput(f):
    try:
        return open(f, "wb")
    except IOError:
        print "Output file could not be opened!"
        exit()


def makedir(dirname):
    global quiet
    try:
        os.mkdir(dirname)
    except OSError, e:
        if not quiet:
            print "WARNING: Directory", dirname, "already exists!"


def unyaz(input, output):
    global quiet, listMode
    # shamelessly stolen^W borrowed from yagcd
    data_size, = struct.unpack_from(">I", input.read(4))  # uncompressed data size
    if listMode:
        print "Uncompressed size:", data_size, "bytes"
        return
    t = input.read(8)  # dummy
    srcplace = 0
    dstplace = 0
    bitsleft = 0
    currbyte = 0
    if not quiet:
        print "Reading input"
    src = input.read()
    dst = [" "]*data_size
    # print len(dst), len(src)
    percent = 0
    if not quiet:
        sys.stdout.write("Decompressing     0%")
        sys.stdout.flush()
    while dstplace < data_size:
        if bitsleft == 0:
            currbyte = ord(src[srcplace])
            srcplace += 1
            bitsleft = 8
        if (currbyte & 0x80) != 0:
            dst[dstplace] = src[srcplace]
            dstplace += 1
            srcplace += 1
        else:
            byte1 = ord(src[srcplace])
            byte2 = ord(src[srcplace+1])
            srcplace += 2
            dist = ((byte1 & 0xF) << 8) | byte2
            copySource = dstplace - (dist + 1)
            numbytes = byte1 >> 4
            if numbytes == 0:
                numbytes = ord(src[srcplace]) + 0x12
                srcplace += 1
            else:
                numbytes += 2
            j = 0
            for i in range(0, numbytes):
                dst[dstplace] = dst[copySource]
                copySource += 1
                dstplace += 1
                j += 1
        currbyte = (currbyte << 1)
        bitsleft -= 1
        if not quiet:
            calcpercent = ((dstplace*1.0)/data_size)*100
            if int(calcpercent) > percent:
                if int(calcpercent) > 9:
                    sys.stdout.write("\b")
                sys.stdout.write("\b\b" + str(int(calcpercent)) + "%")
                sys.stdout.flush()
                percent = calcpercent
    if not quiet:
        print "\nWriting output"
    output.write("".join(dst))


def getNode(index, f, header, info):
    global verbose

    retval = RARCNode()
    f.seek(header.size() + info.size() + 4 + index*retval.size())
    s = f.read(retval.size())
    retval.unpack(s)

    if verbose:
        typeString = binascii.unhexlify(('%08x' % (retval.type)))
        print '*** node %u ***' % (index)
        print 'type:\t\t%s (0x%08x)' % (typeString, retval.type)
        print 'name offset:\t0x%08x' % (retval.filenameOffset)
        print 'name hash:\t0x%04x' % (retval.filenameHash)
        print '# entries:\t0x%04x (%u)' % (
            retval.numFileEntries, retval.numFileEntries)
        print 'file offset:\t0x%08x' % (retval.firstFileEntryOffset)

    return retval


def getString(pos, f):
    t = f.tell()
    f.seek(pos)
    retval = []
    char = 0
    while True:
        char = f.read(1)
        if char == "\0":
            break
        retval.append(char)
    f.seek(t)
    return "".join(retval)


def getFileEntry(index, info, f):
    retval = RARCFileEntry()
    f.seek(info.fileEntriesOffset + index*retval.size() + 0x20)
    retval.unpack(f.read(retval.size()))
    return retval


def processNode(node, header, info, f):
    global quiet, depthnum, listMode
    nodename = getString(node.filenameOffset + info.stringTableOffset + 0x20,
                         f)
    if not listMode:
        if not quiet:
            print "Processing node", nodename
        makedir(nodename)
        os.chdir(nodename)
    else:
        print ("  "*depthnum) + nodename + "/"
        depthnum += 1
    for i in range(0, node.numFileEntries):
        currfile = getFileEntry(node.firstFileEntryOffset + i, info, f)
        currname = getString(currfile.filenameOffset + info.stringTableOffset + 0x20, f)
        if (currfile.id == 0xFFFF):  # file is a subdir
            if currname != "." and currname != "..":  # don't go to "." and ".."
                processNode(
                    getNode(
                        currfile.dataOffset,
                        f,
                        header,
                        info),
                    header,
                    info,
                    f
                )
        else:
            if listMode:
                print ("  "*depthnum) + currname, "-", currfile.dataSize
                continue
            if not quiet:
                print "Dumping", nodename + "/" + currname, " 0%",
            try:
                percent = 0
                dest = open(currname, "wb")
                f.seek(currfile.dataOffset + header.dataStartOffset + 0x20)
                size = currfile.dataSize
                while size > 0:
                    if not quiet:
                        calcpercent = int(((currfile.dataSize-size)/(currfile.dataSize*1.0))*100)
                        calcpercent = int(calcpercent)
                        if calcpercent > percent:
                            if calcpercent > 9:
                                sys.stdout.write("\b")
                            sys.stdout.write("\b\b" + str(calcpercent) + "%")
                            sys.stdout.flush()
                            percent = calcpercent
                    dest.write(f.read(size))
                    size -= 1024
                if not quiet:
                    if percent > 9:
                        sys.stdout.write("\b")
                    sys.stdout.write("\b\b100%")
                    print ""
                dest.close()
            except IOError:
                print "OMG SOMETHING WENT WRONG!!!!1111!!!!!"
                exit()
    if not listMode:
        os.chdir("..")
    else:
        depthnum -= 1


def unrarc(i, outputPath):
    global listMode, verbose
    header = RARCHeader()
    header.unpack(i.read(header.size()))

    info_block = RARCInfoBlock()
    info_block.unpack(i.read(info_block.size()))

    if verbose:
        print header
        print info_block

    if not listMode:
        try:
            makedir(outputPath)
        except:
            pass
        os.chdir(outputPath)

    processNode(getNode(0, i, header, info_block), header, info_block, i)


def get_u8_name(i, g, node):
    retval = []
    i.seek(g.string_table + node.name_offset-1)
    while True:
        t = i.read(1)
        if t == "\0":
            break
        retval.append(t)
    return "".join(retval)


def get_u8_node(i, g, index):
    retval = U8Node()
    index -= 1
    i.seek(g.header.rootnode_offset + (index * retval.size()))
    retval.unpack(i.read(retval.size()))
    return retval


def unu8(i, o):
    global quiet, depthnum, listMode
    header = U8ArchiveHeader()
    header.unpack(i.read(header.size()))
    if not listMode:
        try:
            makedir(o)
        except:
            pass
        os.chdir(o)
    root = U8Node()
    root.unpack(i.read(header.size()))
    g = U8Globals()
    g.rootnode = root
    g.numnodes = root.fsize
    g.header = header
    g.string_table = ((root.fsize)*root.size()) + header.rootnode_offset + 1
    depth = [root.fsize]
    for index in range(2, root.fsize+1):
        node = get_u8_node(i, g, index)
        name = get_u8_name(i, g, node)
        if listMode:
            if node.type == 0:
                print ("  "*depthnum) + name, "-", node.fsize, "bytes"
            elif node.type == 0x0100:
                print ("  "*depthnum) + name + "/"
                depthnum += 1
                depth.append(node.fsize)
        elif node.type == 0:
            if not quiet:
                print "Dumping file node", name, " 0%",
            i.seek(node.data_offset)
            try:
                dest = open(name, "wb")
                percent = 0
                size = node.fsize
                while size > 0:
                    if not quiet:
                        calcpercent = int(((node.fsize-size)/(node.fsize*1.0))*100)
                        if calcpercent > percent:
                            if calcpercent > 9:
                                sys.stdout.write("\b")
                            sys.stdout.write("\b\b" + str(calcpercent) + "%")
                            sys.stdout.flush()
                            percent = calcpercent
                    dest.write(f.read(size))
                    size -= 1024
                if not quiet:
                    if percent > 9:
                        sys.stdout.write("\b")
                    sys.stdout.write("\b\b100%\n")
                dest.close()
            except IOError:
                print "OMG SOMETHING WENT WRONG!!!!!!!111111111!!!!!!!!"
                exit()
        elif node.type == 0x0100:
            if not quiet:
                print "Processing node", name
            makedir(name)
            os.chdir(name)
            depth.append(node.fsize)
        if index == depth[-1]:
            if not listMode:
                os.chdir("..")
            depthnum -= 1
            depth.pop()
    if not listMode:
        os.chdir("..")


def main():
    global quiet, listMode, depthnum, verbose
    parser = OptionParser(usage="python %prog [-q] [-o <output>] <inputfile> [inputfile2] ... [inputfileN]", version="ARCTool 0.3b")
    parser.add_option("-o", "--output", action="store", type="string",
                      dest="of",
                      help="write output to FILE/DIR. If you are extracting multiple archives, all of them will be put in this dir.",
                      metavar="FILE/DIR")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                      default=False,
                      help="don't print anything (except errors)")
    parser.add_option("-l", "--list", action="store_true", dest="listMode",
                      default=False,
                      help="print a list of files contained in the specified archive (ignores -q)")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False)

    (options, args) = parser.parse_args()

    of = options.of
    quiet = options.quiet
    listMode = options.listMode
    verbose = options.verbose

    depthnum = 0

    if len(args) < 1:
        parser.error("Input filename required")

    if len(args) > 1:
        if options.of is not None:
            makedir(of)
            os.chdir(of)

    for inFile in args:
        if options.of is None or len(args) > 1:
            of = os.path.split(inFile)[1] + ".extracted"
        if len(args) > 1 and options.of is not None:
            inFile = "../" + inFile
        try:
            f = open(inFile, "rb")
        except IOError:
            print "Input file could not be opened!"
            exit()
        type = f.read(4)
        if type == "Yaz0":
            if not quiet:
                print "Yaz0 compressed archive"
            unyaz(f, openOutput(of))
        elif type == "RARC":
            if not quiet:
                print "RARC archive"
            unrarc(f, of)
        elif type == "U\xAA8-":
            if not quiet:
                print "U8 archive"
            unu8(f, of)
        else:
            print "Unknown archive type!"
            exit()
        f.close()


if __name__ == "__main__":
    main()
