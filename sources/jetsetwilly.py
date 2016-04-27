# -*- coding: utf-8 -*-

# Copyright 2012, 2014-2016 Richard Dymond (rjdymond@gmail.com)
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

from skoolkit.skoolasm import AsmWriter
from skoolkit.skoolhtml import HtmlWriter, Frame, Udg
from skoolkit.skoolmacro import parse_ints, parse_image_macro

def parse_gbuf(text, index):
    # #GBUFfrom[,to]
    return parse_ints(text, index, 2, (None,))

class JetSetWillyHtmlWriter(HtmlWriter):
    def init(self):
        self.font = {}
        for b, h in self.get_dictionary('Font').items():
            self.font[b] = [int(h[i:i + 2], 16) for i in range(0, 16, 2)]
        start = 41984 + self.snapshot[41983]
        self.items = {}
        for a in range(start, 42240):
            b1 = self.snapshot[a]
            b2 = self.snapshot[a + 256]
            room_num = b1 & 63
            x = b2 & 31
            y = 8 * (b1 >> 7) + b2 // 32
            self.items.setdefault(room_num, []).append((x, y))
        self.room_names, self.room_names_wp = self._get_room_names()
        self.addr_anchor_fmt = self.get_dictionary('Game')['AddressAnchor']

    def _build_logo(self):
        udgs = []
        for j in range(38944, 39424, 32):
            row = []
            for i in range(j + 3, j + 29):
                attr = self.snapshot[i]
                if attr in (5, 8, 41, 44):
                    udg_addr = 33841 + 8 * (i & 1)
                elif attr in (4, 37, 40):
                    udg_addr = 33857 + 8 * (i & 1)
                else:
                    udg_addr = 0
                if attr == 44:
                    attr = 37
                row.append(Udg(attr & 127, self.snapshot[udg_addr:udg_addr + 8]))
            udgs.append(row)
        udgs.append([Udg(0, (0,) * 8)] * len(udgs[0]))
        return udgs

    def expand_logo(self, text, index, cwd):
        # #LOGO[{x,y,width,height}](fname)
        end, crop_rect, fname, frame, alt, params = parse_image_macro(text, index)
        udgs = lambda: self._build_logo()
        frames = [Frame(udgs, 1, 0, *crop_rect, name=frame)]
        return end, self.handle_image(frames, fname, cwd, alt)

    def expand_room(self, text, index, cwd):
        # #ROOMaddr[,scale,x,y,w,h,empty,fix,anim][{x,y,width,height}][(fname)]
        names = ('addr', 'scale', 'x', 'y', 'w', 'h', 'empty', 'fix', 'anim')
        defaults = (2, 0, 0, 32, 17, 0, 0, 0)
        end, crop_rect, fname, frame, alt, params = parse_image_macro(text, index, defaults, names)
        address, scale, x, y, w, h, empty, fix, anim = params
        if not fname:
            room_name = self.room_names[address // 256 - 192]
            fname = room_name.lower().replace(' ', '_')
        room_udgs = self._get_room_udgs(address, empty, fix)
        img_udgs = [room_udgs[i][x:x + w] for i in range(y, y + min(h, 17 - y))]
        if anim:
            attr = self.snapshot[address + 205]
            direction = self.snapshot[address + 214]
            frames = self._animate_conveyor(img_udgs, attr, direction, crop_rect, scale)
        else:
            frames = [Frame(img_udgs, scale, 0, *crop_rect, name=frame)]
        return end, self.handle_image(frames, fname, cwd, alt, 'ScreenshotImagePath')

    def expand_willy(self, text, index, cwd):
        # #WILLYroom,x,y,sprite[,left,top,width,height,scale](fname)
        names = ('room', 'x', 'y', 'sprite', 'left', 'top', 'width', 'height', 'scale')
        defaults = (0, 0, 32, 17, 2)
        end, crop_rect, fname, frame, alt, params = parse_image_macro(text, index, defaults, names)
        room, x, y, sprite, left, top, width, height, scale = params
        room_addr = 49152 + 256 * room
        room_udgs = self._get_room_udgs(room_addr)
        willy = self._get_graphic(40192 + 32 * sprite, 7)
        room_bg = self.snapshot[room_addr + 160]
        self._place_graphic(room_udgs, willy, x, y // 8, y % 8, room_bg)
        img_udgs = [room_udgs[i][left:left + width] for i in range(top, top + min(height, 17 - top))]
        frames = [Frame(img_udgs, scale, 0, *crop_rect, name=frame)]
        return end, self.handle_image(frames, fname, cwd, alt, 'ScreenshotImagePath')

    def expand_gbuf(self, text, index, cwd):
        end, addr_from, addr_to = parse_gbuf(text, index)
        link_text = '#N{}'.format(addr_from)
        if addr_to is not None:
            link_text += '-' + '#N{}'.format(addr_to)
        return end, '#LINK:GameStatusBuffer#{}({})'.format(addr_from, link_text)

    def rooms(self, cwd):
        lines = [
            '#TABLE(default,centre,centre,,centre)',
            '{ =h No. | =h Address | =h Name | =h Teleport }'
        ]
        for room_num in range(61):
            address = 49152 + room_num * 256
            room_name = self.room_names_wp[room_num]
            teleport_code = self._get_teleport_code(room_num)
            lines.append('{{ #N{0} | #N{1} | #R{1}({2}) | {3} }}'.format(room_num, address, room_name, teleport_code))
        lines.append('TABLE#')
        return ''.join(lines)

    def codes(self, cwd):
        lines = [
            '#TABLE(default,centre,centre,centre,centre)',
            '{ =h Address | =h Value | =h Grid | =h Code }'
        ]
        for i in range(179):
            addr = 40448 + i
            value = (self.snapshot[addr] + i) & 255
            code = '{}{}{}{}'.format((value >> 6) + 1, ((value >> 4) & 3) + 1, ((value >> 2) & 3) + 1, (value & 3) + 1)
            grid_loc = chr(65 + (i % 18)) + chr(48 + i // 18)
            lines.append('{{ #N{} | #N{} | {} | {} }}'.format(addr, self.snapshot[addr], grid_loc, code))
        lines.append('TABLE#')
        return '\n'.join(lines)

    def aeroplane(self, cwd):
        nomen_luni = self._get_room_udgs(61440, 1)[:-1]
        under_the_roof = self._get_room_udgs(59904, 1)[:-1]
        frames = [Frame(nomen_luni + under_the_roof)]
        return self.handle_image(frames, 'aeroplane', cwd, path_id='ScreenshotImagePath')

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

    def _get_teleport_code(self, room_num):
        code = ''
        key = 1
        while room_num:
            if room_num & 1:
                code += str(key)
            room_num //= 2
            key += 1
        return code + '9'

    def _animate_conveyor(self, udgs, attr, direction, crop_rect, scale):
        mask = 0
        x, y, width, height = crop_rect
        delay = 10
        frame1 = Frame(udgs, scale, mask, x, y, width, height, delay)
        frames = [frame1]

        base_udg = None
        for row in udgs:
            for udg in row:
                if udg.attr == attr:
                    base_udg = udg
                    break
        if base_udg is None:
            return frames

        prev_udg = base_udg
        while True:
            next_udg = prev_udg.copy()
            data = next_udg.data
            if direction:
                data[0] = (data[0] >> 2) + (data[0] & 3) * 64
                data[2] = ((data[2] << 2) & 255) + (data[2] >> 6)
            else:
                data[0] = ((data[0] << 2) & 255) + (data[0] >> 6)
                data[2] = (data[2] >> 2) + (data[2] & 3) * 64
            if next_udg.data == base_udg.data:
                break
            next_udgs = []
            for row in udgs:
                next_udgs.append([])
                for udg in row:
                    if udg.attr == attr:
                        next_udgs[-1].append(next_udg)
                    else:
                        next_udgs[-1].append(udg)
            frames.append(Frame(next_udgs, scale, mask, x, y, width, height, delay))
            prev_udg = next_udg
        return frames

    def _get_room_udgs(self, addr, empty=0, fix=0):
        # Collect block graphics
        block_graphics = []
        for a in range(addr + 160, addr + 196, 9):
            attr = self.snapshot[a]
            block_graphics.append(Udg(attr, self.snapshot[a + 1:a + 9]))
        room_bg = block_graphics[0].attr

        # Build the room UDG array
        udg_array = []
        for a in range(addr, addr + 128):
            if a % 8 == 0:
                udg_array.append([])
            b = self.snapshot[a]
            for block_id in (b >> 6, (b >> 4) & 3, (b >> 2) & 3, b & 3):
                udg_array[-1].append(block_graphics[block_id])

        # Room name
        name_udgs = [Udg(70, self.font[b]) for b in self.snapshot[addr + 128:addr + 160]]
        udg_array.append(name_udgs)

        # Ramp
        direction, p1, p2, length = self.snapshot[addr + 218:addr + 222]
        if length:
            attr = self.snapshot[addr + 196]
            ramp_udg = Udg(attr, self.snapshot[addr + 197:addr + 205])
            direction = direction * 2 - 1
            x = p1 & 31
            y = 8 * (p2 & 1) + (p1 & 224) // 32
            for i in range(length):
                udg_array[y][x] = ramp_udg
                y -= 1
                x += direction

        # Conveyor
        p1, p2, length = self.snapshot[addr + 215:addr + 218]
        if length:
            attr = self.snapshot[addr + 205]
            if fix:
                b = addr + 205
            else:
                # Simulate the 'Cell-Graphics' bug that affects conveyors
                # http://webspace.webring.com/people/ja/andrewbroad/bugs.html
                b = addr + 160
                while b < addr + 205 and self.snapshot[b] != attr:
                    b += 1
            conveyor_udg = Udg(attr, self.snapshot[b + 1:b + 9])
            x = p1 & 31
            y = 8 * (p2 & 1) + (p1 & 224) // 32
            for i in range(x, x + length):
                udg_array[y][i] = conveyor_udg

        if empty:
            return udg_array

        # Items
        item_udg_data = self.snapshot[addr + 225:addr + 233]
        room_num = addr // 256 - 192
        ink = 3
        for x, y in self.items.get(room_num, ()):
            attr = (udg_array[y][x].attr & 248) + ink
            udg_array[y][x] = Udg(attr, item_udg_data)
            ink += 1
            if ink == 7:
                ink = 3

        # Guardians
        for a in range(addr + 240, addr + 256, 2):
            num, start = self.snapshot[a:a + 2]
            if num == 255:
                break
            def_addr = 40960 + num * 8
            guardian_def = self.snapshot[def_addr:def_addr + 8]
            guardian_type = guardian_def[0] & 7
            if guardian_type & 3 in (1, 2):
                # Horizontal and vertical guardians
                x = start & 31
                y0 = guardian_def[3]
                y = (y0 & 240) // 16
                y_delta = (y0 & 14) // 2
                b1 = guardian_def[1]
                bright = 8 * (b1 & 8)
                ink = b1 & 7
                attr = bright + ink
                sprite_addr = 256 * guardian_def[5] + (start & 224)
                sprite = self._get_graphic(sprite_addr, attr)
                self._place_graphic(udg_array, sprite, x, y, y_delta)
            elif guardian_type & 3 == 3:
                # Rope
                x = start & 31
                length = guardian_def[4] + 1
                rope_udg_data = []
                i = j = 0
                while i < length:
                    if j % 3:
                        rope_udg_data.append(0)
                    else:
                        rope_udg_data.append(128)
                        i += 1
                    j += 1
                rope_udg_data += [0] * (8 - (len(rope_udg_data) & 7))
                rope_udg_array = []
                for i in range(0, len(rope_udg_data), 8):
                    rope_udg_array.append([Udg(room_bg, rope_udg_data[i:i + 8])])
                self._place_graphic(udg_array, rope_udg_array, x, 0, bg_attr=room_bg)
            elif guardian_type == 4:
                # Arrow; first get the display file address at which the middle
                # of the arrow will be drawn
                df_addr = self.snapshot[start + 33280] + 256 * (self.snapshot[start + 33281] - 32)
                # Draw the arrow only if the JSW engine would draw it in the
                # upper two-thirds of the screen (unlike the first arrow in The
                # Attic!)
                if 16384 <= df_addr < 20480:
                    y = ((df_addr // 256 - 64) & 24) + (df_addr % 256) // 32
                    y_delta = (df_addr // 256) & 7
                    x = guardian_def[4] & 31
                    arrow_udg_data = [0] * (y_delta - 1) + [guardian_def[6], 255, guardian_def[6]] + [0] * (6 - y_delta)
                    arrow_udg = Udg(7, arrow_udg_data)
                    self._place_graphic(udg_array, [[arrow_udg]], x, y)

        if addr == 57600:
            # Toilet in the bathroom
            toilet = self._get_graphic(42496, 7)
            self._place_graphic(udg_array, toilet, 28, 13)
        elif addr == 58112:
            # Maria in the master bedroom
            maria = self._get_graphic(40064, 7)
            maria[0][0].attr = maria[0][1].attr = 69
            self._place_graphic(udg_array, maria, 14, 11)

        return udg_array

    def _get_graphic(self, addr, attr=0):
        # Build a 16x16 graphic
        udgs = []
        for offsets in ((0, 1), (16, 17)):
            o1, o2 = offsets
            udgs.append([])
            for a in (addr + o1, addr + o2):
                udgs[-1].append(Udg(attr, self.snapshot[a:a + 16:2]))
        return udgs

    def _place_graphic(self, udg_array, graphic, x, y, y_delta=0, bg_attr=None):
        if y_delta > 0:
            graphic = self._shift_graphic(graphic, y_delta)
        for i, row in enumerate(graphic):
            for j, udg in enumerate(row):
                old_udg = udg_array[y + i][x + j]
                if bg_attr is None or old_udg.attr == bg_attr:
                    new_attr = (old_udg.attr & 56) | (udg.attr & 71)
                else:
                    new_attr = old_udg.attr
                new_data = [old_udg.data[k] | udg.data[k] for k in range(8)]
                udg_array[y + i][x + j] = Udg(new_attr, new_data)

    def _shift_graphic(self, graphic, y_delta):
        attr = graphic[0][0].attr
        blank_udg = Udg(attr, [0] * 8)
        width = len(graphic[0])
        prev_row = [blank_udg] * width
        shifted_graphic = []
        for row in graphic + [[blank_udg] * width]:
            shifted_graphic.append([])
            for i, udg in enumerate(row):
                shifted_udg_data = prev_row[i].data[-y_delta:] + udg.data[:-y_delta]
                shifted_graphic[-1].append(Udg(attr, shifted_udg_data))
                prev_row[i] = udg
        return shifted_graphic

class JetSetWillyAsmWriter(AsmWriter):
    def expand_gbuf(self, text, index):
        end, addr_from, addr_to = parse_gbuf(text, index)
        output = '#N{}'.format(addr_from)
        if addr_to is not None:
            output += '-#N{}'.format(addr_to)
        return end, output
