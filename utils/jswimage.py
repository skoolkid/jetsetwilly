#!/usr/bin/env python
import sys
import os
import argparse

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, SKOOLKIT_HOME)

JETSETWILLY_HOME = os.environ.get('JETSETWILLY_HOME')
if not JETSETWILLY_HOME:
    sys.stderr.write('JETSETWILLY_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(JETSETWILLY_HOME):
    sys.stderr.write('JETSETWILLY_HOME={}; directory not found\n'.format(JETSETWILLY_HOME))
    sys.exit(1)
sys.path.insert(0, '{}/sources'.format(JETSETWILLY_HOME))

from skoolkit.image import ImageWriter
from skoolkit.refparser import RefParser
from skoolkit.skoolhtml import Frame
from skoolkit.snapshot import get_snapshot
from jetsetwilly import JetSetWillyHtmlWriter

class JetSetWilly(JetSetWillyHtmlWriter):
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.defaults = RefParser()
        self.ref_parser = RefParser()
        self.ref_parser.parse('{}/sources/jet_set_willy.ref'.format(JETSETWILLY_HOME))
        self.init()

def _do_pokes(specs, snapshot):
    for spec in specs:
        addr, val = spec.split(',', 1)
        step = 1
        if '-' in addr:
            addr1, addr2 = addr.split('-', 1)
            addr1 = int(addr1)
            if '-' in addr2:
                addr2, step = [int(i) for i in addr2.split('-', 1)]
            else:
                addr2 = int(addr2)
        else:
            addr1 = int(addr)
            addr2 = addr1
        addr2 += 1
        value = int(val)
        for a in range(addr1, addr2, step):
            snapshot[a] = value

def _place_willy(jsw, udg_array, spec):
    if spec:
        values = []
        for n in spec.split(','):
            try:
                values.append(int(n))
            except ValueError:
                values.append(None)
        values += [None] * (3 - len(values))
        x, y, frame = values
        if x is not None and y is not None:
            willy = jsw._get_graphic(40192 + 32 * (frame or 0))
            jsw._place_graphic(udg_array, willy, x, y, 7)

def run(imgfname, options):
    snapshot = get_snapshot('{}/build/jet_set_willy.z80'.format(JETSETWILLY_HOME))
    _do_pokes(options.pokes, snapshot)
    jsw = JetSetWilly(snapshot)
    udg_array = jsw._get_room_udgs(49152 + 256 * options.room)
    _place_willy(jsw, udg_array, options.willy)
    if options.geometry:
        wh, xy = options.geometry.split('+', 1)
        width, height = [int(n) for n in wh.split('x')]
        x, y = [int(n) for n in xy.split('+')]
        udg_array = [row[x:x + width] for row in udg_array[y:y + height]]
    frame = Frame(udg_array, options.scale)
    image_format = 'gif' if imgfname.lower()[-4:] == '.gif' else 'png'
    image_writer = ImageWriter()
    with open(imgfname, "wb") as f:
        image_writer.write_image([frame], f, image_format)

###############################################################################
# Begin
###############################################################################
parser = argparse.ArgumentParser(
    usage='jswimage.py [options] FILE.{png,gif}',
    description="Create an image of a room in Jet Set Willy.",
    add_help=False
)
parser.add_argument('imgfname', help=argparse.SUPPRESS, nargs='?')
group = parser.add_argument_group('Options')
group.add_argument('-g', dest='geometry', metavar='WxH+X+Y',
                   help='Create an image with this geometry')
group.add_argument('-p', dest='pokes', metavar='A[-B[-C]],V', action='append', default=[],
                   help="Do POKE N,V for N in {A, A+C, A+2C,...B} (this option may be used multiple times)")
group.add_argument('-r', dest='room', type=int, default=0,
                   help='Create an image of this room (default: 0)')
group.add_argument('-s', dest='scale', type=int, default=2,
                   help='Set the scale of the image (default: 2)')
group.add_argument('-w', dest='willy', metavar='X,Y[,F]',
                   help="Place Willy at (X,Y) with animation frame F (0-7)")
namespace, unknown_args = parser.parse_known_args()
if unknown_args or not namespace.imgfname:
    parser.exit(2, parser.format_help())
run(namespace.imgfname, namespace)
