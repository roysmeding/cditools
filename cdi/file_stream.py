import io

class FileStream(object):
    def __init__(self, file_record, record=None, channel=None):
        self.file_record = file_record
        self.image = self.file_record.sector.image
        self.file_pos = 0

        self.rt = not ((record is None) and (channel is None))
        
        self.blocks = self.file_record.get_blocks(record, channel)
        self.cur_block = next(self.blocks)
        self.cur_block_pos = 0
        self.eof = False

    def read(self, n=-1):
        buf = b''

        if not self.rt:
            n_left = self.file_record.size - self.file_pos
            if (n == -1) or (n > n_left):
                n = n_left

        while (n == -1) or (self.cur_block_pos + n) >= self.cur_block.data_size:
            buf += self.cur_block.get_data(self.cur_block_pos, self.cur_block.data_size)

            n_read = self.cur_block.data_size - self.cur_block_pos
            self.file_pos += n_read

            if n != -1:
                n -= n_read

            try:
                self.cur_block = next(self.blocks)
                self.cur_block_pos = 0

            except StopIteration:
                self.eof = True
                break
 
        if not self.rt:
            if self.file_pos >= self.file_record.size:
                self.eof = True

        if n > 0:
            if self.eof:
                return buf

            buf += self.cur_block.get_data(self.cur_block_pos, self.cur_block_pos+n)
            self.cur_block_pos += n
            self.file_pos += n
       
        return buf

    def read_block(self):
        return self.read(self.cur_block.data_size - self.cur_block_pos)
