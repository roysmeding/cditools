import datetime

from .basic_types import *

# the directory entry datetime format
def dir_datetime(seq):
    assert len(seq) == 6

    year, month,  day    = 1900+number(seq[0:1]), number(seq[1:2]), number(seq[2:3])
    hour, minute, second = number(seq[3:4]), number(seq[4:5]), number(seq[5:6])

    return datetime.datetime(year, month, day, hour, minute, second)

def _flag(bit, doc):
    "helper for bit flag boilerplate"
    def getter(self):
        return True if (self.flags & (1<<bit)) else False
    return property(getter, doc=doc)

class FileAttributes(object):
    def __init__(self, flags):
        self.flags = flags

    owner_read = _flag( 0, "Owner read")
    owner_exec = _flag( 2, "Owner execute")
    group_read = _flag( 4, "Group read")
    group_exec = _flag( 6, "Group execute")
    world_read = _flag( 8, "World read")
    world_exec = _flag(10, "World execute")
    cdda       = _flag(14, "CD-DA file")
    directory  = _flag(15, "Directory")

class FileFlags(object):
    def __init__(self, flags):
        self.flags = flags

    hidden = _flag(0, "The file is hidden and does not usually appear in\
            directory listings.")

class File(object):
    def __init__(self, sector, offset, directory):
        self.sector    = sector
        self.image     = self.sector.image
        self.offset    = offset
        self.directory = directory

        self.record_size = number(self.get_data(0, 1))
        """The size in bytes of this directory record."""

        self.EAR_size = number(self.get_data(1, 2))
        """The number of blocks at the beginning of the file reserved for
        extended attribute information. The format of the extended attribute
        record is not defined and is reserved for application use."""

        assert self.EAR_size == 0, "The CD-I spec is unclear on how to handle the EAR record length field. Let the author know if you encounter this, so we can figure out how it actually works."

        self.first_lbn = number(self.get_data(6, 10))
        """The logical block number of the first block of the file."""

        self.first_block = self.image.get_block(self.first_lbn)
        """The first block of the file."""

        self.size =  number(self.get_data(14, 18))
        """The size of the file in bytes.
        
        (By convention the size of Form 2 sectors is considered as 2048 bytes
        by the system)"""

        self.creation_date =  dir_datetime(self.get_data(18, 24))
        """The date and time on which the file was created or last modified."""

        self.flags = FileFlags(number(self.get_data(25, 26)))

        self.interleave = (number(self.get_data(26, 27)), number(self.get_data(27, 28)))
        """Two unsigned 8-bit integers indicating how the file is interleaved.
        The numbers represent a ratio between sectors that belong to the file
        and those that do not. As an example, an interleave value of 1:3 would
        represent a file sector map as follows:

            * - - - * - - - * ...

        (* means a sector is part of the file and - means it is unrelated to
        the file.)

        For non-interleaved files both bytes must be set to zero."""

        self.album_idx = number(self.get_data(30, 32))
        """The Album Set Sequence number of the disc which contains this file.
        If the file resides on this disc this field is zero.

        The use and definition of the Album Set Sequence number is the
        responsibility of the content provider."""

        self.name_size = number(self.get_data(32, 33))
        """The number of characters in the file name field. If the length of
        the file name is even, a null padding byte is inserted on the end of
        the name to make the owner ID field begin on an even offset. The
        padding byte is not included in the file name size field."""

        self.real_name_size = self.name_size + (self.name_size % 2)
        """Like name_size, but with padding included"""

        self.name = string(self.get_data(33, 33+self.name_size))
        """The name of the file described by this directory record."""

        self.owner_user = number(self.get_data(35+self.real_name_size, 37+self.real_name_size))
        """The user identification number of the creator of this file."""

        self.owner_group = number(self.get_data(33+self.real_name_size, 35+self.real_name_size))
        """The group identification number of the creator of this file."""

        self.attributes = FileAttributes(number(self.get_data(37+self.real_name_size, 39+self.real_name_size)))
        """The file attributes and permissions. Indicates how the file is
        accessed and who (owner ID) may access it."""

        self.number = number(self.get_data(41+self.real_name_size, 42+self.real_name_size))
        """This number is recorded as the file identifier in the subheader of
        each sector belonging to a Mode 2 file. It is used to select sectors
        that belong to the file."""

    @property
    def is_directory(self):
        # Attributes aren't always set right in CD-I files, so we need to
        # check whether this file is in the path table to determine whether
        # it's a directory.

        return self.directory_record != None

    @property
    def directory_record(self):
        if not hasattr(self, '_directory_record'):
            self._directory_record = None
            for d in self.directory.path_table.directories:
                if d.directory_address == self.first_lbn:
                    self._directory_record = d
                    break

        return self._directory_record

    @property
    def full_name(self):
        if self.directory.name == "\x00":
            return '/' + self.name
        else:
            return self.directory.full_name + '/' + self.name

    def get_data(self, start, end):
        return self.sector.get_data(self.offset + start, self.offset + end)

    def blocks(self):
        """Yields all blocks belonging to the file in order"""

        idx = 0

        while True:
            block = self.image.get_block(self.first_lbn + idx)
            sh = block.subheader

            idx += 1

            if self.number != 0:
                # file might be interleaved
                if sh.file_number != self.number:
                    # block does not belong to this file
                    continue

            # at this point, the block belongs to this file.
            yield block

            if sh.eof:
                # end of file
                break
