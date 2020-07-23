# STATUS
- API works.
- Player works in chrome, therefore is done. Little ugly on start, but whatcha gonna do.
- Worker is working.
- Overall: Could be used as-is.

# TODO
- API:
    - Switch to Quart
    - Random cookie on start. Who cares, we'll re-login each time.
- Player:
    - Maybe more graceful startup?
        - Call to backend when refreshed
    - Main display - what's playing, who's connected.
- Worker:
    - Filesystem watcher - catch backend changes.
    - Better handling of follower failures.
    - Catch expired tokens (new token each time?)
    - Handle no main
    - Rework flow/loops
- Overall:
    - More robust data handoff from frontend to backend
        - Include usernames in tokens?
    - Actual run model. Or not, who cares.
    - Better handling of config, startup, etc.
