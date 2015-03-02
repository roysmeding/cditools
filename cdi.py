import datetime
import mmap

# shorthand parsing methods. They take a sequence of characters (bytes) as input.
def number(seq):
    out = 0
    for c in seq:
        out = 256*out + ord(c)
    return out

def rawstring(seq, encoding='ascii'):
    return ''.join(seq)

def string(seq, encoding='ascii'):
    return rawstring(seq, encoding).rstrip()

# the disc label datetime format
def dl_datetime(seq):
    assert len(seq) == 16

    if seq == '0'*16:
        return None
    else:
        year, month,  day    = int(seq[ 0: 4]), int(seq[ 4: 6]), int(seq[ 6: 8])
        hour, minute, second = int(seq[ 8:10]), int(seq[10:12]), int(seq[12:14])
        us = int(seq[14:16])*10000
        return datetime.datetime(year, month, day, hour, minute, second, us)

# the directory entry datetime format
def dir_datetime(seq):
    assert len(seq) == 6

    year, month,  day    = 1900+number(seq[0:1]), number(seq[1:2]), number(seq[2:3])
    hour, minute, second = number(seq[3:4]), number(seq[4:5]), number(seq[5:6])

    return datetime.datetime(year, month, day, hour, minute, second)

class Subheader(object):
    "A sector sub-header"
    SIZE = 8

    def __init__(self, data):
        # check redundancy
        # for i in range(4):
        #     assert data[i] == data[4+i], "Redundant subheader data does not match"

        # fill in fields
        self.file_number    = number(data[0:1])
        self.channel_number = number(data[1:2])
        self.submode_raw    = number(data[2:3])
        self.coding_raw     = number(data[3:4])

    def _submode_flag(bit, doc):
        "helper for bit flag boilerplate"
        def getter(self):
            return True if (self.submode_raw & (1<<bit)) else False
        return property(getter, doc=doc)

    eor      = _submode_flag(0, "Sector is last in record")
    video    = _submode_flag(1, "Sector contains video")
    audio    = _submode_flag(2, "Sector contains audio")
    data     = _submode_flag(3, "Sector contains data")
    empty    = property(lambda self: (not self.video) and (not self.audio) and (not self.data), doc="Sector has no type")
    trigger  = _submode_flag(4, "Sector causes interrupt when read")
    form2    = _submode_flag(5, "Sector has Form 2 (more data, less error correction)")
    form1    = property(lambda self: not self.form2, doc="Sector has Form 1 (less data, more error correction)")
    realtime = _submode_flag(6, "Sector is for real-time reading")
    eof      = _submode_flag(7, "Sector is last in file")

class Sector(object):
    def __init__(self, disc, offset):
        self.disc = disc
        self.offset = offset
        self.subheader = Subheader(self[0:Subheader.SIZE])

    data_size   = property(lambda self: 2048 if self.subheader.form1 else 2324, doc="The number of data bytes in the sector")
    FULL_SIZE = 2336

    def __getitem__(self, key):
        return self.disc.image_file[self.offset:self.offset+self.FULL_SIZE][key]

    def __iter__(self, key):
        return iter(self.data)

    data = property(lambda self: self[Subheader.SIZE:Subheader.SIZE+self.data_size], doc="Returns the data part of the sector")

class DiscLabel(object):
    STANDARD   = 1
    CODED      = 2
    TERMINATOR = 255

    def __init__(self, sector):
        self.sector = sector
        self.type = number(sector.data[0:1])
        if self.type == DiscLabel.STANDARD:
            self.standard_id    = rawstring(sector.data[  1:  6])
            self.version        = number(sector.data[  6:  7])
            self.volume_flags   = number(sector.data[  7:  8])
            self.system_id      = string(sector.data[  8: 40])
            self.volume_id      = string(sector.data[ 40: 72])
            self.volume_size    = number(sector.data[ 84: 88])
            self.charset        = string(sector.data[ 88:120])
            self.album_size     = number(sector.data[122:124])
            self.album_idx      = number(sector.data[126:128])
            self.block_size     = number(sector.data[130:132])
            self.path_tbl_size  = number(sector.data[136:140])
            self.path_tbl_addr  = number(sector.data[148:152])
            self.album_id       = string(sector.data[190:318])
            self.publisher_id   = string(sector.data[318:446])
            self.data_preparer  = string(sector.data[446:574])
            self.app_id         = string(sector.data[574:702])
            self.copyright_file = string(sector.data[702:734])
            self.abstract_file  = string(sector.data[739:771])
            self.biblio_file    = string(sector.data[776:808])
            self.creation_date  = dl_datetime(sector.data[813:829])
            self.mod_date       = dl_datetime(sector.data[830:846])
            self.exp_date       = dl_datetime(sector.data[847:863])
            self.effective_date = dl_datetime(sector.data[864:880])
            self.fs_version     = number(sector.data[881:882])

class FileAttr(object):
    def __init__(self, flags):
        self.flags = flags

    def _flag(bit, doc):
        "helper for bit flag boilerplate"
        def getter(self):
            return True if (self.flags & (1<<bit)) else False
        return property(getter, doc=doc)

    owner_read = _flag( 0, "Owner can read")
    owner_exec = _flag( 2, "Owner can execute")
    group_read = _flag( 4, "Group can read")
    group_exec = _flag( 6, "Group can execute")
    world_read = _flag( 8, "Anyone can read")
    world_exec = _flag(10, "Anyone can execute")
    cdda       = _flag(14, "File is CD-DA")
    directory  = _flag(15, "File is directory")

