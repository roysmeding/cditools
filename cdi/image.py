import mmap

from .basic_types import *
from .sector import Sector
from .disc_label import DiscLabel
from .path_table import PathTable

class Image(object):
    FIRST_DISCLABEL_IDX = 16

    def __init__(self, filename, headers=False):
        self.headers = headers

        image_file = open(filename, 'rb')
        self.image_file = mmap.mmap(image_file.fileno(), 0, access=mmap.ACCESS_READ)

        self._sector_cache = {}

    @property
    def disc_labels(self):
        if hasattr(self, '_disc_labels'):
            return self._disc_labels

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
    def block_offset(self):
        return self.disc_labels[0].sector.index - Image.FIRST_DISCLABEL_IDX

    @property
    def path_table(self):
        return PathTable(
                self.get_block(self.disc_labels[0].path_table_address),
                self.disc_labels[0].path_table_size
            )

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

    def get_sector(self, idx):
        """Retrieves a sector"""
        if not idx in self._sector_cache:
            self._sector_cache[idx] = Sector(self, idx)
        return self._sector_cache[idx]

    def get_block(self, lbn):
        """Retrieves a sector by its Logical Block Number"""
        return self.get_sector(lbn + self.block_offset)

    def lbn2idx(self, lbn):
        return lbn + self.block_offset

    def get_sectors(self):
        for idx in range(0, self.block_offset + self.disc_labels[0].volume_size):
            yield self.get_sector(idx)
