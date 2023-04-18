from enum import Enum
from functools import partial
import itertools
import json
import os
import signal
import shlex
import shutil
import subprocess
import sys
import termios
import threading
import time

import setproctitle


# TODO move stand alone functions into utils.py?
def log(i):
    with open("/home/yobleck/.moc/sort/test.log", "a") as f:
        f.write(f"{time.asctime()}: {str(i)}\n")


def sig_handler(sig, frame):
    if sig == signal.SIGINT:
        print("\x1b[2J\x1b[H\x1b[?25h", end="")
        # TODO cancel timer
        sys.exit(0)
    elif sig == signal.SIGWINCH:
        print("screen size updated")
        pass  # update UI.scrn_size


def getch(blocking: bool = True, bytes_to_read: int = 1) -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new = list(old_settings)
    new[3] &= ~(termios.ICANON | termios.ECHO)
    new[6][termios.VMIN] = 1 if blocking else 0
    new[6][termios.VTIME] = 1  # 0 is faster but inputs appear on screen?
    termios.tcsetattr(fd, termios.TCSADRAIN, new)
    try:
        ch = sys.stdin.read(bytes_to_read)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


esc_chars = {"[A": "up", "[B": "dn", "[C": "rt", "[D": "lf", "[F": "end", "[H": "home", "[[A": "F1",
             "[[B": "F2", "[[C": "F3", "OS": "F4", "[Z": "shft+tb", "[5~": "pgup", "[6~": "pgdn",  # "OR": "F3"
             "[15~": "F5", "[17~": "F6", "[18~": "F7", "[19~": "F8", "[20~": "F9", "[21~": "F10",
             "[23~": "F11", "[24~": "F12"}  # TODO fix more F keys


def handle_esc() -> str:  # TODO only using keys with length 3?
    """https://en.wikipedia.org/wiki/ANSI_escape_code
    I don't know if this holds across all computers/keyboards
    or if my setup just weird?
    BUG: holding down key that uses less than 4 esc chars will capture
    first char of next sequence early so next characters are captured as plain text"""
    a = getch(False, 4)
    if a in esc_chars.keys():
        # log("key: " + a)
        return esc_chars[a]
    elif a == "":
        return "esc"
    # log("failed " + a)
    return ""


def moc_sync() -> dict:
    """sync with moc server via socket https://github.com/jonsafari/mocp/blob/master/protocol.h
    using subprocess mocp -i for now
    """
    d = {'State': '',
         'File': '',
         'Title': '',
         'Artist': '',
         'SongTitle': '',
         'Album': '',
         'TotalTime': '0',
         'TimeLeft': '0',
         'TotalSec': '1',  # avoid ZeroDivisionError
         'CurrentTime': '0',
         'CurrentSec': '0',
         'Bitrate': '0',
         'AvgBitrate': '0',
         'Rate': '0'}
    in_list = subprocess.run("mocp -i", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE).stdout.decode().splitlines()
    if in_list:  # TODO handle server not running?
        for i in in_list:
            d[i.split(": ")[0]] = i.split(": ")[1]
    return d


def folder_sort(folder: str, sort_mode: str, reverse: bool = False) -> list:
    do_sort = False if sort_mode == "name" else True
    files = subprocess.run(f"LC_COLLATE=en_US.utf8 ls -1pa{'r' * reverse} {'--sort=' * do_sort}{sort_mode * do_sort} "
                           f"--group-directories-first '{folder}'",
                           shell=True, stdout=subprocess.PIPE).stdout.decode().splitlines()

    to_remove = []
    for i, f in enumerate(files):
        if f[-1] == "/":
            continue
        elif f[-4:] not in [".mp3", ".wav", ".ogg", ".oga", ".m4a", ".aac", "flac", ".m3u"]:
            to_remove.append(f)
    for r in to_remove:
        files.remove(r)
    print("\x1b[2J\x1b[H")
    return files


