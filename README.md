# mocs
["Music On Console"](https://github.com/jonsafari/mocp) is great, but it can only sort songs alphabetically.
Here is a python ncurses gui that allows songs to be sorted.
  - a-z and z-a
  - size small-large and large-small
  - date modified old-new and new-old
  
  ## Installation
  download files to any folder nut usually ~/.moc/sort/<br>
  alias mocs="python path/to/sorter.py" #in .bashrc for convenience<br>
  depends on python, mocp, and the python packages setproctitle and wcwidth
  
## Usage
  1. open mocp and navigate to desired folder the quit mocp (but don't kill server)
  2. open mocs <br>
    - vertical arrow keys to scroll songs <br>
    - horizontal arrow keys to seek through song <br>
    - "enter" to play <br>
    - "space" to pause/unpause <br>
    - "s" to stop <br>
    - "m" to toggle through sort modes <br>
    - "a" to toggle autoplay <br>
    - "," volume down 5% <br>
    - "." volume up 5% <br>
    - "esc" to exit program <br>

## Use mocp instead of this to:
  - search for songs
  - create and use playlists
  - change settings/themes/muxing etc.

## WIP <br>
This mocp alternate frontend is WIP. It may have feature parity in the future, or maybe not since all this program does is call the commandline through the python subprocess module and present the results.
V2 in progress

## Known Issues:
    - holding enter key breaks UI
    - a number of UI elements have hardcoded postions and may look wrong for small terminals (should work with 80 col x 20 row and up)
    - progress bar and some other elements may flicker on less robust terminals
    - crude interface with mocp server
