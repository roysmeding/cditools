from .basic_types import *
from .file import *

class Directory(object):
    def __init__(self, sector, offset):
        self.sector = sector
        self.offset = offset

        # read actual sector
        self._contents = []
        offset = 0

        self.name_size = number(self.get_data(0, 1))
        """The length of the directory file name string in this path table
        entry."""

        self.name = string(self.get_data(8, 8+self.name_size))
        """The name of the directory."""

        self.ear_size = number(self.get_data(1, 2))
        """The length of the Extended Attribute record."""

        self.directory_address = number(self.get_data(2, 6))
        """This field contains the beginning logical block number (LBN) of the
        directory file on disc."""

        self.directory_file = self.sector.image.get_block(self.directory_address)

        self.parent = number(self.get_data(6, 8))
        """This is the number (relative to the beginning of the Path Table) of
        this directory's parent."""

        while True:
            file_record_size = number(self.directory_file.get_data(offset+0, offset+1))

            if file_record_size == 0:
                break

            f = File(self.directory_file, offset, self)

            self._contents.append(f)
            offset += file_record_size

    def get_data(self, start, end):
        return self.sector.get_data(self.offset+start, self.offset+end)


    @property
    def parent_dir(self):
        return self.sector.image.path_table.directories[self.parent-1]

    @property
    def size(self):
        """The size of the directory record on disk"""
        return 8 + self.name_size + (self.name_size % 2)  # last term is padding byte if name size is uneven


    @property
    def contents(self):
        return self._contents[2:]

    @property
    def full_name(self):
        if self.name == "\x00": # root directory
            return '/'
        else:
            if self.parent_dir.full_name == '/':
                return '/' + self.name
            else:
                return self.parent_dir.full_name + '/' + self.name

