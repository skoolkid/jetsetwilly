#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

PROLOGUE = """# -*- coding: utf-8 -*-
import sys
import os

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, '{}/tests'.format(SKOOLKIT_HOME))
import disassemblytest

JSW_SKOOL = '../sources/jet_set_willy.skool'
"""

OUTPUT_JSW = """Creating directory {odir}
Using skool file: {skoolfile}
Using ref files: ../sources/jet_set_willy.ref, ../sources/jet_set_willy-bugs.ref, ../sources/jet_set_willy-changelog.ref, ../sources/jet_set_willy-facts.ref, ../sources/jet_set_willy-pokes.ref
Parsing {skoolfile}
Creating directory {odir}/jet_set_willy
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to {odir}/jet_set_willy/skoolkit.css
Copying ../sources/jet_set_willy.css to {odir}/jet_set_willy/jet_set_willy.css
  Writing disassembly files in jet_set_willy/asm
  Writing jet_set_willy/maps/all.html
  Writing jet_set_willy/maps/routines.html
  Writing jet_set_willy/maps/data.html
  Writing jet_set_willy/maps/messages.html
  Writing jet_set_willy/maps/unused.html
  Writing jet_set_willy/buffers/gbuffer.html
  Writing jet_set_willy/tables/rooms.html
  Writing jet_set_willy/tables/codes.html
  Writing jet_set_willy/reference/credits.html
  Writing jet_set_willy/reference/changelog.html
  Writing jet_set_willy/reference/bugs.html
  Writing jet_set_willy/reference/facts.html
  Writing jet_set_willy/reference/glossary.html
  Writing jet_set_willy/reference/pokes.html
  Writing jet_set_willy/index.html"""

def write_tests(class_name, variables, options_list, extra_options):
    print(PROLOGUE)
    for name, value in variables:
        print('{} = """{}"""'.format(name, value))
        print('')
    class_name = '{}TestCase'.format(test_type.capitalize())
    print('class {0}(disassemblytest.{0}):'.format(class_name))
    for options in options_list:
        method_name_suffix = options.replace('-', '_').replace(' ', '')
        method_name = 'test_jsw{}'.format(method_name_suffix)
        if extra_options:
            options += ' ' + extra_options
        args = ["'{}'".format(options), 'JSW_SKOOL'] + [name for name, v in variables]
        print("    def {}(self):".format(method_name))
        print("        self._test_{}({})".format(test_type, ', '.join(args)))
        print("")

def get_asm_options_list():
    options_list = []
    for b in ('', '-D', '-H'):
        for c in ('', '-l', '-u'):
            for f in ('', '-f 1', '-f 2', '-f 3'):
                for p in ('', '-s', '-r'):
                    options_list.append('{} {} {} {}'.format(b, c, f, p).strip())
    return options_list

def get_ctl_options_list():
    options_list = []
    for w in ('', '-w b', '-w bt', '-w btd', '-w btdr', '-w btdrm', '-w btdrms', '-w btdrmsc'):
        for h in ('', '-h'):
            for a in ('', '-a'):
                for b in ('', '-b'):
                    options_list.append('{} {} {} {}'.format(w, h, a, b).strip())
    return options_list

def get_html_options_list():
    options_list = []
    for b in ('', '-D', '-H'):
        for c in ('', '-u', '-l'):
            options_list.append('{} {}'.format(b, c).strip())
    return options_list

VARIABLES = {
    'html': [('OUTPUT_JSW', OUTPUT_JSW)],
    'sft': [('JSW_Z80', '../build/jet_set_willy.z80')]
}

OPTIONS_LISTS = {
    'asm': get_asm_options_list(),
    'ctl': get_ctl_options_list(),
    'html': get_html_options_list(),
    'sft': ('', '-h', '-b', '-h -b')
}

EXTRA_OPTIONS = {
    'html': '-W ../sources:jetsetwilly.JetSetWillyHtmlWriter'
}
###############################################################################
# Begin
###############################################################################
if len(sys.argv) != 2 or sys.argv[1].lower() not in OPTIONS_LISTS:
    sys.stderr.write("Usage: {} asm|ctl|html|sft\n".format(os.path.basename(sys.argv[0])))
    sys.exit(1)
test_type = sys.argv[1].lower()
write_tests(test_type, VARIABLES.get(test_type, ()), OPTIONS_LISTS[test_type], EXTRA_OPTIONS.get(test_type, ''))
