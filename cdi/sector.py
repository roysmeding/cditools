from .basic_types import *

class Subheader(object):
    """A sector sub-header"""
    SIZE = 8

    def __init__(self, data):
        self.file_number    = number(data[0:1])
        self.channel_number = number(data[1:2])
        self.submode_raw    = number(data[2:3])
        self.coding_raw     = number(data[3:4])

        if self.audio:
            self.coding = AudioCoding(self.coding_raw)

        elif self.video:
            if self.coding_raw & (1 << 7):
                # The Application Specific Coding Flag (ASCF) is set.
                # This means the coding information is unknown.
                self.coding = None
            else:
                self.coding = VideoCoding(self.coding_raw)

        else:
            self.coding = None

    def _smf(self, bit):
        """Convert submode flag to boolean"""

        return True if (self.submode_raw & (1 << bit)) else False

    @property
    def eor(self):
        """End Of Record (EOR)


        True for the last sector of a logical record, False otherwise.
        The use of the EOR bit is only mandatory for real-time records.
        """

        return self._smf(0)

    @property
    def video(self):
        """True for video sectors, False otherwise."""

        return self._smf(1)

    @property
    def audio(self):
        """True for audio sectors, False otherwise.

        Audio sectors can only be Form 2."""

        return self._smf(2)

    @property
    def data(self):
        """True for data sectors, False otherwise.

        Data sectors can only be Form 1."""

        return self._smf(3)

    @property
    def empty(self):
        """True when sector has no type."""
        return not (self.video or self.audio or self.data)

    @property
    def trigger(self):
        """True when sector causes interrupt when read.
        
        Used to synchronize the application with various coding information,
        like visuals to audio, in real time.
        """

        return self._smf(4)

    @property
    def form2(self):
        """True for all Form 2 sectors, False otherwise.
        
        Form 2 sectors contain more data, but less error correction."""

        return self._smf(5)

    @property
    def form1(self):
        """True for all Form 1 sectors, False otherwise.
        
        Form 1 sectors contain less data, but more error correction."""

        return not self.form2

    @property
    def realtime(self):
        """Real-Time Sector
        
        When True, the data has to be processed without interrupting the
        real-time behavior of the CD-I system. For example, audio sectors have
        to be transferred to the ADPCM decoder in real time in order to avoid
        the overflow or underflow of data.
        """

        return self._smf(6)

    @property
    def eof(self):
        """True for the last sector of a file, false for all other sectors."""

        return self._smf(7)

class Coding(object):
    def __init__(self, coding_raw):
        self.coding_raw = coding_raw

    def _flag(self, bit):
        return True if (self.coding_raw & (1 << bit)) else False

    def _field(self, start, size):
        return (self.coding_raw >> start) & ((1 << size) - 1)


class AudioCoding(Coding):
    """The coding flags defined for an audio sector."""

    def __init__(self, coding_raw):
        super().__init__(coding_raw)

    @property
    def mono(self):
        return self._field(0, 2) == 0

    @property
    def stereo(self):
        return self._field(0, 2) == 1


    SAMPLE_RATE_37800 = 0
    """Sample rate is 37.8 kHz."""

    SAMPLE_RATE_18900 = 1
    """Sample rate is 18.9 kHz."""

    @property
    def sample_rate(self):
        return self._field(2, 2)


    SAMPLE_DEPTH_4BIT = 0
    """4 bits per sample."""

    SAMPLE_DEPTH_8BIT = 1
    """8 bits per sample."""

    @property
    def sample_depth(self):
        return self._field(4, 2)

    @property
    def emphasis(self):
        """True if a CD-DA pre-emphasis filter was applied during recording."""
        return self._flag(6)


class VideoCoding(Coding):
    """The coding flags defined for a video sector."""

    def __init__(self, coding_raw):
        super().__init__(coding_raw)


    ENCODING_CLUT4    =  0
    ENCODING_CLUT7    =  1
    ENCODING_CLUT8    =  2
    ENCODING_RL3      =  3
    ENCODING_RL7      =  4
    ENCODING_DYUV     =  5
    ENCODING_RGB555_L =  6
    ENCODING_RGB555_U =  7
    ENCODING_QHY      =  8

    ENCODING_MPEG     = 15

    @property
    def encoding(self):
        """How the image data is encoded."""
        return self._field(0, 4)


    RESOLUTION_NORMAL = 0
    RESOLUTION_DOUBLE = 1
    RESOLUTION_HIGH   = 3

    @property
    def resolution(self):
        return self._field(4, 2)


    @property
    def odd_lines(self):
        """If error concealment is to be used, this flag indicates whether the
        sector contains the odd lines of the image. If error concealment is not
        to be used, returns False."""

        return self._flag(6)

    @property
    def even_lines(self):
        """If error concealment is to be used, this flag indicates whether the
        sector contains the even lines of the image. If error concealment is
        not to be used, returns True."""

        return not self.odd_lines


class Sector(object):
    CD_HEADER_SIZE = 16         # CD sector header size

    def __init__(self, image, index):
        self.image = image

        if self.image.headers:
            self.full_size = 2336 + Sector.CD_HEADER_SIZE
        else:
            self.full_size = 2336

        if index > (image.image_file.size() // self.full_size):
            raise EOFError("EOF on image")

        self.index = index

        self.offset = self.index * self.full_size + (Sector.CD_HEADER_SIZE if self.image.headers else 0)

        self.subheader = Subheader(self.image.image_file[self.offset:self.offset + Subheader.SIZE])

        if self.subheader.form1:
            self.data_size = 2048
        else:
            self.data_size = 2324

    def get_data(self, start=None, end=None):
        _start = self.offset + Subheader.SIZE
        _end = _start + self.data_size

        if start is None:
            return self.image.image_file[_start:_end]

        elif end is None:
            return self.image.image_file[_start:_end][start]

        else:
            return self.image.image_file[_start:_end][start:end]
