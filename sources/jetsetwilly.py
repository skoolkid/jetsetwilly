# Copyright 2012, 2014-2021 Richard Dymond (rjdymond@gmail.com)
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

from skoolkit.graphics import Frame, Udg
from skoolkit.skoolhtml import HtmlWriter
from skoolkit.skoolmacro import parse_ints, parse_brackets, parse_image_macro

class JetSetWillyHtmlWriter(HtmlWriter):
    def init(self):
        self.expand(self.get_section('Expand'))
        self.font = {c: self.snapshot[15360 + 8 * c:15368 + 8 * c] for c in range(32, 122)}
        self.room_names_wp = self._get_room_names()
        self.room_frames = {}

    def expand_rframe(self, text, index, cwd):
        # #RFRAME(num,force=0,fix=0)(frame=$num)
        end, num, force, fix = parse_ints(text, index, 0, (0, 0), ('num', 'force', 'fix'), self.fields)
        if force:
            end, frame = parse_brackets(text, end)
        else:
            frame = str(num)
        if force or num not in self.room_frames:
            udgs = self._get_room_udgs(49152 + num * 256, fix)
            self.handle_image(Frame(udgs, 2, name=frame))
            if not force:
                self.room_frames[num] = True
        return end, ''

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

    def expand_jsw(self, text, index, cwd):
        # #JSWtrans[{x,y,width,height}](fname)
        end, crop_rect, fname, frame, alt, (trans,) = parse_image_macro(text, index, names=['trans'])
        tindex = int(trans > 0)
        alpha = 255 * int(trans == 0)
        udgs = lambda: self._build_logo()
        frames = [Frame(udgs, 1, 0, *crop_rect, name=frame, tindex=tindex, alpha=alpha)]
        return end, self.handle_image(frames, fname, cwd, alt)

    def room_name(self, cwd, room_num):
        return self.room_names_wp[room_num]

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
            lines.append('{{ #N{} | #N{},,,1(0x) | {} | {} }}'.format(addr, self.snapshot[addr], grid_loc, code))
        lines.append('TABLE#')
        return '\n'.join(lines)

    def _get_room_names(self):
        rooms_wp = {}
        for a in range(49152, 64768, 256):
            room_num = a // 256 - 192
            room_name_wp = ''.join([chr(b) for b in self.snapshot[a + 128:a + 160]]).strip()
            while room_name_wp.find('  ') > 0:
                start = room_name_wp.index('  ')
                end = start + 2
                while room_name_wp[end] == ' ':
                    end += 1
                room_name_wp = '{}#SPACE({}){}'.format(room_name_wp[:start], end - start, room_name_wp[end:])
            rooms_wp[room_num] = room_name_wp
        return rooms_wp

    def _get_room_udgs(self, addr, fix=0):
        # Collect block graphics
        block_graphics = []
        for a in range(addr + 160, addr + 206, 9):
            attr = self.snapshot[a]
            if fix:
                b = a
            else:
                # Simulate the 'Cell-Graphics' bug
                # https://www.oocities.org/andrewbroad/spectrum/willy/bugs.html
                b = addr + 160
                while b < a and self.snapshot[b] != attr:
                    b += 1
            block_graphics.append(Udg(attr, self.snapshot[b + 1:b + 9]))
        room_bg = block_graphics[0].attr

        # Build the room UDG array
        udg_array = []
        for a in range(addr, addr + 128):
            if a % 8 == 0:
                udg_array.append([])
            b = self.snapshot[a]
            for block_id in (b >> 6, (b >> 4) & 3, (b >> 2) & 3, b & 3):
                udg_array[-1].append(block_graphics[block_id].copy())

        # Room name
        name_udgs = [Udg(70, self.font[b]) for b in self.snapshot[addr + 128:addr + 160]]
        udg_array.append(name_udgs)

        # Ramp
        direction, p1, p2, length = self.snapshot[addr + 218:addr + 222]
        if length:
            attr = self.snapshot[addr + 196]
            ramp_udg = block_graphics[4]
            direction = direction * 2 - 1
            x = p1 & 31
            y = 8 * (p2 & 1) + (p1 & 224) // 32
            for i in range(length):
                udg_array[y][x] = ramp_udg.copy()
                y -= 1
                x += direction

        # Conveyor
        p1, p2, length = self.snapshot[addr + 215:addr + 218]
        if length:
            conveyor_udg = block_graphics[5]
            x = p1 & 31
            y = 8 * (p2 & 1) + (p1 & 224) // 32
            for i in range(x, x + length):
                udg_array[y][i] = conveyor_udg.copy()

        return udg_array
