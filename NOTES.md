# STATUS
- API works.
- Player works in chrome, therefore is done. Little ugly on start, but whatcha gonna do.
- Worker is working.
- Overall: Could be used as-is.
- Player and API sharing "store" module, all async

# PRIORITY
- Main display
- Config handling

# TODO
- API:
    - Random cookie on start. Who cares, we'll re-login each time.
- Player:
    - Player now looks slightly better on cold start.
    - Main display 
        - who's leader
        - what's playing (/current_song)
        - who's connected
        - auto-refresh?
- Overall:
    - Better handling of config, startup, etc.
    - More robust data handoff from frontend to backend
        - Include usernames in tokens?
    - Actual run model. Or not, who cares.
