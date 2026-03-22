NOTES_PATH = r'notes.json'          # file in which your notes will be saved

CHAIN_MISS_THRESHOLD_MS = 1000      # consecutive misses in this timeframe will be handled as chain misses
SAVE_MISS_MARKS = False             # set True to save miss marks between sessions
                                    # by default notes are ignored if their text says 'miss' and nothing else

IGNORE_LIST = ['miss', '']
