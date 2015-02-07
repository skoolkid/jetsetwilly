#!/usr/bin/env python
import sys
import os
import argparse
from collections import OrderedDict

try:
    from skoolkit.snapshot import get_snapshot
    from skoolkit import tap2sna, sna2skool
except ImportError:
    SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
    if not SKOOLKIT_HOME:
        sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
        sys.exit(1)
    if not os.path.isdir(SKOOLKIT_HOME):
        sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
        sys.exit(1)
    sys.path.insert(0, SKOOLKIT_HOME)
    from skoolkit.snapshot import get_snapshot
    from skoolkit import tap2sna, sna2skool

JETSETWILLY_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = '{}/build'.format(JETSETWILLY_HOME)
JSW_Z80 = '{}/jet_set_willy.z80'.format(BUILD_DIR)

GUARDIANS = {
    43776: (4, 5),
    43904: (4, 5),
    44032: (4, 66),
    44160: (4, 4),
    44288: (4, 14),
    44416: (4, 7),
    44544: (4, 11),
    44672: (4, 3),
    44800: (4, 5),
    44928: (4, 5),
    45056: (4, (3, 6, 5, 5)),
    45184: (2, 23),
    45248: (2, 6),
    45312: (8, 7),
    45568: (4, 13),
    45696: (4, 74),
    45824: (0, 4),
    46080: (8, 4),
    46336: (8, 67),
    46592: (8, 66),
    46848: (2, 67),
    46912: (2, 3),
    46976: (4, 15),
    47104: (8, 5),
    47360: (4, 13),
    47488: (4, 68),
    47616: (4, 66),
    47744: (4, 52),
    47872: (4, 15),
    48000: (4, 70),
    48128: (8, 66),
    48384: (8, 14),
    48640: (4, 4),
    48768: (4, 69),
    48896: (4, 5),
    49024: (2, 4),
    49088: (2, 22)
}

