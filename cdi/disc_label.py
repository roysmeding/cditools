import datetime

from .basic_types import *
from .path_table import PathTable

def dl_datetime(seq):
    """The format of a 16-byte date and time field is recorded as a string of
    numerals "YYYYMMDDHHMMSStt" where tt means hundredths of a second. For
    example, 6:51 a.m. on September 6, 1954 would be recorded as
    "1954090606510000". No consideration is made for time zones. If a date is
    not used, it contains "0" characters."""

    assert len(seq) == 16

    if seq == '0'*16:
        return None
    else:
        year, month,  day    = int(seq[ 0: 4]), int(seq[ 4: 6]), int(seq[ 6: 8])
        hour, minute, second = int(seq[ 8:10]), int(seq[10:12]), int(seq[12:14])
        us = int(seq[14:16])*10000

        try:
            return datetime.datetime(year, month, day, hour, minute, second, us)
        except ValueError:
            return None

class DiscLabel(object):
    STANDARD   = 1      # the Standard File Structure Volume Descriptor record
    CODED      = 2      # the Coded Character Set File Structure Volume Descriptor record
    TERMINATOR = 255

    def __init__(self, sector):
        self.sector = sector
        
        self.type = number(self.get_data(0, 1))
        """The type of Disc Label Record"""

    def get_data(self, start, end):
        return self.sector.get_data(start, end)

    @staticmethod
    def create(sector):
        t = number(sector.get_data(0, 1))

        if t == DiscLabel.STANDARD:
            return StandardDiscLabel(sector)

        elif t == DiscLabel.CODED:
            raise NotImplementedError()

        elif t == DiscLabel.TERMINATOR:
            return TerminatorDiscLabel(sector)

        else:
            raise ValueError("Unknown disc label type {:d}".format(t))

class StandardDiscLabel(DiscLabel):
    """File Structure Volume Descriptor Record.

    Every CD-I disc contains at least one File Structure Volume Descriptor
    record."""

    def __init__(self, sector):
        super().__init__(sector)

        self.standard_id = rawstring(self.get_data(1, 6))
        """The standard to which the disc file structure conforms.
        CD-I discs contain the string "CD-I" followed immediately with a space
        character."""

        self.version = number(self.get_data(6, 7))
        """The version number of the standard to which the disc conforms.
        The current version is one."""

        self.volume_flags = number(self.get_data(7, 8))
        """The characteristics of the volume."""

        self.system_id = string(self.get_data(8, 40))
        """The operating system which may use any fields described as reserved
        for the system. All CD-I discs must contain the string "CD-RTOS" padded
        on the right with space characters."""

        self.volume_id = string(self.get_data(40, 72))
        """The logical name of the CD-I disc, padded on the right with space
        characters."""

        self.volume_size = number(self.get_data(84, 88))
        """The total size of the usable portion of the disc in blocks (e.g.,
        the highest addressable block to the operating system is the value of
        this field minus 1)."""

        self.charset = string(self.get_data( 88, 120))
        """One escape sequence according to the International Register of Coded
        Character Sets to be used with escape sequence standards for recording.
        The ESC character, which is the first character of all sequences, shall
        be omitted when recording this field."""

        self.album_size = number(self.get_data(122, 124))
        """The total number of discs in the album to which this disc belongs."""

        self.album_idx = number(self.get_data(126, 128))
        """The relative sequence number of this disc in the album to which it
        belongs. The first disc in the sequence will be the number 1."""

        self.block_size = number(self.get_data(130, 132))
        """The size of a block (in bytes) as seen by the file system. For CD-I
        discs, the block size is always 2048 bytes."""

        self.path_table_size = number(self.get_data(136, 140))
        """The size in bytes of the system Path Table."""

        self.path_table_address = number(self.get_data(148, 152))
        """The block address of the first block of the system Path Table."""

        self.album_id = string(self.get_data(190, 318))
        """The name of the album to which this disc belongs, padded on the
        right with space characters."""

        self.publisher_id = string(self.get_data(318, 446))
        """The publisher of the disc (i.e., who specified the contents of the
        disc), padded on the right with space characters."""

        self.data_preparer = string(self.get_data(446, 574))
        """The author of the contents of the disc, padded on the right with
        space characters."""

        self.app_id = string(self.get_data(574, 702))
        """The path name of the application program to execute when the disc is
        first mounted. Section VII.1.2 outlines how this name is used in the
        startup sequence."""

        self.copyright_file = string(self.get_data(702, 734))
        """Optionally contains the name of a file that contains a copyright
        message. Any desired information may be encoded in this file. It is
        accessed in an application dependent manner. This field is padded on
        the right with space characters. If there is no name, all characters
        are space characters."""

        self.abstract_file = string(self.get_data(739, 771))
        """Optionally contains the name of a file that contains an abstract
        message for the disc. Any desired information may be encoded in this
        file. It is accessed in an application dependent manner. This field is
        padded on the right with space characters. If there is no name, all
        characters are space characters."""

        self.biblio_file = string(self.get_data(776, 808))
        """This field optionally contains the name of a file that contains
        bibliographic information about the disc. Any desired information may
        be encoded in this file. It is accessed in an application dependent
        manner. This field is padded on the right with space characters. If
        there is no name, all characters are space characters."""

        self.created_date = dl_datetime(self.get_data(813, 829))
        """The date and time that the CD-I disc was originally mastered."""

        self.modified_date = dl_datetime(self.get_data(830, 846))
        """Recorded in this field are the date and time that the disc was last
        changed (e.g., re-mastered)."""

        self.expires_date = dl_datetime(self.get_data(847, 863))
        """If the data on a disc is valid only for a limited time, this field
        indicates the time at which the disc becomes obsolete."""

        self.effective_date = dl_datetime(self.get_data(864, 880))
        """If the data on a disc is not valid until a specific time, this field
        indicates the time at which the disc becomes useful."""

        self.fs_version = number(self.get_data(881, 882))
        """Indicates the revision number of the file structure standard to
        which the directory search files conform. It is set to one."""

    @property
    def path_table(self):
        return PathTable(self.sector.image.get_block(self.path_table_address), self.path_table_size)


class TerminatorDiscLabel(DiscLabel):
    """Terminator Record.
    
    At least one Terminator record is required on every CD-I disc. It is the
    last record in the Disc Label and signifies the end of the Disc Label."""

    def __init__(self, sector):
        super().__init__(sector)

        self.standard_id = rawstring(self.get_data(1, 6))
        """The standard to which the disc file structure conforms.
        CD-I discs contain the string "CD-I" followed immediately with a space
        character."""

        self.version = number(self.get_data(6, 7))
        """The version number of the standard to which the disc conforms.
        The current version is one."""
