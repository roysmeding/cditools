import mmap

from .basic_types import *
from .sector import Sector, CDHeader
from .disc_label import DiscLabel
from .path_table import PathTable

class RawImage(object):
    """A CD-I disc image that may not have a path label. Only raw sector data is available."""
    FIRST_DISCLABEL_IDX = 16

    def __init__(self, filename):
        image_file = open(filename, 'rb')
        self.image_file = mmap.mmap(image_file.fileno(), 0, access=mmap.ACCESS_READ)

        if self.image_file[:12] == CDHeader.SYNC_FIELD:
            self.headers = True
        else:
            self.headers = False

        if self.headers:
            subheader1 = self.image_file[CDHeader.SIZE    :CDHeader.SIZE + 4]
            subheader2 = self.image_file[CDHeader.SIZE + 4:CDHeader.SIZE + 8]
        else:
            subheader1 = self.image_file[0:4]
            subheader2 = self.image_file[4:8]
        
        if subheader1 != subheader2:
            raise RuntimeError('File does not appear to be a valid CD-I disc image.')

        self._sector_cache = {}

    def get_sector(self, idx):
        """Retrieves a sector"""
        if not idx in self._sector_cache:
            self._sector_cache[idx] = Sector(self, idx)
        return self._sector_cache[idx]

    def get_sectors(self):
        offset = 0
        idx = 0
        while (offset + self.sector_size) < self.image_file.size():
            yield self.get_sector(idx)
            idx += 1
            offset += self.sector_size

    @property
    def sector_size(self):
        if self.headers:
            return 2336 + CDHeader.SIZE
        else:
            return 2336



class Image(RawImage):
    def __init__(self, filename):
        super().__init__(filename)

    @property
    def disc_labels(self):
        if not hasattr(self, '_disc_labels'):
            sector_idx = 0
            self._disc_labels = []

            while True:
                sector = self.get_sector(sector_idx)
                if sector.subheader.data:
                    dl = DiscLabel.create(sector)

                    if dl.type == DiscLabel.TERMINATOR:
                        break
                    else:
                        self._disc_labels.append(dl)

                sector_idx += 1

        return self._disc_labels

    @property
    def block_size(self):
        """Logical block size. This is used for e.g. measuring file sizes."""
        return self.disc_labels[0].block_size

    @property
    def block_offset(self):
        return self.disc_labels[0].sector.index - Image.FIRST_DISCLABEL_IDX

    @property
    def path_table(self):
        return self.disc_labels[0].path_table

    @property
    def root(self):
        """The root directory of the image"""
        for d in self.path_table.directories:
            if d.name == '\x00':
                return d

    def files(self):
        for d in self.path_table.directories:
            for f in d.contents:
                yield f.full_name

    def get_file(self, fname):
        for d in self.path_table.directories:
            for f in d.contents:
                if f.full_name == fname:
                    return f

        return None

    def get_block(self, lbn):
        """Retrieves a sector by its Logical Block Number"""
        return self.get_sector(lbn + self.block_offset)

    def lbn2idx(self, lbn):
        return lbn + self.block_offset
