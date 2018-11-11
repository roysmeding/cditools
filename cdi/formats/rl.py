from .clut import PaletteImage

class RLImage(PaletteImage):
    def _read_data(self, f):
        self.data = b''
        for _ in range(self.height):
            while True:
                byte = f.read(1)
                self.data += byte
                
                if (byte[0] & 0b10000000) != 0:
                    length = f.read(1)
                    self.data += length

                    if length[0] == 0:
                        break

    def decode_byte(self, byte):
        raise NotImplementedError()

    def entries(self):
        data = iter(self.data)
        x, y = 0, 0
        while True:
            byte = next(data, None)
            if byte is None:
                assert x == 0 and y == self.height, 'Premature end of data: expected {:d},{:d} but ended at {:d},{:d}'.format(0, self.height, x, y)
                break

            entries = tuple(self.decode_byte(byte))

            if (byte & 0b10000000) == 0:
                yield from entries
                x += len(entries)

            else:
                count = next(data)
                assert count != 1

                if count == 0:
                    count = self.width - x

                    yield from entries * count

                    y += 1
                    x  = 0
                else:
                    yield from entries * count
                    x += count * len(entries)

class RL7Image(RLImage):
    """A run-length coded palette image with 7-bit (128-color) palette entries"""
    def __init__(self, f, timestamp, width, height, palette):
        assert len(palette) == 128
        super().__init__(f, timestamp, width, height, palette)

    def decode_byte(self, byte):
        yield byte & 0b01111111

class RL3Image(RLImage):
    """A run-length coded palette image with 3-bit (8-color) palette entries"""
    def __init__(self, f, timestamp, width, height, palette):
        assert width  % 2 == 0, 'Width must be a multiple of 2 pixels.'
        assert height % 2 == 0, 'Height must be a multiple of 2 pixels.'
        assert len(palette) == 8

        super().__init__(f, timestamp, width, height)

    def decode_byte(self, byte):
        yield (byte & 0b01110000) >> 4
        yield  byte & 0b00000111
