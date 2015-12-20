"""
termutils - collection of cross-platform terminal utilites

get_fg()
reset_fg()
set_fg()

get_bg()
reset_bg()
set_bg()

get_color()
reset_color()
set_color()

get_size()

get_pos()
set_pos()

get_key()

wipe()
"""

import os
import sys
import struct
import colorama as c


c.init()
_fg = 7
_bg = 0

_fg_colors = {
              0: c.Fore.BLACK,
              1: c.Fore.RED,
              2: c.Fore.GREEN,
              3: c.Fore.YELLOW,
              4: c.Fore.BLUE,
              5: c.Fore.MAGENTA,
              6: c.Fore.CYAN,
              7: c.Fore.WHITE,
}

_bg_colors = {
              0: c.Back.BLACK,
              1: c.Back.RED,
              2: c.Back.GREEN,
              3: c.Back.YELLOW,
              4: c.Back.BLUE,
              5: c.Back.MAGENTA,
              6: c.Back.CYAN,
              7: c.Back.WHITE,
}

_color_idx = {
              "BLACK": 0,
              "RED": 1,
              "GREEN": 2,
              "YELLOW": 3,
              "BLUE": 4,
              "MAGENTA": 5,
              "CYAN": 6,
              "WHITE": 7,
}


## Get terminal size ##


def get_size():
    """Returns terminal size as (cols, rows)"""
    xy=None
    if os.name == "nt":
        xy = _getTerminalSize_windows()
        if xy is None:
           xy = _getTerminalSize_tput()
           # needed for window's python in cygwin's xterm!
    elif os.name == "posix":
        xy = _getTerminalSize_linux()
    if xy is None:
        xy = (80, 25)      # default value
    return xy


def _getTerminalSize_windows():
    res = None
    try:
        from ctypes import windll, create_string_buffer

        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12

        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    except:
        return None
    if res:
        import struct
        (bufx, bufy, curx, cury, wattr,
         left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
        sizex = right - left + 1
        sizey = bottom - top + 1
        return sizex, sizey
    else:
        return None


def _getTerminalSize_tput():
    try:
        import subprocess
        proc = subprocess.Popen(["tput", "cols"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        cols = int(output[0])
        proc = subprocess.Popen(["tput", "lines"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        rows = int(output[0])
        return (cols, rows)
    except:
        return None


def _getTerminalSize_linux():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,'1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])


## Get cursor position ##


def get_pos():
    """Returns cursor location as (cols, rows)"""
    xy=None
    if os.name == "nt":
        xy = _getCurPos_windows()
    elif os.name == "posix":
        xy = _getCurPos_linux()
    return xy


def _getCurPos_windows():
    res = None
    try:
        from ctypes import windll, create_string_buffer

        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12

        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    except:
        return None
    if res:
        import struct
        (bufx, bufy, curx, cury, wattr,
         left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
        sizex = right - left + 1
        sizey = bottom - top + 1
        return curx + 1, cury + 1
    else:
        return None


def _getCurPos_linux():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    x = None
    y = None
    try:
        ch = ""
        tty.setraw(sys.stdin.fileno())
        while not ch.endswith('R'):
            ch += sys.stdin.read(1)
        x, y = ch.split(';')
        x = int(x.rpartition('[')[2])
        y = int(y.rstrip('R'))
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return x, y


## Set cursor position ##


def set_pos(x, y):
    print("\x1b[{};{}H".format(y, x), end='')


## Clear screen ##


def wipe():
    """Cross-platform function to clear the screen"""
    if os.name == "nt":
        os.system("cls")
    elif os.name == "posix":
        os.system("clear")
    else:
        print("\x1b[1,1H")
        x, y = get_size()
        print(" " * (x * y))


## Get keypress ##


class _Getch:
    """Gets a single character from standard input"""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty
        import termios

    def __call__(self):
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


get_key = _Getch()


## Foreground color ##


def get_fg():
    return _fg


def set_fg(color):
    if isinstance(color, str):
        color = _color_idx[color]
    elif isinstance(color, int):
        pass
    else:
        return
    _fg = color
    print(_fg_colors[color], end='')


def reset_fg():
    _fg = 7
    print(c.Fore.WHITE)


## Background color ##


def get_bg():
    return _bg


def set_bg(color):
    if isinstance(color, str):
        color = _color_idx[color]
    elif isinstance(color, int):
        pass
    else:
        return
    _bg = color
    print(_bg_colors[color], end='')


def reset_bg():
    _bg = 0
    print(c.Back.BLACK)


## Both colors ##


def get_color():
    return _fg, _bg


def set_color(fg, bg):
    set_fg(fg)
    set_bg(bg)


def reset_color():
    reset_fg()
    reset_bg()


def set_bright():
    print(c.Style.BRIGHT, end='')


def set_dim():
    print(c.Style.NORMAL, end='')


## Continuation of init routines ##

# reset terminal to defaults

print(c.Fore.WHITE, c.Back.BLACK, end='')