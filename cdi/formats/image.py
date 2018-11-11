class Image(object):
    """A single image, created from a Vaguely File-Like Object™"""
    def __init__(self, f, timestamp, width, height):
        self.timestamp = timestamp
        self.width = width
        self.height = height
        self._read_data(f)

    def _read_data(self, f):
        raise NotImplementedError()

    @property
    def size(self):
        return len(self.data)

    def to_pil(self):
        raise NotImplementedError()

class ImageDecoder(object):
    """Decodes image data from a disc file"""

    def __init__(self, image_type, blocks):
        """Create a new decoder."""

        self.image_type = image_type
        self.blocks = blocks

        self.width  = None
        self.height = None
        self.packed = False
        self.params = {}

        self._next_block()

    def set_params(self, **params):
        self.params = params

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

    def read(self, n):
        buf = b''

        while n > 0:
            if self.eof:
                raise ValueError("Unexpected EOF in middle of image: {:d} bytes left".format(n))

            blockleft = self.cur_block.data_size - self.block_pos
            if blockleft <= n:
                buf += self.cur_block.get_data(self.block_pos, self.cur_block.data_size)
                n -= blockleft
                self._next_block()

            else:
                buf += self.cur_block.get_data(self.block_pos, self.block_pos + n)
                self.block_pos += n
                n = 0

        return buf

    def decode_image(self):
        img = self.image_type(self, None, self.width, self.height, **self.params)

        if not self.packed and self.block_pos > 0:
            self._next_block()
        
        return img
