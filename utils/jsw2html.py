#!/usr/bin/env python
import sys
import os
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if SKOOLKIT_HOME:
    if not os.path.isdir(SKOOLKIT_HOME):
        sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
        sys.exit(1)
    sys.path.insert(0, SKOOLKIT_HOME)
    from skoolkit import skool2html, sna2skool, tap2sna
    skool2html.SEARCH_DIRS += (os.path.join(SKOOLKIT_HOME, 'resources'),)
else:
    try:
        from skoolkit import skool2html, sna2skool, tap2sna
    except ImportError:
        sys.stderr.write('Error: SKOOLKIT_HOME is not set, and SkoolKit is not installed\n')
        sys.exit(1)

sys.stderr.write("Found SkoolKit in {}\n".format(skool2html.PACKAGE_DIR))

import jsw2ctl

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
build_dir = os.path.join(parent_dir, 'build')
if not os.path.isdir(build_dir):
    os.mkdir(build_dir)

# Write jet_set_willy.z80
jswz80 = os.path.join(build_dir, 'jet_set_willy.z80')
if not os.path.isfile(jswz80):
    tap2sna.main(('-d', build_dir, '@{}/jet_set_willy.t2s'.format(parent_dir)))

# Write jet_set_willy.ctl
ctlfile = os.path.join(build_dir, 'jet_set_willy.ctl')
with open(ctlfile, 'wt') as f:
    f.write(jsw2ctl.main(jswz80))

# Write jet_set_willy.skool
stdout = sys.stdout
sys.stdout = StringIO()
sna2skool.main(('-c', ctlfile, jswz80))
skoolfile = os.path.join(build_dir, 'jet_set_willy.skool')
with open(skoolfile, 'wt') as f:
    f.write(sys.stdout.getvalue())
sys.stdout = stdout

# Build the HTML disassembly
writer_class = '{}/skoolkit:jetsetwilly.JetSetWillyHtmlWriter'.format(parent_dir)
options = '-c Config/HtmlWriterClass={} -d {}/html'.format(writer_class, build_dir)
args = options.split() + sys.argv[1:] + [skoolfile]
skool2html.main(args)
