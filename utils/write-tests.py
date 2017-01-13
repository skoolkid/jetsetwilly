#!/usr/bin/env python3
import sys
import os

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, '{}/tools'.format(SKOOLKIT_HOME))
from testwriter import write_tests

SKOOL = '../sources/jsw.skool'

SNAPSHOT = '../build/jet_set_willy.z80'

OUTPUT = """Using skool file: {skoolfile}
Using ref files: ../sources/jsw.ref, ../sources/bugs.ref, ../sources/changelog.ref, ../sources/facts.ref, ../sources/glossary.ref, ../sources/pokes.ref
Parsing {skoolfile}
Creating directory {odir}/jet_set_willy
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to {odir}/jet_set_willy/skoolkit.css
Copying ../sources/jsw.css to {odir}/jet_set_willy/jsw.css
  Writing disassembly files in jet_set_willy/asm
  Writing jet_set_willy/maps/all.html
  Writing jet_set_willy/maps/routines.html
  Writing jet_set_willy/maps/data.html
  Writing jet_set_willy/maps/messages.html
  Writing jet_set_willy/maps/unused.html
  Writing jet_set_willy/buffers/gbuffer.html
  Writing jet_set_willy/reference/bugs.html
  Writing jet_set_willy/reference/changelog.html
  Writing jet_set_willy/reference/facts.html
  Writing jet_set_willy/reference/glossary.html
  Writing jet_set_willy/reference/pokes.html
  Writing jet_set_willy/tables/rooms.html
  Writing jet_set_willy/tables/codes.html
  Writing jet_set_willy/reference/credits.html
  Writing jet_set_willy/index.html"""

HTML_WRITER = '../sources:jetsetwilly.JetSetWillyHtmlWriter'

ASM_WRITER = '../sources:jetsetwilly.JetSetWillyAsmWriter'

write_tests(SKOOL, SNAPSHOT, OUTPUT, HTML_WRITER, ASM_WRITER)
