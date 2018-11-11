#!/usr/bin/env python3

import argparse
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# parse command-line arguments
parser = argparse.ArgumentParser(description='Outputs information from a CD-I disc image as JSON to stdout.')
parser.add_argument('image_file',  help='Image file to open')

class JSONEncoder(json.JSONEncoder):
    def __init__(self):
        super().__init__(indent=4)

    def encode_directory(self, d):
        return {
            'name':     d.name,
            'path':     d.full_name,
            'contents': d.contents,
        }

    def encode_attributes(self, a):
        result = []

        for attr in [ 'owner_read', 'owner_exec', 'group_read', 'group_exec', 'world_read', 'world_exec', 'cdda', 'directory' ]:
            if getattr(a, attr):
                result.append(attr)

        return result

    def encode_file(self, f):
        info = {
            'name': f.name,
            'path': f.full_name,
            'size': f.size,
            'creation_date': f.creation_date,
            'owner': { 'user': f.owner_user, 'group': f.owner_group },
            'attributes': self.encode_attributes(f.attributes),
            'hidden': f.flags.hidden,
        }

        if f.album_idx != 0:
            info['album'] = f.album_idx

        if f.interleave != (0, 0):
            info['interleave'] = list(f.interleave)

        return info

    def encode_image(self, img):
        return {
            'disc_labels': img.disc_labels,
        }

    def encode_disc_label(self, dl):
        return {
            'volume_id':  dl.volume_id,
            'version':    dl.version,
            'system_id':  dl.system_id,
            'num_blocks': dl.volume_size,

            'album': {
                'id':    dl.album_id,
                'index': dl.album_idx,
                'count': dl.album_size,
            },

            'publisher':     dl.publisher_id,
            'data_preparer': dl.data_preparer,

            'dates': {
                'created':   dl.created_date,
                'modified':  dl.modified_date,
                'effective': dl.effective_date,
                'expires':   dl.expires_date,
            },

            'info_files': {
                'copyright': dl.copyright_file,
                'abstract':  dl.abstract_file,
                'biblio':    dl.biblio_file,
                'app':       dl.app_id,
            },


            'filesystem': dl.path_table.directories,
        }

    def default(self, o):
        if isinstance(o, cdi.Image):
            return self.encode_image(o)

        elif isinstance(o, cdi.DiscLabel):
            return self.encode_disc_label(o)

        elif isinstance(o, cdi.Directory):
            return self.encode_directory(o)

        elif isinstance(o, cdi.File):
            return self.encode_file(o)

        elif isinstance(o, datetime.datetime):
            return o.isoformat()

        else:
            return super().default(o)

args = parser.parse_args()
img = cdi.Image(args.image_file)
encoder = JSONEncoder()
for chunk in JSONEncoder().iterencode(img):
    sys.stdout.write(chunk)
