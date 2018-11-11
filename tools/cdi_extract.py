#!/usr/bin/env python3

import argparse
import sys
import os
import json
import tempfile
import subprocess
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

class Extractor(object):
    def __init__(self, read, recipe):
        self.infn = read['file'] if 'file' in read else None
        self.outfn = None
        self.outfile = None

        if 'channel' in read:
            self.channel = str(read['channel'])
        elif 'channels' in read:
            self.channel = '+'.join((str(ch) for ch in read['channels']))
        else:
            self.channel = '+'.join((str(ch) for ch in range(32)))
            
        self.record = 0

        if 'postprocess' in read:
            if isinstance(read['postprocess'], str):
                assert read['postprocess'] in recipe['postprocess']
                self.postprocess = recipe['postprocess'][read['postprocess']]
            else:
                self.postprocess = read['postprocess']
        else:
            self.postprocess = None

    def pre_close(self):
        pass

    def close(self):
        if self.outfile is None:
            return

        self.pre_close()
        self.outfile.close()
        if not self.postprocess is None:
            params = { "input": self.outfile.name, "output": self.outfn }
            try:
                os.makedirs(os.path.dirname(self.outfn), exist_ok=True)
                subprocess.run([ arg.format(**params) for arg in self.postprocess ]).check_returncode()

            finally:
                os.remove(self.outfile.name)

        self.outfn = None

    def post_open(self, outfile):
        pass

    def set_output(self, filename):
        if self.outfile is None or self.outfn != filename:
            self.close()

            self.outfn = filename
            if self.postprocess is None:
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                self.outfile = open(filename, 'wb')
            else:
                self.outfile = tempfile.NamedTemporaryFile('wb', delete=False)

            self.post_open(filename)

            return True
        else:
            return False

    def write(self, data):
        assert not self.outfile is None
        self.outfile.write(data)

    def get_output_params(self):
        return {
            "file":    self.infn.rsplit('/', 1)[1] if not self.infn is None else None,
            "path":    self.infn,
            "channel": self.channel,
            "record":  self.record,
        }

    def get_output_filename(self):
        raise NotImplementedError()

    def _extract(self, blocks, file_record):
        raise NotImplementedError()

    def _count_records(self, blocks):
        for block in blocks:
            yield block
            if block.subheader.eor:
                self.record += 1

    def extract(self, blocks, file_record):
        yield from self._extract(self._count_records(blocks), file_record)

class RawExtractor(Extractor):
    """Extractor that just outputs the file as-is on disc, minus sector header/subheader and such."""

    def __init__(self, read, recipe):
        super().__init__(read, recipe)
        self.output = read['output']

    def get_output_filename(self):
        return self.output.format(**self.get_output_params())

    def _extract(self, blocks, file_record):        
        bytes_left = file_record.size

        for block in blocks:
            if bytes_left <= 0:
                break

            output_filename = self.get_output_filename()

            if self.set_output(output_filename):
                yield output_filename
            
            output_data = block.get_data()

            if bytes_left >= 2048:
                self.write(output_data)
                bytes_left -= 2048
            else:
                self.write(output_data[:bytes_left])
                bytes_left = 0

