import struct
import numpy as np

import PIL.Image

from ..sector import VideoCoding

class DYUVStream(object):
    """Decodes CD-I DYUV video data from a disc file"""

    # DPCM quantization table
    QUANT_TABLE = [
              0,
              1,
              4,
              9,
             16,
             27,
             44,
             79,
            128,
            177,
            212,
            229,
            240,
            247,
            252,
            255
        ]

    WIDTH  = 384
    HEIGHT = 240

    def __init__(self, blocks):
        """Create a new decoder stream.

        Arguments:
            - blocks: an iterator that yields the blocks to decode
        """

        self.blocks = blocks
        try:
            self.cur_block = next(self.blocks)
            self.block_pos = 0
            self.eof = False

        except StopIteration:
            self.cur_block = None
            self.block_pos = None
            self.eof = True

    def decode_image(self, initial_values):
        """Decodes a single image.

        initial_values is a function that, given a line number (y coordinate),
        returns a tuple (Y, U, V) of initial values for the Y U V DPCM
        decoding. They are specified by the CD-I program and can be stored in
        an arbitrary manner.
        """

        if self.block_pos != 0:
            # each image starts in a new sector
            try:
                self.cur_block = next(self.blocks)
                self.block_pos = 0

            except StopIteration:
                self.cur_block = None
                self.block_pos = None
                self.eof = True

                raise ValueError("No more image sectors left in file")

        while self.cur_block.get_data(self.block_pos, self.block_pos+2) == '\x00\x00':
            self.block_pos += 2

        Y = []
        U = []
        V = []

        def dpcm(prev, delta):
            return (prev + self.QUANT_TABLE[delta]) % 256

        # used for upsampling the half-resolution U and V components
        xa = np.linspace(0, self.WIDTH-2, self.WIDTH//2)
        xr = np.linspace(0, self.WIDTH-1, self.WIDTH)

        for y in range(self.HEIGHT):
            Yline = []
            Uline = []
            Vline = []

            Yprev, Uprev, Vprev = initial_values(y)

            for x in range(self.WIDTH//2):
                B0, B1 = struct.unpack_from('BB', self.cur_block.get_data(self.block_pos, self.block_pos+2))
                self.block_pos += 2

                dU, dY0 = (B0 & 0xF0) >> 4, B0 & 0x0F
                dV, dY1 = (B1 & 0xF0) >> 4, B1 & 0x0F

                Yprev = dpcm(Yprev, dY0)
                Yline.append(Yprev)

                Uprev = dpcm(Uprev, dU)
                Uline.append(Uprev)

                Yprev = dpcm(Yprev, dY1)
                Yline.append(Yprev)

                Vprev = dpcm(Vprev, dV)
                Vline.append(Vprev)

                if self.block_pos >= self.cur_block.data_size:
                    try:
                        self.cur_block = next(self.blocks)
                        self.block_pos = 0

                    except StopIteration:
                        self.cur_block = None
                        self.block_pos = None
                        self.eof = True

                        raise ValueError("Unexpected EOF in middle of image")


            Y.append(Yline)
            U.append(np.interp(xr, xa, Uline))
            V.append(np.interp(xr, xa, Vline))

        Y = np.array(Y, dtype='uint8')
        U = np.array(U, dtype='uint8')
        V = np.array(V, dtype='uint8')

        return PIL.Image.fromarray(np.transpose([Y,U,V], [1,2,0]), mode='YCbCr')
