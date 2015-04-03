#!/usr/bin/env python
import sys
import os

JETSETWILLY_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSW_SKOOL = '{}/sources/jet_set_willy.skool'.format(JETSETWILLY_HOME)

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if SKOOLKIT_HOME:
    if not os.path.isdir(SKOOLKIT_HOME):
        sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
        sys.exit(1)
    sys.path.insert(0, SKOOLKIT_HOME)
    from skoolkit import skool2asm, skool2html, sna2skool, tap2sna
else:
    try:
        from skoolkit import skool2asm, skool2html, sna2skool, tap2sna
    except ImportError:
        sys.stderr.write('Error: SKOOLKIT_HOME is not set, and SkoolKit is not installed\n')
        sys.exit(1)

sys.stderr.write("Found SkoolKit in {}\n".format(skool2html.PACKAGE_DIR))

def run_skool2asm():
    skool2asm.main(sys.argv[1:] + [JSW_SKOOL])

def run_skool2html():
    writer_class = '{}/skoolkit:jetsetwilly.JetSetWillyHtmlWriter'.format(JETSETWILLY_HOME)
    skool2html_options = '-d {}/build/html'.format(JETSETWILLY_HOME)
    skool2html_options += ' -S {}/resources -S {}/resources'.format(SKOOLKIT_HOME, JETSETWILLY_HOME)
    skool2html_options += ' -W {}'.format(writer_class)
    skool2html.main(skool2html_options.split() + sys.argv[1:] + [JSW_SKOOL])
