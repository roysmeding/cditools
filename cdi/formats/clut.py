from .image import Image

class PaletteImage(Image):
    def __init__(self, f, timestamp, width, height, palette):
        super().__init__(f, timestamp, width, height)
        assert isinstance(palette, list)
        self.palette = palette

    def entries(self):
        raise NotImplementedError()

    def palette_data(self):
        for entry in self.palette:
            yield from entry

    def to_pil(self):
        import PIL.Image
        img = PIL.Image.frombytes('P', (self.width, self.height), bytes(self.entries()))
        img.putpalette(self.palette_data())
        return img

class CLUT8Image(PaletteImage):
    """A palette image with 8-bit (256-color) palette entries"""
    def __init__(self, f, timestamp, width, height, palette):
        assert len(palette) == 256
        super().__init__(f, timestamp, width, height, palette)

    def _read_data(self, f):
        return f.read(self.width * self.height)

    def entries(self):
        yield from iter(self.data)

class CLUT7Image(PaletteImage):
    """A palette image with 7-bit (128-color) palette entries"""
    def __init__(self, f, timestamp, width, height, palette):
        assert len(palette) == 128
        super().__init__(f, timestamp, width, height, palette)

    def _read_data(self, f):
        self.data = f.read(self.width * self.height)

    def entries(self):
        for byte in self.data:
            yield byte & 0b01111111

class CLUT4Image(PaletteImage):
    """A palette image with 4-bit (16-color) palette entries"""
    def __init__(self, f, timestamp, width, height, palette):
        assert width  % 2 == 0, 'Width must be a multiple of 2 pixels.'
        assert height % 2 == 0, 'Height must be a multiple of 2 pixels.'
        assert len(palette) == 16

        super().__init__(f, timestamp, width, height, palette)

    def _read_data(self, f):
        self.data = f.read(self.width * self.height // 2)

    def entries(self):
        for byte in self.data:
            yield (byte & 0b11110000) >> 4
            yield  byte & 0b00001111
