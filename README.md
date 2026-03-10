# OsuModdingHelper
A helper tool for playtesting and modding osu! maps.


## Features

- **Make comments while playing a map.** 
Pause, go to the ModdingHelper's window and enter your comment. 
It will automatically receive a timestamp and attach to the map.
- **Navigate your comments while editing a map.** 
Click on a comment in ModdingHelper's window, and it will take you to its timestamp in osu.
- **Review your misses. Or don't.** 
Every miss receives an automatic comment that you can view later 
(chain misses have a latency period of 1s).
These can be turned off.
- **Procrastinate and finish your work later.** 
Your comments for every map are saved when you close the program and loaded when you open it again. 
Empty comments and default miss comments are NOT saved. 
Edit their text to enable saving.


# Installation

OsuModdingHelper requires [tosu](https://tosu.app/) to work.
It makes use of the data that tosu reads from osu's memory.

### Instructions for users

- Download [tosu](https://tosu.app/)
- Download the [latest release](https://github.com/Kivicatte/osu-modding-helper/releases/tag/v0.1.0-alpha) of OsuModdingHelper
  (Windows only)
- Unpack and run both (tosu.exe and ModdingHelper.exe)


### Instructions for developers

Set up your environment with the following requirements.
- Python>=3.10
- PySide6=6.10
- matplotlib=3.10

Launch main.py to run the program. Note that it still needs tosu running as well.

Versions of the libraries are not strict, it's simply the ones I tested with. 
Others might work but it's not guaranteed.

# License
OsuModdingHelper is licensed under AGPL-3.0-or-later. See the LICENSE file for the full text.
