from .image import RawImage

class CDFM(object):
    """A class mirroring the CD-I Compact Disc File Manager interface for seeking and playing files."""

    # assumed sector size for seeks
    SECTOR_SIZE = 2048

    def __init__(self, file):
        """Create a new CDFM instance from a file record. Mirrors the CD-I CDFM I$Open system call.
        If file is an Image or RawImage, open the entire disc.
        """
        self.file = file
        self.reset()

    def reset(self):
        if isinstance(self.file, RawImage):
            self.blocks = self.file.get_sectors()
        else:
            self.blocks = self.file.blocks()

    def seek(self, position):
        """Seek to the specified position. Mirrors the CD-I CDFM SS_Seek SetStat function."""

        self.reset()

        for _ in range(position // self.SECTOR_SIZE):
            try:
                next(self.blocks)
            except StopIteration:
                raise RuntimeError('Attempt to seek beyond end of file.')

    def play(self, channel_mask, num_records):
        """Yield blocks from the specified channels for the specified number of records."""
        self.channel_mask = channel_mask

        for i, block in enumerate(self.blocks):
            # check channel number
            if ((1 << block.subheader.channel_number) & channel_mask) == 0:
                continue
            
            yield block

            if block.subheader.eor:
                num_records -= 1

            if num_records == 0:
                break
