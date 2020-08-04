"""Sync worker

Run as a separate single process. Reads the Main and follower tokens from the store,
and attempts to have followers play everything the main user does.
"""
import aiofiles
import asyncio
import logging
import os

from typing import Dict, Tuple, Optional

import tekore as tk

from utils import spotify
from utils import store

class FatalError(Exception):
    pass

#######
# SYNC OPERATIONS
#######
async def check_new(leader: tk.Spotify, current_id: Optional[str], current_playing: bool) -> Tuple[bool, str, bool]:
    """Check if the leader is playing a different track than the provided ID.

    This method also writes out new song information using the store.
    If spotify throws an error (perish the thought), pretend nothing changed,
    we'll grab it again next time.

    Parameters
    ----------
    leader: tk.Spotify
        Spotify client of the current leader
    current_id: str or None
        The song ID to compare against, or None if the leader wasn't playing anything.
    current_playing: bool
        Whether the leader was playing when last we checked.

    Returns
    -------
    (bool, str, bool): Whether the song has changed, what the new ID is if so, 
        and whether the leader is playing.
    """
    try:
        new = await spotify.get_current_track(leader)
    except:
        logging.exception("Error getting currently playing track.")
        return False, current_id, current_playing
    new_id = new.item.id if new else None
    new_playing = new.is_playing if new else False
    changed = (new_id != current_id or new_playing != current_playing)
    if changed:
        new_track = new.item.name if new  else "Not Playing"
        logging.info(f"New track: {new_track}")
        await store.write_song(new.item.json() if new else "null")
    return changed, new_id, new_playing

async def sync(leader: tk.Spotify, followers: Dict[str, tk.Spotify], song_id: Optional[str], playing: bool) -> None:
    """Sync the list of followers to the leader

    If given a song_id and playing is True, will attempt to sync all followers
    to that song. If given a song_id of None or playing is False, will attempt
    to stop all followers.

    Parameters
    ----------
    leader: tk.Spotify
        Leader client
    followers: {str: tk.Spotify}
        Dictionary mapping follower user_ids to Spotify clients
    song_id: str or None
        The song ID to sync, or None if the followers should be stopped.
    playing: bool
        Whether the leader is currently playing.
    """
    if song_id == None or playing == False:
        logging.info("leader stopped.")
        await stop_all(followers)
    else:
        logging.info(f"Got new track: {song_id}")
        await play_to_all(song_id, leader, followers)

async def play_to_all(track_id: str, leader: tk.Spotify, followers: Dict[str, tk.Spotify]) -> None:
    """Synchronize playback of a given track to all followers and the leader.

    This attempts to stop the leader and start playback again once all clients are playing.
    It means the leader will necessarily lag the followers a tiny bit. It also means we
    can only sync a song from the beginning, not the middle.

    Parameters
    ----------
    track_id: str
        ID of the track to play
    leader: tk.Spotify
        Leader spotify client
    followers: {str: tk.Spotify}
        Dictionary of user_id -> spotify client for each follower.
    """
    try:
        await leader.playback_pause()
        await leader.playback_seek(0)
    except:
        pass
    results = await asyncio.gather(*[
        spotify.play_track(user, client, track_id) for (user, client) in followers.items()
    ])
    try:
        await leader.playback_resume()
    except:
        logging.exception("Couldn't make user continue. Oh well.")
    for user, success in results:
        if not success:
            logging.info(f"couldn't play track for {user}")

async def stop_all(followers: Dict[str, tk.Spotify]):
    """Stop all followers.

    Parameters:
    followers: {str: tk.Spotify}
        Dictionary of user_id -> spotify client for each follower.
    """
    await asyncio.gather(*[
        spotify.stop(client) for client in followers.values()
    ])

#######
# Leader and Follower Setup
#######
async def setup_follower(user_id: str, client: Optional[tk.Spotify]) -> Tuple[str, Optional[tk.Spotify]]:
    """Check if a follower is correctly set up.

    This is used to verify that followers have up to date tokens and should
    still be used in the follower rotation. If we don't have a token in the
    store for a given user, we return None. If a client is provided and its
    token matches the one in the store, it is returned as-is. If not, we attempt
    to build a client for the user.

    Parameters
    ----------
    user_id: str 
        ID of the user to setup and verify tokens.
    client: tk.Spotify or None
        An existing client to compare to the token on disk
    
    Returns
    -------
    (str, tk.Spotify or None): The provided user id and a spotify client if we
        successfully created one.
    """
    try:
        token_str = await store.get_token(user_id)
        if spotify.client_is_good(client, token_str):
            return user_id, client
        display_name, client = await spotify.get_user(token_str) 
        await spotify.set_device(client)
        return user_id, client
    except Exception as err:
        logging.exception("Could not set up user %s", user_id)
        return user_id, None

async def check_followers(followers: Dict[str, tk.Spotify]) -> Dict[str, tk.Spotify]:
    """Check a dictionary of followers to ensure clients and tokens are up to date.

    This function will ensure our followers match the set of tokens we have. Followers
    with no tokens on file will be deleted, new tokens with no matching followers will
    have clients created for them.

    Parameters
    ---------
    followers: {str: tk.Spotify}
        Our existing dictionary of followers.

    Returns
    -------
    {str: tk.Spotify}: Dictionary of followers we have tokens for.
    """
    users = [u for u in await store.list_tokens() if u != "main"]
    loaded_users = await asyncio.gather(*[
        setup_follower(username, followers.get(username))
        for username in users])
    followers = {user:client for user, client in loaded_users if client is not None}
    logging.info(followers)
    return followers

async def check_leader(leader: Optional[tk.Spotify]) -> Optional[tk.Spotify]:
    """Check if our leader user is up to date and still registered.

    Parameters
    ----------
    leader: tk.Spotify or None
        Current leader client, if we have one.

    Returns
    -------
    tk.Spotify or None: Leader client if we have a token, None if not.
    """
    if not await store.have_token("main"):
        return None
    try:
        token_str = await store.get_token("main")
        if not spotify.client_is_good(leader, token_str):
            username, leader = await spotify.get_user(token_str)
            logging.info(f"Got leader user: {username}")
        return leader
    except Exception as err:
        logging.exception("Error getting leader user.")
        return None

#######
# And now the magic.
#######
async def main() -> None:
    """Main sync loop
    
    The loop runs every 2 seconds. It validates the leader user, checks if playback
    has changed, and only if it has, updates the followers and pushes the changes.

    It runs indefinitely, or until Spotify's API digs up another reason to throw an error
    that I haven't seen before.
    """    
    leader = None
    followers = dict()
    song_id, playing = None, False
    while True:
        await asyncio.sleep(2)
        leader = await check_leader(leader)
        if not leader:
            continue
        changed, song_id, playing = await check_new(leader, song_id, playing)
        if changed:
            followers = await check_followers(followers)
            await sync(leader, followers, song_id, playing)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    spotify.configure("./config.ini")
    asyncio.run(main())