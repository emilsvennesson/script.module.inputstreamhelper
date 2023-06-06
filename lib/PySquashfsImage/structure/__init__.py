from ctypes import LittleEndianStructure, c_int16, c_uint16, c_uint32

from ..const import Type


class _Base(LittleEndianStructure):

    @classmethod
    def from_bytes(cls, bytes_):
        return cls.from_buffer_copy(bytes_)


class DirEntry(_Base):
    _fields_ = [
        ("_offset", c_uint16),
        ("_inode_number", c_int16),
        ("_type", c_uint16),
        ("_size", c_uint16),
    ]
    _name = None

    @property
    def offset(self):
        return self._offset

    @property
    def inode_number(self):
        return self._inode_number

    @property
    def type(self):
        return Type(self._type)

    @property
    def size(self):
        return self._size

    @property
    def name(self):
        return self._name.decode()


class DirHeader(_Base):
    _fields_ = [
        ("_count", c_uint32),
        ("_start_block", c_uint32),
        ("_inode_number", c_uint32),
    ]

    @property
    def count(self):
        return self._count

    @property
    def start_block(self):
        return self._start_block

    @property
    def inode_number(self):
        return self._inode_number
