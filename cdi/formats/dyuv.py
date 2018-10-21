import struct
import numpy as np

import PIL.Image

from ..sector import VideoCoding

class DYUVDecoder(object):
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

    def __init__(self, blocks):
        """Create a new decoder."""

        self.blocks = blocks
        self.iv_func = lambda y: (0, 0, 0)

        self.width  = 384
        self.height = 240

        self._next_block()

    def initial_values(self, iv_func):
        self.iv_func = iv_func

    def size(self, w, h):
        self.width  = w
        self.height = h

    def _next_block(self):
        try:
            self.cur_block = next(self.blocks)
            self.block_pos = 0
            self.eof = False

        except StopIteration:
            self.eof = True

    def decode_image(self):
        """Decodes a single image."""

        Y = []
        U = []
        V = []

        def dpcm(prev, delta):
            return (prev + self.QUANT_TABLE[delta]) % 256

        # used for upsampling the half-resolution U and V components
        xa = np.linspace(0, self.width-2, self.width//2)
        xr = np.linspace(0, self.width-1, self.width)

        for y in range(self.height):
            Yline = []
            Uline = []
            Vline = []

            Yprev, Uprev, Vprev = self.iv_func(y)

            for x in range(self.width//2):
                B0, B1 = struct.unpack_from('BB', self.cur_block.get_data(self.block_pos, self.block_pos + 2))
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
                    self._next_block()

                    if self.eof:
                        raise ValueError("Unexpected EOF in middle of image")

            Y.append(Yline)
            U.append(np.interp(xr, xa, Uline))
            V.append(np.interp(xr, xa, Vline))

        # images only ever start at the start of a block so move to the next one.
        if self.block_pos > 0:
            self._next_block()

        Y = np.array(Y, dtype='uint8')
        U = np.array(U, dtype='uint8')
        V = np.array(V, dtype='uint8')

        return PIL.Image.fromarray(np.transpose([Y,U,V], [1,2,0]), mode='YCbCr')

    def decode_all_images(self):
        while not self.eof:
            yield self.decode_image()
