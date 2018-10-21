import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import cdi
import cdi.cdfm

class Sequencer(object):
    """Common interface for decoder scripts to indicate what to feed to the decoder."""
    def __init__(self, img, decoder):
        self.img = img
        self.decoder = decoder
        self.cdifile = None

    def exec_file(self, infilename):
        print("Reading commands from file '{:s}'".format(infilename))

        with open(infilename, 'r') as f:
            self.decoder.decode(self._inner_exec(f))

    def _inner_exec(self, f):
        for line in f:
            line = line.strip()

            if line.startswith('#'):
                continue

            if line == '':
                continue

            cmd, args = line.split(None, 1)
            args = [ arg.strip() for arg in args.split(',') ]

            if   cmd == 'open':
                filename, = args
                file_record = self.img.get_file(filename)
                self.cdifile = cdi.cdfm.CDFM(file_record)

            elif cmd == 'seek':
                pos, = args
                self.cdifile.seek(int(pos))

            elif cmd == 'output':
                filename, = args
                self.decoder.set_output(filename)

            elif cmd == 'play':
                mask, records = args
                yield from self.cdifile.play(int(mask, 16), int(records))

            else:
                self.decoder.handle_command(cmd, args)

    ARGS_EPILOG = """
        The SPEC parameter consists of an absolute on-disc filename, optionally followed by a channel list, optionally followed by a number of records. These fields are separated by colons (':').

        The channel list consists of one or more channel numbers (0-31) separated by the '+' symbol. If a channel combination is the symbol '*', it consists of all channels.

        All channels in the channel list are combined into a single stream. An empty or missing channel list means each channel is extracted separately.

        If the record number is missing, each record will be extracted as a separate stream. If the record number is '*', all records are extracted as one stream.
        """

    def _read_records(self, filename, records, mask, basename):
        file_record = self.img.get_file(filename)
        self.cdifile = cdi.cdfm.CDFM(file_record)

        if records == '':
            record = 0
            while True:
                self.decoder.set_output('{:s}.rec{:04d}'.format(basename, record))

                for block in self.cdifile.play(mask, 1):
                    yield block
                else:
                    record += 1
                    continue

                break

        else:
            self.decoder.set_output(basename)
            yield from self.cdifile.play(mask, -1 if records == '*' else int(records))

    def _parse_filespec(self, spec):
        parts = spec.split(':')
        if   len(parts) == 1:
            return (*parts, '', '')

        elif len(parts) == 2:
            return (*parts, '')

        elif len(parts) == 3:
            return parts

    def _parse_channelspec(self, channels):
        if channels == '*':
            return 0xFFFFFFFF

        mask = 0x00000000
        for ch in channels.split('+'):
            assert int(ch) < 32
            mask |= 1 << int(ch)

        return mask

    def from_args(self, args):
        if not args.cmdfile is None:
            self.exec_file(args.cmdfile)

        elif len(args.files) > 0:
            for filespec in args.files:
                filename, channels, records = self._parse_filespec(filespec)

                _, basename = filename.rsplit('/', 1)

                if channels == '':
                    for ch in range(32):
                        self.decoder.decode(self._read_records(filename, records, 1 << ch, '{:s}.ch{:02d}'.format(basename, ch)))

                else:
                    mask = self._parse_channelspec(channels)
                    self.decoder.decode(self._read_records(filename, records, mask, '{:s}.ch{:s}'.format(basename, channels)))
