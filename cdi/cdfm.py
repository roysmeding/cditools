class CDFM(object):
    """A class mirroring the CD-I Compact Disc File Manager interface for seeking and playing files."""

    # assumed sector size for seeks
    SECTOR_SIZE = 2048

    def __init__(self, file_record):
        """Create a new CDFM instance from a file record. Mirrors the CD-I CDFM I$Open system call."""
        self.file_record = file_record
        self.blocks = file_record.blocks()
        self.channel_mask = 0xFFFFFFFF

    def seek(self, position):
        """Seek to the specified position. Mirrors the CD-I CDFM SS_Seek SetStat function."""

        # refresh iterator
        self.blocks = file_record.blocks()

        for _ in range(position // self.SECTOR_SIZE):
            try:
                next(self.blocks)
            except StopIteration:
                raise RuntimeError('Attempt to seek beyond end of file.')

    def play(self, channel_mask, num_records):
        """Yield blocks from the specified channels for the specified number of records."""
        self.channel_mask = channel_mask

        for block in self.blocks:
            # check channel number
            if ((1 << block.subheader.channel_number) & channel_mask) == 0:
                continue
            
            yield block

            if block.subheader.eor:
                num_records -= 1

            if num_records == 0:
                break
