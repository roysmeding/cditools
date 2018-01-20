import datetime

from .basic_types import *
from .file_stream import FileStream

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

class ChannelInfo(object):
    def __init__(self):
        self.n_audio = 0
        self.n_video = 0
        self.n_data  = 0
        self.n_empty = 0

class RecordInfo(object):
    def __init__(self, f, start_idx):
        self.file      = f
        self.start_idx = start_idx
        self.channels  = {}

class File(object):
    def __init__(self, sector, offset, directory):
        self.sector = sector
        self.image = self.sector.image
        self.offset = offset
        self.directory = directory

        self.record_size = number(self.get_data(0, 1))
        """The size in bytes of this directory record."""

        self.EAR_size = number(self.get_data(1, 2))
        """The number of blocks at the beginning of the file reserved for
        extended attribute information. The format of the extended attribute
        record is not defined and is reserved for application use."""

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
            for d in self.image.path_table.directories:
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
        return self.sector.get_data(self.offset+start, self.offset+end)

    @property
    def records(self):
        if not hasattr(self, '_records'):
            self._compute_record_info()
       
        return self._records

    def _compute_record_info(self):
        self._records = []
        record = None

        for block in self.get_blocks():
            sh = block.subheader

            if record is None:
                record = RecordInfo(self, block.index)
            
            if not sh.channel_number in record.channels:
                record.channels[sh.channel_number] = ChannelInfo()

            if   sh.audio:
                record.channels[sh.channel_number].n_audio += 1
            elif sh.video:
                record.channels[sh.channel_number].n_video += 1
            elif sh.data:
                record.channels[sh.channel_number].n_data  += 1
            else:
                record.channels[sh.channel_number].n_empty += 1

            if block.subheader.eor or block.subheader.eof:
                self._records.append(record)
                record = None

    def get_blocks(self, record=None, channel=None):
        """Generates the blocks belonging to the file in order"""
        if record is None:
            idx = self.image.lbn2idx(self.first_lbn)
            cur_record = 0
        else:
            idx = self.records[record].start_idx
            cur_record = record

        while True:
            block = self.image.get_sector(idx)
            sh = block.subheader

            num_match = (self.number == 0) or (sh.file_number == self.number)
            rec_match = (record  is None) or (cur_record == record)
            cha_match = (channel is None) or (sh.channel_number == channel)

            if num_match and rec_match and cha_match:
                yield block

            if (record is None) and sh.eof:
                break

            if sh.eor:
                if (not record is None) and (cur_record == record):
                    break

                cur_record += 1

            idx += 1

    def open(self, record=None, channel=None):
        return FileStream(self, record, channel)
