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

from skoolkit.graphics import Frame, Udg, overlay_udgs
from skoolkit.skoolhtml import HtmlWriter
from skoolkit.skoolmacro import parse_ints, parse_brackets, parse_image_macro

class JetSetWillyHtmlWriter(HtmlWriter):
    def init(self):
        self.font = {c: self.snapshot[15360 + 8 * c:15368 + 8 * c] for c in range(32, 122)}
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
        self.room_frames = {}

    def expand_rframe(self, text, index, cwd):
        # #RFRAME(num,force=0,fix=0)(frame=$num)
        end, num, force, fix = parse_ints(text, index, 0, (0, 0), ('num', 'force', 'fix'), self.fields)
        if force:
            end, frame = parse_brackets(text, end)
        else:
            frame = str(num)
        if force or num not in self.room_frames:
            udgs = self._get_room_udgs(49152 + num * 256, 1, fix)
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
        room, x, pixel_y, sprite, left, top, width, height, scale = params
        room_addr = 49152 + 256 * room
        room_udgs = self._get_room_udgs(room_addr, 1)
        willy = self._get_graphic(40192 + 32 * sprite, 7)
        room_bg = self.snapshot[room_addr + 160]
        self._place_graphic(room_udgs, willy, x, pixel_y, room_bg)
        img_udgs = [room_udgs[i][left:left + width] for i in range(top, top + min(height, 17 - top))]
        frames = [Frame(img_udgs, scale, 0, *crop_rect, name=frame)]
        return end, self.handle_image(frames, fname, cwd, alt, 'ScreenshotImagePath')

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

        if empty:
            return udg_array

        # Items
        room_num = addr // 256 - 192
        ink = 3
        for x, y in self.items.get(room_num, ()):
            attr = (udg_array[y][x].attr & 248) + ink
            udg_array[y][x] = Udg(attr, self.snapshot[addr + 225:addr + 233])
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
                pixel_y = guardian_def[3] // 2
                b1 = guardian_def[1]
                bright = 8 * (b1 & 8)
                ink = b1 & 7
                attr = bright + ink
                sprite_addr = 256 * guardian_def[5] + (start & 224)
                sprite = self._get_graphic(sprite_addr, attr)
                self._place_graphic(udg_array, sprite, x, pixel_y)
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
                self._place_graphic(udg_array, rope_udg_array, x, 0, room_bg)
            elif guardian_type == 4:
                # Arrow; first get the display file address at which the middle
                # of the arrow will be drawn
                df_addr = self.snapshot[start + 33280] + 256 * (self.snapshot[start + 33281] - 32)
                # Draw the arrow only if the JSW engine would draw it in the
                # upper two-thirds of the screen (unlike the first arrow in The
                # Attic!)
                if 16384 <= df_addr < 20480:
                    pixel_y = 64 * ((df_addr - 16384) // 2048) + (df_addr % 256) // 4
                    y_delta = (df_addr // 256) & 7
                    x = guardian_def[4] & 31
                    arrow_udg_data = [0] * (y_delta - 1) + [guardian_def[6], 255, guardian_def[6]] + [0] * (6 - y_delta)
                    arrow_udg = Udg(7, arrow_udg_data)
                    self._place_graphic(udg_array, [[arrow_udg]], x, pixel_y)

        if addr == 57600:
            # Toilet in the bathroom
            toilet = self._get_graphic(42496, 7)
            self._place_graphic(udg_array, toilet, 28, 13 * 8)
        elif addr == 58112:
            # Maria in the master bedroom
            maria = self._get_graphic(40064, 7)
            maria[0][0].attr = maria[0][1].attr = 69
            self._place_graphic(udg_array, maria, 14, 11 * 8)

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

    def _place_graphic(self, udg_array, graphic, x, pixel_y, bg_attr=None):
        rattr = lambda b, f: b & 56 | f & 71 if bg_attr in (None, b) else b
        overlay_udgs(udg_array, graphic, x * 8, pixel_y, 0, rattr)
