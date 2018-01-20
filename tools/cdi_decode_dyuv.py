import argparse

# parse command-line arguments
parser = argparse.ArgumentParser(description='Decode DYUV image data from an extracted CD-I video track')
parser.add_argument('input_file',   help='Track file to decode')
parser.add_argument('output_file',  help='Output file name base')

args = parser.parse_args()


