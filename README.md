# Overview
This repository contains tools for dealing with the Philips CD-I disk format,
also known as 'Green Book'. It contains tools for extracting file system data
from the image, and for decoding audio and image tracks.

# Files
The following files are currently contained in this repository.

## Base library files
* cdi.py
    This is the main library for dealing with the CD-I disk data. It contains representations of discs, sectors, files etc.

## Scripts for dumping/viewing disk image information
* cdi_dump_files.py
    Splits a CD-I disk image into separate files according to the file system information contained within.
* cdi_dump_sectors.py
    Extracts only sectors matching certain properties from a CD-I disk image.
* cdi_ls.py
    Lists all directories, files, records and channels in a CD-I disk image.
* cdi_sectors.py
    Pretty-prints all sectors in a CD-I disk image.

## Scripts for decoding audio data
* cdi_decode_audio.py
    Decodes audio sectors as described in the Green Book specification.

## Scripts for decoding video data
Unfortunately, the video formats generally require out-of-band data like pallette values, which each game can store differently.
In addition, some games seem to employ weird tricks to wring more performance out of the video hardware. These things mean it's basically impossible to make a general purpose image decoder.

* cdi_decode_clut7.py
    Decodes CLUT7 image sectors.
* cdi_decode_dyuv.py
    Decodes DYUV image sectors.