def add_songs_to_playlist_and_play(songs: list, start_pos: int, folder: str) -> None:
    # TODO remove starting pos var? and use splice when calling
    # TODO loop around
    # songs = list(songs)
    i = 0
    subprocess.run(f"mocp -s; mocp -c", shell=True)
    for s in songs[start_pos:]:
        if s[-1] != "/" and s[-4:] != ".m3u":
            # -a option allows for multiple files to be added in one command
            # but they are added to playlist instead of queue
            # -q queue can't be cleared from command line
            # TODO replace loop with list comprehension that combines all parameters into one string. BUG unknown error
            subprocess.Popen(f"mocp -a {shlex.quote(folder + s)}", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            if i == 0:
                time.sleep(0.1)  # allows Popen() to finish before playing
                subprocess.run(f"mocp -p", shell=True)  # play first song while waiting for playlist to populate
                i += 1
            time.sleep(0.01)


help_scrn: str = "MOCS2 HELP SCREEN"  # TODO

config: dict = {  # default config values that don't rely on any other code for their definition
    "update_rate": 1,  # seconds
    "volume": 50,  # 0-100%
    "sort_mode": "name",  # options include "name", "time", and "size"
    "sort_reversed": False,
    "starting_folder": os.path.expanduser("~") + "/",
}
# parse config file
if os.path.exists("./mocs_settings.json"):
    with open("./mocs_settings.json", "r") as f:
        temp_dict: dict = json.load(f)
    for k in temp_dict.keys():
        if k in config.keys():
            config[k] = temp_dict[k]


class UI():
    w, h = shutil.get_terminal_size()
    scrn_size: tuple = (w, h - 1)  # - 1 for kitty weirdness?
    current_folder: str = config["starting_folder"]

    sort_cycle = itertools.cycle(["name", "size", "time"])
    sort_mode = config["sort_mode"]
    while True:
        if sort_mode == next(sort_cycle):
            break
    sort_reversed: bool = config["sort_reversed"]

    song_list: list = folder_sort(current_folder, sort_mode, sort_reversed)  # list(range(100))
    list_slice: tuple = (0, scrn_size[1] - 6)  # (top, bottom). - x for progress bar
    selected_song: int = 0  # between 0 and len(song_list)
    current_song_info: dict = moc_sync()
    volume: int = config["volume"]

    # TODO colors
    @classmethod
    def draw_list(cls, key: str) -> None:
        """draw borders, slice of list of files, highlight currently playing and selected, play/pause/stop state
        then call update_prog_bar
        """
        # if key == "\n":
        #     key = "entr"
        # print(f"\x1b[0;0H\x1b[Kkey pressed: {key}. sort mode: {cls.sort_mode} reversed: {cls.sort_reversed} folder: {cls.current_folder}")  # temp
        print(f"\x1b[0;0H\x1b[K┌─┤MOCS2├{'─' * 10}┤{cls.current_folder}├{'─' * (cls.scrn_size[0] - len(cls.current_folder) - 22)}┐")
        # ┌─┐
        for num, song in enumerate(cls.song_list[cls.list_slice[0]:cls.list_slice[1] + 1]):  # + 1 to include last item
            # TODO colors
            print(f"\x1b[K│{num + cls.list_slice[0]:03d} {song} {'<--'*(num + cls.list_slice[0] == cls.selected_song)}"
                  f"{' ' * (cls.scrn_size[0] - len(song) - 7 - (3 * (num + cls.list_slice[0] == cls.selected_song)))}│")
        for _ in range(cls.scrn_size[1] - num - 6):
            print(f"\x1b[K│{' ' * (cls.scrn_size[0] - 2)}│")  # any filler space if list is shorter than screen

        print(f"\x1b[K├{'─' * (cls.scrn_size[0] - 2)}┤")  # bottom of list
        # BUG duplicating songs with jp characters in them. possibly due to extra width chars
        # print("\x1b[0m")

    @classmethod
    def draw_status_bar(cls) -> None:
        # https://cloford.com/resources/charcodes/utf-8_box-drawing.htm
        cls.current_song_info = moc_sync()

        print(f"\x1b[{cls.scrn_size[1] - 2};0H\x1b[K│{cls.current_song_info['State']} > {cls.current_song_info['Title']}")
        print(f"\x1b[{cls.scrn_size[1] - 1};0H\x1b[K│sort mode: [{cls.sort_mode}]  reversed: [{cls.sort_reversed}]")

        print(f"\x1b[{cls.scrn_size[1]};0H\x1b[K├─┤{cls.current_song_info['CurrentTime']} {cls.current_song_info['TimeLeft']}"
              f" [{cls.current_song_info['TotalTime']}] {cls.progress_bar()}")
        # print("\x1b[0m")

    @classmethod
    def scroll(cls, amount: int) -> None:
        # outer if statement allows for scrolling cursor to last values. inner ifs correct for over shooting
        if 0 <= cls.selected_song < len(cls.song_list):
            cls.selected_song += amount
            if cls.selected_song < 0:  # scroll up
                cls.selected_song = 0
            elif cls.selected_song > len(cls.song_list) - 1:  # scroll down
                cls.selected_song = len(cls.song_list) - 1

        # handles scrolling the entire screen to keep cursor visible
        if cls.selected_song > cls.list_slice[1]:  # scroll down
            shift = cls.selected_song - cls.list_slice[1]
            cls.list_slice = (cls.list_slice[0] + shift, cls.list_slice[1] + shift)
        elif cls.selected_song < cls.list_slice[0]:  # scroll up
            shift = cls.list_slice[0] - cls.selected_song
            cls.list_slice = (cls.list_slice[0] - shift, cls.list_slice[1] - shift)

        # print(f"\x1b[{cls.scrn_size[1]};0H\x1b[Kselected: {cls.selected_song}")

    @classmethod
    def progress_bar(cls) -> str:
        # calculate what the progress bar should look like
        bar_width = cls.scrn_size[0] - 12 - len(cls.current_song_info["CurrentTime"]) -\
            len(cls.current_song_info["TimeLeft"]) - len(cls.current_song_info["TotalTime"])  # other characters on line add up to 12
        percent = int(cls.current_song_info["CurrentSec"]) / int(cls.current_song_info["TotalSec"])
        return f"┤{'█' * int(percent * bar_width)}{' ' * int((1 - percent) * bar_width)}├─┘"  # █ = \u2588, ┤ = \u2524, ├ = \u251c

    @classmethod
    def enter(cls) -> None:
        # TODO move the core functionality to an outside function and just have UI stuff in here?
        if cls.song_list[cls.selected_song][-1] == "/":  # handle folders
            if cls.song_list[cls.selected_song][-2:] == "./":  # go up a folder
                cls.current_folder = cls.current_folder.rsplit("/", 2)[0] + "/"
                cls.song_list = folder_sort(cls.current_folder, cls.sort_mode, cls.sort_reversed)
                cls.selected_song = 0
            else:  # go into a folder
                cls.current_folder = cls.current_folder + cls.song_list[cls.selected_song]
                cls.song_list = folder_sort(cls.current_folder, cls.sort_mode, cls.sort_reversed)
                cls.selected_song = 0
        elif cls.song_list[cls.selected_song][-4:] == ".m3u":
            pass  # TODO implement playlists?
        else:  # play song and add other songs to playlist
            add_songs_to_playlist_and_play(cls.song_list, cls.selected_song, cls.current_folder)

    @classmethod
    def cycle_sort(cls):
        cls.sort_mode = next(cls.sort_cycle)
        cls.song_list = folder_sort(cls.current_folder, cls.sort_mode, cls.sort_reversed)

    @classmethod
    def reverse_sort(cls):
        cls.sort_reversed = not cls.sort_reversed
        cls.song_list = folder_sort(cls.current_folder, cls.sort_mode, cls.sort_reversed)


config.update({  # default config values that have to be defined after UI()
    "key_binds": {" ": partial(subprocess.run, "mocp -G", shell=True),  # move to config?
                  "S": partial(subprocess.run, "mocp -s; mocp -c", shell=True),
                  "w": partial(UI.scroll, -1),
                  "s": partial(UI.scroll, 1),
                  "up": partial(UI.scroll, -1),
                  "dn": partial(UI.scroll, 1),
                  "lf": partial(subprocess.run, "mocp -k -1", shell=True),
                  "rt": partial(subprocess.run, "mocp -k 1", shell=True),
                  "pgup": partial(UI.scroll, -10),
                  "pgdn": partial(UI.scroll, 10),
                  "\n": partial(UI.enter),
                  "m": partial(UI.cycle_sort),
                  "M": partial(UI.reverse_sort),
                  # "c": clear playlist?
                  },
})


class RepeatTimer(threading.Timer):  # TODO sync timer to song start?
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


if __name__ == "__main__":
    setproctitle.setproctitle("mocs2")  # these are here because they only matter when the program is looping
    for signum in [signal.SIGINT, signal.SIGWINCH]:
        signal.signal(signum, sig_handler)

    timer = RepeatTimer(config["update_rate"], UI.draw_status_bar)
    timer.start()

    print("\x1b[2J\x1b[H\x1b[?25l")
    UI.draw_list(" ")
    UI.draw_status_bar()

    while True:
        char = getch()
        if char == "\x1b":
            char = handle_esc()
            if char == "esc":
                break
            elif char in config["key_binds"].keys():
                config["key_binds"][char]()
        elif char == "q":
            break
        elif char in config["key_binds"].keys():
            config["key_binds"][char]()

        UI.draw_list(char)
        UI.draw_status_bar()

    # TODO write certain values back out to the config file
    timer.cancel()
    print("\x1b[2J\x1b[H\x1b[?25h", end="")
