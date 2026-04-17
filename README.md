# Osu Modding Helper
A helper tool for playtesting and modding osu! maps.


## Features

- **Make comments while playing a map.** 
Pause, go to the ModdingHelper's window and enter your comment.
- **Navigate your comments while editing a map.** 
Select a comment in ModdingHelper's window, it will trigger an osu link to the timestamp.
- **Post your comments.**
Copypaste them quickly - timestamp included!
- **Review where you missed.** 
Combo breaks receive an automatic comment (chain misses have a 1s cooldown by default).
- **Save your work and finish later.** 
Your comments for every map are saved when you close the program and loaded when you open it again.


# Installation

Modding Helper requires [tosu](https://tosu.app/) to work.
It makes use of the data that tosu reads from osu's memory.

### For users

1. Download [tosu](https://tosu.app/)
2. Download the [latest release](https://github.com/Kivicatte/osu-modding-helper/releases/latest) of OsuModdingHelper (built only for Windows currently)
3. Unpack and run both (tosu.exe and ModdingHelper.exe)

Tosu opens its dashboard in your browser when launched - 
you can turn it off in its settings if it's annoying.

### For developers

Get Python 3.10+, then install dependencies:

```commandline
pip install -r requirements.txt
```

Run main.py:

```commandline
python main.py
```

You still need to run tosu as well.


# Usage

## Interface breakdown

![](https://kivicatte.s-ul.eu/smyZRTlb)

## Managing comments

There are 3 types of comments:
- **General** comments are created by you and not tied to a timestamp.
- **Timeline** comments are created by you and tied to a timestamp.
- **Miss** comments are created automatically when you lose combo and tied to a timestamp. 
You can also create them by hand if you want. These work in editor playtest and multiplayer too.

All comments are tied to a single difficulty, not a mapset.

### Actions

- **Create.** Click the green plus button or type in the input line and press enter.
- **Select.** Click on comment marker in the marker section or on graph.
- **Edit.** Select a comment, then edit the message in the input line and press enter.
When a miss comment is edited, it's automatically converted to a timeline comment.
- **Copy.** Press Ctrl+C to copy a selected comment to clipboard.
Timeline comments are copied in \[timestamp] - \[comment] format, ready for posting.
- **Move.** Press Ctrl+M to move a selected comment to current time.
- **Delete.** Press X button on comment marker. Press red trash bin button to delete all comments of one type.
- **Saving** comments is automatic. 
Ignored comments are dropped between the sessions, the rest are saved
  (see settings). Nothing is dropped during the session.

Copy and move actions can also be done from comment marker's context menu.

![](https://kivicatte.s-ul.eu/4gfRwg4f)

### Limitations

- One timestamp can only have one comment (timeline or miss). 
Creating a new comment on an existing timestamp won't work.
- Creating timeline or miss comments outside of gameplay or editor should be avoided.
The timestamp you'll get may be unpredictable.

## Additional features

### Deactivate comments

Depending on your goal, you might want to keep the selected comment active 
or deactivate it automatically while navigating a map.

Default behavior depends on what you're doing in osu.
When you're playing, the comment is deactivated as soon as you unpause.
When you're editing, the comment is active until you deactivate in manually or activate another comment.

You can change this behavior for both playtesting and editing in settings.

### Stay on top mode

If you want to see the map and your comments at the same time, 
you can force Modding Helper's window to stay on top when you're editing via settings.

If Modding Helper appears unresponsive after entering or exiting the editor with staying on top enabled, try double-clicking it.
This may be due to conflict with osu itself and is unlikely to be fixed :c

# Security

[Virustotal scan](https://www.virustotal.com/gui/file/26f98e155eb376d4b5e7f3408fead10a626157b39aab9aa9c181c94348934baf) (main executable)

# Contacts

For any feedback or questions, feel free to use my [osu profile](https://osu.ppy.sh/users/2790640) 
or other contacts if you have any.

_If something is broken, check that tosu is running and not spamming errors first._


# License

Osu Modding Helper is licensed under AGPL-3.0-or-later. See the LICENSE file for the full text.
