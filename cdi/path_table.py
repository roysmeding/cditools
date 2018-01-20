from .basic_types import *
from .directory import *

class PathTable(object):
    def __init__(self, sector, size):
        self.sector = sector
        self.directories = []
        self.size = size
        offset = 0

        while offset < self.size:
            new_dir = Directory(self.sector, offset)
            self.directories.append(new_dir)
            offset += new_dir.size