class JetSetWilly:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.sprite_macros = self._get_sprite_macros()
        self.room_names, self.room_names_wp = self._get_room_names()
        self.room_macros = self._get_room_macros()
        self.room_entities = self._get_room_entities()

    def _get_sprite_macros(self):
        sprite_macros = {
            40000: '#UDGARRAY2,6,,2;40000-40017-1-16(foot)',
            40032: '#UDGARRAY2,66,,2;40032-40049-1-16(barrel)'
        }
        for i, a in enumerate(range(40064, 40192, 32)):
            sprite_macros[a] = '#UDGARRAY2,step=2;{},69;{},69;{},7;{},7(maria{})'.format(a, a + 1, a + 16, a + 17, i)
        return sprite_macros

    def _get_room_names(self):
        rooms = {}
        rooms_wp = {}
        for a in range(49152, 64768, 256):
            room_num = a // 256 - 192
            room_name = ''.join([chr(b) for b in self.snapshot[a + 128:a + 160]]).strip()
            room_name_wp = room_name
            while room_name_wp.find('  ') > 0:
                start = room_name_wp.index('  ')
                end = start + 2
                while room_name_wp[end] == ' ':
                    end += 1
                room_name_wp = '{}#SPACE({}){}'.format(room_name_wp[:start], end - start, room_name_wp[end:])
            rooms[room_num] = room_name
            rooms_wp[room_num] = room_name_wp
        return rooms, rooms_wp

    def _get_room_macros(self):
        room_macros = {}
        for room_num in range(61):
            addr = 256 * (room_num + 192)
            room_macros[room_num] = '#R{}({})'.format(addr, self.room_names_wp[room_num])
        return room_macros

    def _get_room_entities(self):
        room_entities = {}
        for room_num in range(61):
            addr = 256 * (room_num + 192)
            for a in range(addr + 240, addr + 256, 2):
                num, start = self.snapshot[a:a + 2]
                if num == 255:
                    break
                room_entities.setdefault(room_num, []).append((num, start))
        return room_entities

    def _get_room_links(self, room_nums):
        macros = [self.room_macros[n] for n in room_nums]
        if len(macros) == 1:
            return macros[0]
        return '{} and {}'.format(', '.join(macros[:-1]), macros[-1])

    def _get_teleport_code(self, room_num):
        code = ''
        key = 1
        while room_num:
            if room_num & 1:
                code += str(key)
            room_num //= 2
            key += 1
        return code + '9'

    def _get_guardian_macro(self, addr, attr):
        fname = 'guardian{}-{}-{}'.format(addr // 256, (addr % 256) // 32, attr)
        return '#UDGARRAY2,{},,2;{}-{}-1-16({})'.format(attr, addr, addr + 17, fname)

    def get_screen_buffer_address_table(self):
        lines = ['w 33280 Screen buffer address lookup table ']
        lines.append('D 33280 Used by the routines at #R35914, #R37310 and #R38455. '
                     'The value of the Nth entry (0<=N<=127) in this lookup table is the '
                     'screen buffer address for the point with pixel coordinates '
                     '(x,y)=(0,N), with the origin (0,0) at the top-left corner.')
        lines.append('@ 33280 label=SBUFADDRS')
        y = 0
        for addr in range(33280, 33536, 2):
            lines.append('W {} y={}'.format(addr, y))
            y += 1
        lines.append('i 33536')
        return '\n'.join(lines)

    def get_entity_definitions(self):
        defs = {}
        sprite_addrs = {}
        for room_num, specs in self.room_entities.items():
            room_bg = self.snapshot[(room_num + 192) * 256 + 160] & 56
            for num, start in specs:
                defs.setdefault(num, set()).add(room_num)
                def_addr = 40960 + num * 8
                guardian_def = self.snapshot[def_addr:def_addr + 8]
                guardian_type = guardian_def[0] & 7
                if guardian_type & 3 in (1, 2):
                    sprite_addr = 256 * guardian_def[5] + (start & 224)
                    if sprite_addr == 46336:
                        # Use frame 2 instead of frame 0 for the saw sprite
                        sprite_addr = 46400
                    sprite_addrs.setdefault(num, set()).add((sprite_addr, room_bg))

        lines = ['b 40960 Entity definitions']
        lines.append('@ 40960 label=ENTITYDEFS')
        lines.append('D 40960 Used by the routine at #R35068.')
        lines.append('D 40960 The following (empty) entity definition (0) is copied into the entity buffer at #R33024 for any entity specification whose first byte is zero.')
        lines.append('B 40960,8')
        for num in range(1, 112):
            addr = 40960 + num * 8
            if num in defs:
                room_links = self._get_room_links(sorted(defs[num]))
                comment = 'The following entity definition ({}) is used in {}.'.format(num, room_links)
            else:
                comment = 'The following entity definition ({}) is not used.'.format(num)
            lines.append('D {} {}'.format(addr, comment))
            if num in sprite_addrs:
                ink = self.snapshot[40961 + 8 * num] & 7
                bright = 8 * (self.snapshot[40961 + 8 * num] & 8)
                sprites = []
                for a, room_bg in sorted(sprite_addrs[num]):
                    sprites.append(self._get_guardian_macro(a, bright | room_bg | ink))
                lines.append('D {} #UDGTABLE {{ {} }} TABLE#'.format(addr, ' | '.join(sprites)))
            if num in defs or num == 43:
                entity_def = self.snapshot[addr:addr + 8]
                entity_type = entity_def[0] & 7
                direction = 'left to right' if entity_def[0] & 128 else 'right to left'
                ink = entity_def[1] & 7
                bright = (entity_def[1] & 8) // 8
                frame_mask = '{:08b}'.format(entity_def[1])[:3]
                b1_format = ',b1'
                desc1 = 'INK {} (bits 0-2), BRIGHT {} (bit 3), animation frame mask {} (bits 5-7)'.format(ink, bright, frame_mask)
                b6_format = ''
                if entity_type & 3 == 1:
                    desc0 = 'Horizontal guardian (bits 0-2), initial animation frame {} (bits 5 and 6), initially moving {} (bit 7)'.format((entity_def[0] & 96) // 32, direction)
                    desc2 = 'Replaced by the base sprite index and initial x-coordinate (copied from the second byte of the entity specification in the room definition)'
                    desc3 = 'Pixel y-coordinate: {}'.format(entity_def[3] // 2)
                    desc4 = 'Unused'
                    desc5 = 'Page containing the sprite graphic data: #R{}({})'.format(entity_def[5] * 256, entity_def[5])
                    desc6 = 'Minimum x-coordinate'
                    desc7 = 'Maximum x-coordinate'
                elif entity_type & 3 == 2:
                    desc0_infix = ''
                    if frame_mask != '000':
                        desc0_infix = ', animation frame updated on every {}pass (bit 4)'.format('' if entity_def[0] & 16 else 'second ')
                    desc0 = 'Vertical guardian (bits 0-2){}, initial animation frame {} (bits 5 and 6)'.format(desc0_infix, (entity_def[0] & 96) // 32)
                    desc2 = 'Replaced by the base sprite index and x-coordinate (copied from the second byte of the entity specification in the room definition)'
                    desc3 = 'Initial pixel y-coordinate: {}'.format(entity_def[3] // 2)
                    y_inc = entity_def[4] if entity_def[4] < 128 else entity_def[4] - 256
                    if y_inc == 0:
                        direction = 'not moving'
                    elif y_inc > 0:
                        direction = 'moving down'
                    else:
                        direction = 'moving up'
                    desc4 = 'Initial pixel y-coordinate increment: {} ({})'.format(y_inc // 2, direction)
                    desc5 = 'Page containing the sprite graphic data: #R{}({})'.format(entity_def[5] * 256, entity_def[5])
                    desc6 = 'Minimum pixel y-coordinate: {}'.format(entity_def[6] // 2)
                    desc7 = 'Maximum pixel y-coordinate: {}'.format(entity_def[7] // 2)
                elif entity_type & 3 == 3:
                    desc0 = 'Rope (bits 0-2), initially swinging {} (bit 7)'.format(direction)
                    b1_format = ''
                    desc1 = 'Initial animation frame index'
                    desc2 = 'Replaced by the x-coordinate of the top of the rope (copied from the second byte of the entity specification in the room definition)'
                    desc3 = 'Unused'
                    desc4 = 'Length'
                    desc5 = 'Unused'
                    desc6 = 'Unused'
                    desc7 = 'Animation frame at which the rope changes direction'
                else:
                    desc0 = 'Arrow (bits 0-2), flying {} (bit 7)'.format(direction)
                    b1_format = ''
                    desc1 = 'Unused'
                    desc2 = 'Replaced by the pixel y-coordinate (copied from the second byte of the entity specification in the room definition)'
                    desc3 = 'Unused'
                    desc4 = 'Initial x-coordinate: {}'.format(entity_def[4])
                    desc5 = 'Unused'
                    b6_format = ',b1'
                    desc6 = 'Top/bottom pixel row (drawn either side of the shaft)'
                    desc7 = 'Unused'
                lines.append('@ {} label=ENTITY{}'.format(addr, num))
                lines.append('B {},b1 {}'.format(addr, desc0))
                lines.append('B {}{} {}'.format(addr + 1, b1_format, desc1))
                lines.append('B {} {}'.format(addr + 2, desc2))
                lines.append('B {} {}'.format(addr + 3, desc3))
                lines.append('B {} {}'.format(addr + 4, desc4))
                lines.append('B {} {}'.format(addr + 5, desc5))
                lines.append('B {}{} {}'.format(addr + 6, b6_format, desc6))
                lines.append('B {} {}'.format(addr + 7, desc7))
            else:
                lines.append('B {},8'.format(addr))
        lines.append('D 41856 The next 15 entity definitions (112-126) are unused.')
        lines.append('B 41856,120,8')
        lines.append('@ 41976 label=ENTITY127')
        lines.append('D 41976 The following entity definition (127) - whose eighth byte is at #R41983 - '
                     'is copied into the entity buffer at #R33024 for any entity specification whose '
                     'first byte is 127 or 255; the first byte of the definition (255) serves to '
                     'terminate the entity buffer.')
        lines.append('B 41976,7')
        lines.append('i 41983')
        return '\n'.join(lines)

    def get_udg_table(self, addr, num, attr=56, fname=None, rows=1, animation='', delay=None):
        macros = []
        start = addr
        suffix = '*' if animation else ''
        if isinstance(attr, int):
            attrs = [attr] * num
        else:
            attrs = list(attr)
        for r in range(rows):
            macros.append([])
            frames = []
            end = start + (32 * num) // rows
            for b in range(start, end, 32):
                if num == 1:
                    frame = fname
                else:
                    frame = '{}{}'.format(fname, (b - addr) // 32)
                if r % 2:
                    frames.insert(0, frame)
                else:
                    frames.append(frame)
                if b in self.sprite_macros:
                    macros[-1].append(self.sprite_macros[b])
                else:
                    macros[-1].append('#UDGARRAY2,{},,2;{}-{}-1-16({}{})'.format(attrs.pop(0), b, b + 17, frame, suffix))
            start = end
            if r < len(animation):
                if delay:
                    frames[0] += ',{}'.format(delay)
                macros[-1].append('#UDGARRAY*{}({}_{}.gif)'.format(';'.join(frames), fname, animation[r]))
        udgtable = '#UDGTABLE'
        for r in range(rows):
            udgtable += ' {{ {} }}'.format(' | '.join(macros[r]))
        return udgtable + ' TABLE#'

    def get_graphics(self, addr, num, attr, fname=None, rows=1, animation='', delay=None):
        lines = []
        udg_table = self.get_udg_table(addr, num, attr, fname, rows, animation, delay)
        lines.append('D {} {}'.format(addr, udg_table))
        lines.append('B {},{},16'.format(addr, 32 * num))
        return '\n'.join(lines)

    def get_guardian_graphics(self):
        guardians = {}
        for room_num, specs in self.room_entities.items():
            for num, start in specs:
                def_addr = 40960 + num * 8
                guardian_def = self.snapshot[def_addr:def_addr + 8]
                guardian_type = guardian_def[0] & 7
                if guardian_type & 3 in (1, 2):
                    sprite_addr = 256 * guardian_def[5] + (start & 224)
                    if sprite_addr >= 43776:
                        while sprite_addr not in GUARDIANS:
                            sprite_addr -= 32
                        guardians.setdefault(sprite_addr, set()).add(room_num)

        lines = ['b 43776 Guardian graphics']
        lines.append('@ 43776 label=GUARDIANS')
        lines.append('D 43776 Used by the routine at #R37310.')
        lines.append('@ 46592 label=FLYINGPIG0')
        for a in sorted(GUARDIANS.keys()):
            page = a // 256
            base_index = (a % 256) // 32
            num, attr = GUARDIANS[a]
            if isinstance(attr, int):
                attrs = [attr] * num
            else:
                attrs = list(attr)
            end_index = base_index + num - 1
            if a in guardians:
                room_links = self._get_room_links(sorted(guardians[a]))
                comment = 'This guardian (page {}, sprites {}-{}) appears in {}.'.format(page, base_index, end_index, room_links)
            elif a == 45312:
                comment = 'This guardian (page {}, sprites {}-{}) is not used.'.format(page, base_index, end_index)
            elif a == 45824:
                comment = 'The next 256 bytes are unused.'
            lines.append('D {} {}'.format(a, comment))
            if num:
                sprites = []
                for addr in range(a, a + num * 32, 32):
                    sprites.append(self._get_guardian_macro(addr, attrs.pop(0)))
                lines.append('D {} #UDGTABLE {{ {} }} TABLE#'.format(a, ' | '.join(sprites)))
                lines.append('B {},{},16'.format(a, 32 * num))
            else:
                lines.append('S {},256'.format(a))
        lines.append('i 49152')
        return '\n'.join(lines)

    def get_item_table(self):
        lines = ['b 41984 Item table']
        lines.append('D 41984 Used by the routines at #R34762 and #R37841.')
        lines.append('D 41984 The location of item N (173<=N<=255) is defined by the pair of bytes at '
                     'addresses #R41984+N and #R42240+N. The meaning of the bits in each byte-pair is '
                     'as follows:')
        lines.append('D 41984 #TABLE(default,centre) '
                     '{ =h Bit(s) | =h Meaning } '
                     '{ 15 | Most significant bit of the y-coordinate } '
                     '{ 14 | Collection flag (reset=collected, set=uncollected) } '
                     '{ 8-13 | Room number } '
                     '{ 5-7 | Least significant bits of the y-coordinate } '
                     '{ 0-4 | x-coordinate } TABLE#')
        lines.append('@ 41984 label=ITEMTABLE1')
        lines.append('S 41984 Unused')
        items = {}
        for a in range(42157, 42240):
            b1, b2 = self.snapshot[a], self.snapshot[a + 256]
            x, y = b2 & 31, 8 * (b1 >> 7) + b2 // 32
            room_link = self._get_room_links([b1 & 63])
            index = a % 256
            items[index] = (room_link, (x, y))
            lines.append('B {} Item {} at ({},{}) in {}'.format(a, index, y, x, room_link))
        lines.append('@ 42240 label=ITEMTABLE2')
        lines.append('S 42240 Unused')
        for a in range(42413, 42496):
            index = a % 256
            room_link, (x, y) = items[index]
            lines.append('B {} Item {} at ({},{}) in {}'.format(a, index, y, x, room_link))
        lines.append('i 42496')
        return '\n'.join(lines)

    def _write_tiles(self, lines, a):
        room_num = a // 256 - 192
        udgs = []
        for addr, tile_type in ((a + 160, 'background'), (a + 169, 'floor'), (a + 178, 'wall'), (a + 187, 'nasty'), (a + 196, 'ramp'), (a + 205, 'conveyor')):
            attr = self.snapshot[addr]
            if tile_type == 'background':
                room_paper = attr & 120
            img_type = ''
            if attr >= 128:
                paper = (attr & 56) // 8
                ink = attr & 7
                if paper != ink:
                    udg_bytes = self.snapshot[addr + 1:addr + 9]
                    if not all([b == 0 for b in udg_bytes]) and not all([b == 255 for b in udg_bytes]):
                        # This tile is flashing
                        img_type = '.gif'
            udgs.append('#UDG{},{}({}{:02d}{})'.format(addr + 1, attr, tile_type, room_num, img_type))
        tiles_table = '#UDGTABLE { ' + ' | '.join(udgs) + ' } TABLE#'
        comment = 'The next 54 bytes are copied to #R32928 and contain the attributes and graphic data for the tiles used to build the room.'
        tile_usage = [' (unused)'] * 6
        for b in self.snapshot[a:a + 128]:
            for i in range(4):
                tile_usage[b & 3] = ''
                b >>= 2
        ramp_length = self.snapshot[a + 221]
        if ramp_length:
            tile_usage[4] = ''
        conveyor_length = self.snapshot[a + 217]
        if conveyor_length:
            tile_usage[5] = ''
            conveyor_attr = self.snapshot[a + 205]
            b = a + 160
            while b < a + 205 and self.snapshot[b] != conveyor_attr:
                b += 1
            if b < a + 205:
                comment += ' Note that because of a #BUG#corruptedConveyors in the game engine, the conveyor tile is not drawn correctly (see the room image above).'
        lines.append('D {} {}'.format(a + 160, comment))
        lines.append('D {} {}'.format(a + 160, tiles_table))
        lines.append('B {},9,9 Background{}'.format(a + 160, tile_usage[0]))
        lines.append('B {},9,9 Floor{}'.format(a + 169, tile_usage[1]))
        lines.append('B {},9,9 Wall{}'.format(a + 178, tile_usage[2]))
        lines.append('B {},9,9 Nasty{}'.format(a + 187, tile_usage[3]))
        lines.append('B {},9,9 Ramp{}'.format(a + 196, tile_usage[4]))
        lines.append('B {},9,9 Conveyor{}'.format(a + 205, tile_usage[5]))

        return room_paper

    def _write_conveyor(self, lines, a):
        lines.append('D {} The next four bytes are copied to #R32982 and specify the direction, location and length of the conveyor.'.format(a + 214))
        conveyor_d, p1, p2 = self.snapshot[a + 214:a + 217]
        conveyor_x = p1 & 31
        conveyor_y = 8 * (p2 & 1) + (p1 & 224) // 32
        lines.append('B {},1 Direction ({})'.format(a + 214, 'right' if conveyor_d else 'left'))
        lines.append('W {},2 Location in the attribute buffer at #R24064: ({},{})'.format(a + 215, conveyor_y, conveyor_x))
        lines.append('B {},1 Length'.format(a + 217))

    def _write_ramp(self, lines, a):
        lines.append('D {} The next four bytes are copied to #R32986 and specify the direction, location and length of the ramp.'.format(a + 218))
        ramp_d, p1, p2 = self.snapshot[a + 218:a + 221]
        ramp_x = p1 & 31
        ramp_y = 8 * (p2 & 1) + (p1 & 224) // 32
        lines.append('B {},1 Direction (up to the {})'.format(a + 218, 'right' if ramp_d else 'left'))
        lines.append('W {},2 Location in the attribute buffer at #R24064: ({},{})'.format(a + 219, ramp_y, ramp_x))
        lines.append('B {},1 Length'.format(a + 221))

    def _write_exits(self, lines, a, room_name):
        lines.append('D {} The next four bytes are copied to #R33001 and specify the rooms to the left, to the right, above and below.'.format(a + 233))
        room_left, room_right, room_up, room_down = self.snapshot[a + 233:a + 237]
        for addr, num, name, desc in (
            (a + 233, room_left, self.room_names_wp.get(room_left), 'to the left'),
            (a + 234, room_right, self.room_names_wp.get(room_right), 'to the right'),
            (a + 235, room_up, self.room_names_wp.get(room_up), 'above'),
            (a + 236, room_down, self.room_names_wp.get(room_down), 'below'),
        ):
            if name and name != room_name:
                lines.append('B {} Room {} (#R{}({}))'.format(addr, desc, 256 * (num + 192), name))
            elif name:
                lines.append('B {} Room {} ({})'.format(addr, desc, name))
            else:
                lines.append('B {} Room {} (none)'.format(addr, desc))

    def _write_entity_specs(self, lines, a):
        room_num = a // 256 - 192
        start = a + 240
        entities = []
        for addr in range(start, a + 256, 2):
            num, coords = self.snapshot[addr:addr + 2]
            def_addr = 40960 + (num & 127) * 8
            entity_def = self.snapshot[def_addr:def_addr + 8]
            guardian_type = entity_def[0] & 7
            entities.append((num, coords, guardian_type, def_addr))
        infix = '' if room_num == 47 else 'are copied to #R33008 and '
        lines.append('D {} The next eight pairs of bytes {}specify the entities (ropes, arrows, guardians) in this room.'.format(start, infix))
        addr = start
        terminated = False
        for num, coords, guardian_type, def_addr in entities:
            if num == 0:
                desc = 'Nothing'
            elif num == 255:
                desc = 'Terminator'
                terminated = True
            elif guardian_type == 1:
                desc = 'Guardian no. {} (horizontal), base sprite {}, initial x={}'.format(num, coords // 32, coords & 31)
            elif guardian_type == 2:
                desc = 'Guardian no. {} (vertical), base sprite {}, x={}'.format(num, coords // 32, coords & 31)
            elif guardian_type == 3:
                desc = 'Rope at x={}'.format(coords & 31)
            else:
                direction = ('right to left', 'left to right')[self.snapshot[def_addr] // 128]
                if coords & 1:
                    # Faulty arrow specification
                    y0 = self.snapshot[coords + 33281] - 96
                    pixel_y = 8 * (y0 & 248) + (y0 & 7) + (self.snapshot[coords + 33280] & 224) // 4
                else:
                    pixel_y = coords // 2
                desc = 'Arrow flying {} at pixel y-coordinate {}'.format(direction, pixel_y)
            suffix = ' (unused)' if 0 < num < 255 and terminated else ''
            if addr == 59900:
                lines.append('@ {} bfix=DEFB 69,82'.format(addr))
            lines.append('B {},2 {} (#R{}){}'.format(addr, desc, def_addr, suffix))
            addr += 2

    def get_rooms(self):
        lines = []

        start = 41984 + self.snapshot[41983]
        items = {}
        for a in range(start, 42240):
            b1 = self.snapshot[a]
            b2 = self.snapshot[a + 256]
            room_num = b1 & 63
            x = b2 & 31
            y = 8 * (b1 >> 7) + b2 // 32
            items.setdefault(room_num, []).append((x, y))

        for a in range(49152, 64768, 256):
            room = self.snapshot[a:a + 256]
            room_num = a // 256 - 192
            room_name = self.room_names[room_num]
            if room_num == 60:
                lines.append('@ {} ignoreua:t'.format(a))
            lines.append('b {} Room {}: {} (teleport: {})'.format(a, room_num, self.room_names_wp[room_num], self._get_teleport_code(room_num)))
            if a in (50688, 56320, 56576, 59904, 61440):
                # Rooms with flashing cells
                room_image = '#ROOM{}({}.gif)'.format(a, room_name.lower().replace(' ', '_'))
            elif a == 61184:
                # [
                room_image = '#ROOM{}(left_square_bracket)'.format(a)
            else:
                room_image = '#ROOM{}'.format(a)
            if room_num == 47:
                lines.append('D 61184 This room is not used.')
            else:
                lines.append('D {} Used by the routine at #R35068.'.format(a))
            lines.append('D {} #UDGTABLE {{ {} }} TABLE#'.format(a, room_image))
            if room_num == 47:
                lines.append('D 61184 The first 128 bytes define the room layout. Each bit-pair (bits 7 and 6, 5 and 4, 3 and 2, or 1 and 0 of each byte) determines the type of tile (background, floor, wall or nasty) that will be drawn at the corresponding location.')
                lines.append('B 61184,128,8 Room layout (completely empty)')
            else:
                lines.append('D {} The first 128 bytes are copied to #R32768 and define the room layout. Each bit-pair (bits 7 and 6, 5 and 4, 3 and 2, or 1 and 0 of each byte) determines the type of tile (background, floor, wall or nasty) that will be drawn at the corresponding location.'.format(a))
                if room_num == 30:
                    lines.append('@ 56872 bfix=DEFB 0,0,0,129,4,0,0,0')
                elif room_num == 43:
                    lines.append('@ 60224 bfix=DEFB 0,0,0,0,0,48,195,0')
                lines.append('B {},128,8 Room layout'.format(a))

            # Room name
            if room_num == 47:
                lines.append('D 61312 The next 32 bytes specify the room name.')
            else:
                lines.append('D {} The next 32 bytes are copied to #R32896 and specify the room name.'.format(a + 128))
            lines.append('T {},32 Room name'.format(a + 128))

            if room_num == 47:
                lines.append('D 61344 In a working room definition, the next 80 bytes define the tiles, conveyor, ramp, border colour, item graphic, and exits. In this room, however, there are code remnants and unused data.')
                lines.append('B 61344,9,9 Background tile')
                lines.append('B 61353')
                lines.append('C 61361')
                lines.append('B 61370')
                lines.append('C 61372')
                lines.append('B 61399')
                lines.append('B 61401 Conveyor length (deliberately set to 0)')
                lines.append('C 61402')
                lines.append('B 61405 Ramp length (deliberately set to 0)')
                lines.append('C 61406')
                lines.append('B 61423')
            else:
                # Tiles
                room_paper = self._write_tiles(lines, a)

                # Conveyor direction, location and length
                self._write_conveyor(lines, a)

                # Ramp direction, location and length
                self._write_ramp(lines, a)

                # Border colour
                lines.append('D {} The next byte is copied to #R32990 and specifies the border colour.'.format(a + 222))
                lines.append('B {} Border colour'.format(a + 222))

                # Bytes 223/224
                lines.append('D {} The next two bytes are copied to #R32991, but are not used.'.format(a + 223))
                lines.append('B {} Unused'.format(a + 223))

                # Item graphic
                lines.append('D {} The next eight bytes are copied to #R32993 and define the item graphic.'.format(a + 225))
                lines.append('D {0} #UDGTABLE {{ #UDG{0},{1}(item{2:02d}) }} TABLE#'.format(a + 225, room_paper + 3, room_num))
                lines.append('B {},8,8 Item graphic{}'.format(a + 225, '' if items.get(room_num) else ' (unused)'))

                # Rooms to the left, to the right, above and below
                self._write_exits(lines, a, room_name)

                # Bytes 237-239
                lines.append('D {} The next three bytes are copied to #R33005, but are not used.'.format(a + 237))
                lines.append('B {} Unused'.format(a + 237))

            # Entities
            self._write_entity_specs(lines, a)

        lines.append('i 64768')
        return '\n'.join(lines)

def run(subcommand):
    if not os.path.isdir(BUILD_DIR):
        os.mkdir(BUILD_DIR)
    if not os.path.isfile(JSW_Z80):
        tap2sna.main(('-d', BUILD_DIR, '@{}/jet_set_willy.t2s'.format(JETSETWILLY_HOME)))
    jsw = JetSetWilly(get_snapshot(JSW_Z80))
    ctlfile = '{}/{}.ctl'.format(BUILD_DIR, subcommand)
    with open(ctlfile, 'wt') as f:
        f.write(getattr(jsw, methods[subcommand][0])())
    sna2skool.main(('-c', ctlfile, JSW_Z80))

###############################################################################
# Begin
###############################################################################
methods = OrderedDict((
    ('entity-defs', ('get_entity_definitions', 'Entity definitions (40960-41982)')),
    ('guardians', ('get_guardian_graphics', 'Guardian graphics (43776-49151)')),
    ('items', ('get_item_table', 'Item table (41984-42495)')),
    ('rooms', ('get_rooms', 'Rooms (49152-64767)')),
    ('sbat', ('get_screen_buffer_address_table', 'Screen buffer address table (33280-33535)'))
))
subcommands = '\n'.join('  {} - {}'.format(k, v[1]) for k, v in methods.items())
parser = argparse.ArgumentParser(
    usage='%(prog)s SUBCOMMAND',
    description="Produce a skool file snippet for Jet Set Willy. SUBCOMMAND must be one of:\n\n{}".format(subcommands),
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False
)
parser.add_argument('subcommand', help=argparse.SUPPRESS, nargs='?')
namespace, unknown_args = parser.parse_known_args()
if unknown_args or namespace.subcommand not in methods:
    parser.exit(2, parser.format_help())
run(namespace.subcommand)