class File(object):
    def __init__(self, name, attr_size, first_lbn, size, creation_date, flags, interleave_a, interleave_b, album_idx, owner, attributes, number):
        self.name          = name
        self.attr_size     = attr_size
        self.first_lbn     = first_lbn
        self.size          = size
        self.creation_date = creation_date
        self.flags         = flags
        self.interleave_a  = interleave_a
        self.interleave_b  = interleave_b
        self.album_idx     = album_idx
        self.owner         = owner
        self.attributes    = attributes
        self.number        = number

class Directory(object):
    def __init__(self, name, attr_size, sector, parent):
        self.name       = name
        self.attr_size  = attr_size
        self.sector     = sector
        self.parent     = parent

        # read actual sector
        self.contents = []
        offset = 0
        while True:
            file_record_length = number(sector.data[offset+ 0:offset+ 1])
            if file_record_length == 0:
                break

            file_attr_size     = number(sector.data[offset+ 1:offset+ 2])
            file_first_lbn     = number(sector.data[offset+ 6:offset+10])
            file_size          = number(sector.data[offset+14:offset+18])
            file_creation_date = dir_datetime(sector.data[offset+18:offset+24])
            file_flags         = number(sector.data[offset+25:offset+26])
            file_interleave_a  = number(sector.data[offset+26:offset+27])
            file_interleave_b  = number(sector.data[offset+27:offset+28])
            file_album_idx     = number(sector.data[offset+30:offset+32])
            file_name_size     = number(sector.data[offset+32:offset+33])

            file_name          = string(sector.data[offset+33:offset+33+file_name_size])

            file_owner         = number(sector.data[offset+33+file_name_size:offset+37+file_name_size])
            file_attributes    = number(sector.data[offset+37+file_name_size:offset+39+file_name_size])
            file_number        = number(sector.data[offset+41+file_name_size:offset+42+file_name_size])

            f = File(file_name, file_attr_size, file_first_lbn, file_size, file_creation_date, file_flags, file_interleave_a,
                     file_interleave_b, file_album_idx, file_owner, FileAttr(file_attributes), file_number)

            self.contents.append(f)

            offset += file_record_length 

    def __getitem__(self, key):
        return self.contents[key]

    def __iter__(self):
        return iter(self.contents)

class PathTable(object):
    def __init__(self, sector, size):
        self.directories = []
        self.size = size
        offset = 0
        while offset < self.size:
            name_size  = number(sector.data[offset+0:offset+1])
            attr_size  = number(sector.data[offset+1:offset+2])
            dir_addr   = number(sector.data[offset+2:offset+6])
            parent_dir = number(sector.data[offset+6:offset+8])
            name       = string(sector.data[offset+8:offset+8+name_size])

            self.directories.append(Directory(name, attr_size, sector.disc.block(dir_addr), parent_dir))
            offset += 8+name_size + (name_size%2)   # last term is padding byte if name size is uneven

    def __getitem__(self, key):
        return self.directories[key]

    def __iter__(self):
        return iter(self.directories)

class Disc(object):
    HEADER_LEN = 16
    FIRST_DISCLABEL_IDX = 16

    def __init__(self, image_file, headers=False):
        "Create a disc image object from an image file. Does not immediately start processing it."
        self.image_file = mmap.mmap(image_file.fileno(), 0, access=mmap.ACCESS_READ)
        self.sectors = []
        self.disclabels = []
        self.block_offset = None
        self.headers = headers

    def read(self):
        "Read the basic info from the disc image"
        self.read_sectors()
        self._find_disclabel()

    def read_sectors(self):
        offset = Disc.HEADER_LEN if self.headers else 0
        while offset < self.image_file.size():
            new_sector = Sector(self, offset)
            offset += (Sector.FULL_SIZE+Disc.HEADER_LEN) if self.headers else Sector.FULL_SIZE
            self.sectors.append(new_sector)

    def _find_disclabel(self):
        for idx, sector in enumerate(self.sectors):
            # all data sectors until terminator are disc labels
            if sector.subheader.data:
                dl = DiscLabel(sector)
                if self.block_offset is None:
                    self.block_offset = idx - Disc.FIRST_DISCLABEL_IDX

                if dl.type == DiscLabel.TERMINATOR:
                    break
                else:
                    self.disclabels.append(dl)

        else:
            if len(self.disclabels) == 0:
                raise RuntimeError("Never found disc label sector in disc image")
            else:
                raise RuntimeError("Never found disc label terminator sector in disc image")

        # find path table
        self.path_tbl = PathTable(self.block(self.disclabels[0].path_tbl_addr), self.disclabels[0].path_tbl_size)

    def lbn2sector(self, lbn):
        "Convert a Logical Block Number to a sector index"
        return lbn + self.block_offset

    def sector2lbn(self, sector):
        "Convert a sector index to a Logical Block Number"
        return sector - self.block_offset

    def block(self, lbn):
        "Returns the specified block"
        return self[self.lbn2sector(lbn)]

    def __getitem__(self, key):
        return self.sectors[key]
