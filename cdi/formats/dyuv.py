import struct
import array

from ..sector import VideoCoding

from .image import Image

class DYUVImage(Image):
    # DPCM quantization table
    QUANT_TABLE = [
          0,   1,   4,   9,
         16,  27,  44,  79,
        128, 177, 212, 229,
        240, 247, 252, 255
    ]

    def __init__(self, f, timestamp, width, height, yuv):
        assert width  % 2 == 0, 'Width must be a multiple of 2 pixels.'
        assert height % 2 == 0, 'Height must be a multiple of 2 pixels.'

        super().__init__(f, timestamp, width, height)

        self.initial_values = yuv

    def _read_data(self, f):
        self.data = f.read(self.width * self.height)

    def to_yuv422p(self):
        """Returns the image data as YUV420p with 8-bit components, which is basically the native pixel format (with delta coding removed)."""
        Y = array.array('B', (0 for _ in range(self.width * self.height     )))
        U = array.array('B', (0 for _ in range(self.width * self.height // 2)))
        V = array.array('B', (0 for _ in range(self.width * self.height // 2)))

        for y in range(self.height):
            Yprev, Uprev, Vprev = self.initial_values[y]

            for x in range(0, self.width, 2):
                idx = y * self.width + x
                B0, B1 = struct.unpack('BB', self.data[idx:idx + 2])

                dU, dY0 = (B0 & 0xF0) >> 4, B0 & 0x0F
                dV, dY1 = (B1 & 0xF0) >> 4, B1 & 0x0F

                Yprev = (Yprev + self.QUANT_TABLE[dY0]) & 0xFF
                Y[idx] = Yprev

                Yprev = (Yprev + self.QUANT_TABLE[dY1]) & 0xFF
                Y[idx + 1] = Yprev

                Uprev = (Uprev + self.QUANT_TABLE[dU ]) & 0xFF
                U[idx // 2] = Uprev

                Vprev = (Vprev + self.QUANT_TABLE[dV ]) & 0xFF
                V[idx // 2] = Vprev

        return (Y, U, V)

    def to_yuv444p(self):
        """Returns the image data as YUV444p with 8-bit components, i.e. with U and V interpolated to the same resolution as Y."""
        Y, U, V = self.to_yuv422p()

        Uout = array.array('B', (0 for _ in range(self.width * self.height)))
        Vout = array.array('B', (0 for _ in range(self.width * self.height)))

        for y in range(self.height):
            for x in range(0, self.width, 2):
                idx = y * self.width + x

                Uout[idx] = U[idx // 2]
                if x < self.width - 2:
                    Uout[idx + 1] = (U[idx // 2] + U[(idx // 2) + 1]) // 2
                else:
                    Uout[idx + 1] =  U[idx // 2]

                Vout[idx] = V[idx // 2]
                if x < self.width - 2:
                    Vout[idx + 1] = (V[idx // 2] + V[(idx // 2) + 1]) // 2
                else:
                    Vout[idx + 1] =  V[idx // 2]

        return Y, Uout, Vout

    def to_pil(self):
        import PIL.Image
        Y, U, V = self.to_yuv444p()
        def _interleave():
            for i in range(len(Y)):
                yield Y[i]
                yield U[i]
                yield V[i]

        return PIL.Image.frombytes('YCbCr', (self.width, self.height), bytes(_interleave())).convert('RGB')
