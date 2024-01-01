# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""
Minimal implementation of Squashfs for extracting files from an image.

Information sourced from:
https://dr-emann.github.io/squashfs/
https://github.com/plougher/squashfs-tools/blob/master/squashfs-tools/squashfs_fs.h

Assumptions made:
- Zstd is used for compression.
- Directory table consists of only one metadata block.
- There is only one file with the specific name i.e. no file of the same name in another directory.
- We only need to read inodes of basic files.
"""

import os

from ctypes import CDLL, c_void_p, c_size_t, create_string_buffer
from ctypes.util import find_library

from struct import unpack, calcsize
from dataclasses import dataclass
from math import log2, ceil

from .kodiutils import log


class ZstdDecompressor:
    """
    zstdandard decompressor class

    It's a class to avoid having to load the zstd library for every decompression.
    """
    def __init__(self):
        libzstd = CDLL(find_library("zstd"))
        self.zstddecomp = libzstd.ZSTD_decompress
        self.zstddecomp.restype = c_size_t
        self.zstddecomp.argtypes = (c_void_p, c_size_t, c_void_p, c_size_t)
        self.iserror = libzstd.ZSTD_isError

    def decompress(self, comp_data, comp_size, outsize=8*2**10):
        """main function, decompresses binary string <src>"""
        if len(comp_data) != comp_size:
            raise IOError("Decompression failed! Length of compressed data doesn't match given size.")

        dest = create_string_buffer(outsize)

        actual_outsize = self.zstddecomp(dest, len(dest), comp_data, len(comp_data))
        if self.iserror(actual_outsize):
            raise IOError(f"Decompression failed! Error code: {actual_outsize}")
        return dest[:actual_outsize]  # outsize is always a multiple of 8K, but real size may be smaller


@dataclass(frozen=True)
class SBlk:
    """superblock as dataclass, does some checks after initialization"""
    s_magic: int
    inodes: int
    mkfs_time: int
    block_size: int
    fragments: int
    compression: int
    block_log: int
    flags: int
    no_ids: int
    s_major: int
    s_minor: int
    root_inode: int
    bytes_used: int
    id_table_start: int
    xattr_id_table_start: int
    inode_table_start: int
    directory_table_start: int
    fragment_table_start: int
    lookup_table_start: int

    def __post_init__(self):
        """Some sanity checks"""
        squashfs_magic = 0x73717368  # Has to be present in every valid squashfs image
        if self.s_magic != squashfs_magic:
            raise IOError("Squashfs magic doesn't match!")

        if log2(self.block_size) != self.block_log:
            raise IOError("block_size and block_log do not match!")

        if bool(self.flags & 0x0004):
            raise IOError("Check flag should always be unset!")

        if self.s_major != 4 or self.s_minor != 0:
            raise IOError("Unsupported squashfs version!")

        if self.compression != 6:
            raise IOError("Image is not compressed using zstd!")


@dataclass(frozen=True)
class MetaDataHeader:
    """
    header of metadata blocks.

    Most things are contained in metadata blocks, including:
    - Compression options
    - directory table
    - fragment table
    - file inodes
    """
    compressed: bool
    size: int


@dataclass(frozen=True)
class InodeHeader:
    """squashfs_base_inode_header dataclass"""
    inode_type: int
    mode: int
    uid: int
    guid: int
    mtime: int
    inode_number: int


@dataclass(frozen=True)
class BasicFileInode:
    """
    This is squashfs_reg_inode_header, but without the base inode header part
    """
    start_block: int
    fragment: int
    offset: int
    file_size: int
    block_list: tuple[int]


@dataclass(frozen=True)
class DirectoryHeader:
    """squashfs_dir_header dataclass"""
    count: int
    start_block: int
    inode_number: int


@dataclass(frozen=True)
class DirectoryEntry:
    """
    Directory entry dataclass.

    This is squashfs_dir_entry in the squashfs-tools source code,
    but there "itype" is called "type" and "name_size" is just "size".

    Implements __len__, giving the number of bytes of the whole entry.
    """
    offset: int
    inode_number: int
    itype: int
    name_size: int
    name: bytes

    def __len__(self):
        """the first four entries are 2 bytes each. name is actually one byte longer than given in name_size"""
        return 8 + 1 + self.name_size


@dataclass(frozen=True)
class FragmentBlockEntry:
    """squashfs_fragment_entry dataclass"""
    start_block: int
    size: int
    unused: int  # This field has no meaning

# TODO: add more debug logging
class SquashFs:
    """
    Main class to handle a squashfs image, find and extract files from it.
    """
    def __init__(self, fpath):
        self.zdecomp = ZstdDecompressor()
        self.imfile = open(fpath, "rb")
        self.sblk = self.get_sblk()
        self.frag_entries = self.get_fragment_table()

    def get_sblk(self):
        """
        Read and check the superblock.
        """
        fmt = "<5I6H8Q"
        size = calcsize(fmt)

        self.imfile.seek(0)
        return SBlk(*unpack(fmt, self.imfile.read(size)))

    @staticmethod
    def fragment_block_entry(chunk):
        """
        Interpret <chunk> as fragment block entry.
        """
        fmt = "<Q2I"
        chunk = chunk[:calcsize(fmt)]
        return FragmentBlockEntry(*unpack(fmt, chunk))

    def get_fragment_table(self):
        """
        Read the fragment table.

        Returns the entries as tuple.
        """
        mblocks_num = ceil(self.sblk.fragments / 512)
        fmt = f"<{mblocks_num}Q"
        size = calcsize(fmt)

        self.imfile.seek(self.sblk.fragment_table_start)
        mblocks_poss = unpack(fmt, self.imfile.read(size))

        frag_entries = []
        for pos in mblocks_poss:
            data = self.get_metablock(pos)
            while len(data) > 0:
                entry = self.fragment_block_entry(data)
                frag_entries.append(entry)
                data = data[16:]  # each entry is 16 bytes

        return tuple(frag_entries)

    @staticmethod
    def get_size(csize):
        """
        For fragment entries and fragment blocks, the information if the data is compressed or not is contained in the (1 << 24) bit of the size.
        """
        compressed = not bool(csize & 0x1000000)
        size = csize & 0xffffff
        return compressed, size

    @staticmethod
    def metadata_header(chunk):
        """
        Interprets <chunk> as header of a metadata block
        """
        header = unpack("<H", chunk)[0]
        compressed = not bool(header & 0x8000)
        size = header & 0x7fff

        return MetaDataHeader(compressed, size)

    def get_metablock(self, block_pos):
        """
        Reads the header of a metadata block at block_pos and returns the extraced data.
        """
        self.imfile.seek(block_pos)

        mheader = self.metadata_header(self.imfile.read(2))

        data = self.imfile.read(mheader.size)
        if mheader.compressed:
            data = self.zdecomp.decompress(data, mheader.size)

        return data

    @staticmethod
    def inode_header(chunk):
        """
        Interprets <chunk> as inode header.
        """
        fmt = "<4H2I"
        chunk = chunk[:calcsize(fmt)]
        return InodeHeader(*unpack(fmt, chunk))

    def basic_file_inode(self, chunk):
        """
        Interprets <chunk> as inode of a basic file.
        """
        rest_fmt = "<4I"
        rest_size = calcsize(rest_fmt)
        rest_chunk, block_sizes_chunk = chunk[:rest_size], chunk[rest_size:]
        start_block, fragment, offset, file_size = unpack(rest_fmt, rest_chunk)

        num_blocks = ceil(file_size / self.sblk.block_size)
        if fragment != 0xffffffff:  # There is a fragment. In that case block_sizes is only a list of the full blocks
            num_blocks -= 1

        bsizes_fmt = f"<{num_blocks}I"
        bsizes_size = calcsize(bsizes_fmt)
        block_sizes_chunk = block_sizes_chunk[:bsizes_size]
        block_sizes = unpack(bsizes_fmt, block_sizes_chunk)
        return BasicFileInode(start_block, fragment, offset, file_size, block_sizes)

    @staticmethod
    def directory_header(chunk):
        """
        Interprets <chunk> as a header in the directory table.
        """
        fmt = "<3I"
        chunk = chunk[:calcsize(fmt)]
        return DirectoryHeader(*unpack(fmt, chunk))

    @staticmethod
    def directory_entry(chunk):
        """
        Interprets <chunk> as an entry in the directory table.
        """
        fmt = f"<HhHH{min(30, len(chunk) - 8)}s"
        chunk = chunk[:calcsize(fmt)]
        dentry = list(unpack(fmt, chunk))
        dentry[-1] = dentry[-1][:dentry[-2]+1]
        return DirectoryEntry(*dentry)

    def get_fragment(self, file_inode):
        """
        Get the fragment of a file.

        The fragment is the last part of a file.
        If the files size is not divisible by sblk.block_size, that last part may simply be stored in another block,
        or as a fragment in a fragment block (together with other fragments).
        """
        if file_inode.fragment == 0xffffffff:  # There is no fragment.
            return b''

        entry = self.frag_entries[file_inode.fragment]

        self.imfile.seek(entry.start_block)

        compressed, size = self.get_size(entry.size)
        data = self.imfile.read(size)

        if compressed:
            data = self.zdecomp.decompress(data, size, self.sblk.block_size)

        dstart = file_inode.offset
        dlen = file_inode.file_size % self.sblk.block_size
        data = data[dstart:dstart + dlen]

        return data

    def get_dentry(self, name):
        """
        Searches the directory table for the entry for <name>.
        """
        data = self.get_metablock(self.sblk.directory_table_start)
        bname = name.encode()

        while len(data) > 0:
            header = self.directory_header(data)
            data = data[12:]

            for _ in range(header.count+1):
                dentry = self.directory_entry(data)
                if dentry.name == bname:
                    return header, dentry

                data = data[len(dentry):]

        raise FileNotFoundError(f"{name} not found!")

    def get_inode_from_pos(self, block_pos, pos_in_block):
        """
        Get the inode for a basic file from the starting point of the block and the position in the block.
        """
        data = self.get_metablock(block_pos)
        data = data[pos_in_block:]

        header = self.inode_header(data)
        data = data[16:]

        if header.inode_type == 2:  # 2 is basic file
            return self.basic_file_inode(data)

        log(4, "inode types other than basic file are not implemented!")
        return None

    def get_inode(self, name):
        """
        Get the inode for a basic file by its name.
        """
        head_entry = self.get_dentry(name)
        if not head_entry:
            return head_entry

        dhead, dentry = head_entry

        block_pos = self.sblk.inode_table_start + dhead.start_block
        pos_in_block = dentry.offset

        return self.get_inode_from_pos(block_pos, pos_in_block)

    def read_file_blocks(self, filename):
        """
        Generator where each iteration returns a block of file <filename> as bytes.
        """

        inode = self.get_inode(filename)

        fragment = self.get_fragment(inode)
        file_len = len(fragment)

        self.imfile.seek(inode.start_block)
        curr_pos = self.imfile.tell()

        for bsize in inode.block_list:
            compressed, size = self.get_size(bsize)

            if not curr_pos == self.imfile.tell():
                log(3, "Pointer not at correct position. Moving.")
                self.imfile.seek(curr_pos)

            block = self.imfile.read(size)
            curr_pos = self.imfile.tell()

            if compressed:
                block = self.zdecomp.decompress(block, size, self.sblk.block_size)

            file_len += len(block)
            yield block

        if file_len != inode.file_size:
            log(4, "Size of extracted file not correct. Something went wrong!")
            log(4, f"calculated file_len: {file_len}, given file_size: {inode.file_size}")
            return False

        yield fragment

    def extract_file(self, filename, target_dir):
        """
        Extracts file <filename> to <target_dir>
        """
        with open(os.path.join(target_dir, filename), "wb") as outfile:
            try:
                for block in self.read_file_blocks(filename):
                    outfile.write(block)

                return True
            except FileNotFoundError as err:
                log(4, err)
                return False