class MPEGExtractor(RawExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    @staticmethod
    def _is_mpeg_video(block):
        return block.subheader.video and block.subheader.coding_raw == 0b00001111

    @staticmethod
    def _is_mpeg_audio(block):
        return block.subheader.audio and block.subheader.coding_raw == 0b01111111

    @staticmethod
    def _is_mpeg_sp(block):
        return block.subheader.video and block.subheader.coding_raw == 0b00011111

    def _mpeg_blocks(self, blocks):
        for block in blocks:
            if self._is_mpeg_video(block) or self._is_mpeg_audio(block) or self._is_mpeg_sp(block):
                yield block

    def _extract(self, blocks, file_record):
        yield from super()._extract(self._mpeg_blocks(blocks), file_record)

import array
from cdi.formats.image import ImageDecoder
from cdi.sector import VideoCoding

from palette import PALETTE8, PALETTE16, PALETTE128, PALETTE256

class ImageExtractor(Extractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

        assert 'images' in read
        if isinstance(read['images'], list):
            self.imagesets = read['images']
        else:
            self.imagesets = [ read['images'] ]

        self.output = None
        self.image = None

    def get_output_params(self):
        params = super().get_output_params()
        params.update(image=self.image)
        return params

    def get_output_filename(self):
        return self.output.format(**self.get_output_params())

    def setup_decoder(self, imageset):
        self.decoder.size(imageset['size']['w'], imageset['size']['h'])
        if 'packed' in imageset and imageset['packed'] == True:
            self.decoder.packed = True

    def create_decoder(self, blocks):
        raise NotImplementedError()
    
    def write(self, image):
        image.to_pil().save(self.outfile)

    def _extract(self, blocks, file_record):
        self.decoder = self.create_decoder(blocks)

        for imageset in self.imagesets:
            self.output = imageset['output']
            self.setup_decoder(imageset)

            if 'count' in imageset:
                count = imageset['count']

            else:
                count = 1

            for self.image in range(count):
                output_filename = self.get_output_filename()

                if self.set_output(output_filename):
                    yield output_filename

                self.write(self.decoder.decode_image())

class DYUVExtractor(ImageExtractor):
    DEFAULT_YUV = (16, 128, 128)

    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_DYUV:
                    yield block

        from cdi.formats.dyuv import DYUVImage
        return ImageDecoder(DYUVImage, video_blocks(blocks))

    def get_yuv(self, imageset):
        height = imageset['size']['h']
        if 'yuv' in imageset:
            yuv = imageset['yuv']
            if isinstance(yuv, list):
                assert len(yuv) == height
                return [ (line['y'], line['u'], line['v']) for line in yuv ]
            else:
                return [ (yuv['y'], yuv['u'], yuv['v']) for _ in range(height) ]
        else:
            return [ self.DEFAULT_YUV for _ in range(height) ]

    def setup_decoder(self, imageset):
        super().setup_decoder(imageset)
        self.decoder.set_params(yuv=self.get_yuv(imageset))

class PaletteImageExtractor(ImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        raise NotImplementedError()

    def get_palette(self, imageset):
        if 'palette' in imageset:
            return imageset['palette']
        else:
            return self.default_palette()

    def setup_decoder(self, imageset):
        super().setup_decoder(imageset)
        self.decoder.set_params(palette=self.get_palette(imageset))

class CLUT8Extractor(PaletteImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        return PALETTE256

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_CLUT8:
                    yield block

        from cdi.formats.clut import CLUT8Image
        return ImageDecoder(CLUT8Image, video_blocks(blocks))

class CLUT7Extractor(PaletteImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        return PALETTE128

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_CLUT7:
                    yield block

        from cdi.formats.clut import CLUT7Image
        return ImageDecoder(CLUT7Image, video_blocks(blocks))

class CLUT4Extractor(PaletteImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        return PALETTE16

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_CLUT4:
                    yield block

        from cdi.formats.clut import CLUT4Image
        return ImageDecoder(CLUT4Image, video_blocks(blocks))

class RL7Extractor(PaletteImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        return PALETTE128

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_RL7:
                    yield block

        from cdi.formats.rl import RL7Image
        return ImageDecoder(RL7Image, video_blocks(blocks))

class RL3Extractor(PaletteImageExtractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

    def default_palette(self):
        return PALETTE8

    def create_decoder(self, blocks):
        def video_blocks(blocks):
            for block in blocks:
                if block.subheader.video and block.subheader.coding.encoding == VideoCoding.ENCODING_RL3:
                    yield block

        from cdi.formats.rl import RL3Image
        return ImageDecoder(RL3Image, video_blocks(blocks))

import wave
from cdi.formats.audio import AudioDecoder
from cdi.sector import AudioCoding

class ADPCMExtractor(Extractor):
    def __init__(self, read, recipe):
        super().__init__(read, recipe)

        self.output = read['output']
        self.coding = read['coding'] if 'coding' in read else {}

        self.decoder = AudioDecoder()

    def get_output_filename(self):
        return self.output.format(**self.get_output_params())

    def pre_close(self):
        self.wavfile.close()    

    def post_open(self, filename):
        self.wavfile = wave.open(self.outfile)
        self.wavfile.setnchannels(2 if self.decoder.stereo else 1)
        self.wavfile.setsampwidth(2)
        self.wavfile.setframerate(self.decoder.sample_rate)

    def write(self, data):
        self.wavfile.writeframes(data)

    def _extract(self, blocks, file_record):
        for block in blocks:
            if not block.subheader.audio:
                # skip block
                continue

            if 'layout' in self.coding:
                if block.subheader.coding.layout != self.coding['layout']:
                    continue

            if 'rate' in self.coding:
                if block.subheader.coding.sample_rate != self.coding['rate']:
                    continue

            if 'depth' in self.coding:
                if block.subheader.coding.sample_depth != self.coding['depth']:
                    continue

            # process the block first, we might need initialization data to determine e.g. output parameters
            output_data = self.decoder.decode_block(block)

            output_filename = self.get_output_filename()

            if self.set_output(output_filename):
                yield output_filename

            self.write(output_data)

EXTRACTOR_MAP = {
    'raw':   RawExtractor,
    'mpeg':  MPEGExtractor,
    'dyuv':  DYUVExtractor,
    'clut8': CLUT8Extractor,
    'clut7': CLUT7Extractor,
    'clut4': CLUT4Extractor,
    'rl7':   RL7Extractor,
    'rl3':   RL3Extractor,
    'adpcm': ADPCMExtractor,
}

# parse command-line arguments
parser = argparse.ArgumentParser(
        description='Extracts, decodes and processes from a CD-I disc image based on a \'recipe\' file.',
        epilog='The recipe file is a JSON file containing instructions on what to exact and using what parameters.'
    )

parser.add_argument('recipe', help='Recipe file to read')

args = parser.parse_args()

print("Opening recipe file '{:s}'".format(args.recipe))
with open(args.recipe, 'r') as recipefile:
    recipe = json.load(recipefile)

if 'author' in recipe:
    print("\tAuthor: {:s}\n".format(recipe['author']))

raw = 'raw' in recipe and recipe['raw']

image_filename = os.path.join(os.path.dirname(args.recipe), recipe['disc'])

def create_extractor(read):
    assert read['extractor'] in EXTRACTOR_MAP
    return EXTRACTOR_MAP[read['extractor']](read, recipe)

def get_channel_mask(read):
    assert not ('channel' in read and 'channels' in read)

    if 'channel' in read:
        return 1 << read['channel']

    elif 'channels' in read:
        mask = 0x00000000
        for channel in read['channels']:
            mask |= 1 << channel
        return mask

    else:
        return 0xFFFFFFFF

if raw:
    print("Opening disc image file '{:s}' in raw mode".format(image_filename))
    img = cdi.RawImage(image_filename)
else:
    print("Opening disc image file '{:s}'".format(image_filename))
    img = cdi.Image(image_filename)

class ReadIterator(object):
    def __init__(self, source, channel_mask, records):
        self.source = source
        self.channel_mask = channel_mask
        self.records = records

    def __iter__(self):
        cdfm = cdi.CDFM(self.source)
        return cdfm.play(self.channel_mask, self.records)

    def __len__(self):
        count = 0
        for block in self:
            count += 1
        return count

for read_idx, read in enumerate(recipe['reads']):
    if isinstance(read, str):
        # strings can be used basically as comments -- print them to stdout too
        print(read)
        continue

    try:
        channel_mask = get_channel_mask(read)
        if raw:
            file = None
            source = img
        else:
            source = file = img.get_file(read['file'])

        records = read['records'] if 'records' in read else -1

        bar = tqdm(ReadIterator(source, channel_mask, records), desc='Read {:d}/{:d}'.format(read_idx, len(recipe['reads'])), unit='block')

        extractor = create_extractor(read)
        try:
            for output in extractor.extract(bar, file):
                bar.write("Writing output file '{:s}'".format(output))
        finally:
            extractor.close()
            bar.close()

    except Exception as e:
        raise e
