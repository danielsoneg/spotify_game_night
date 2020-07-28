import aiofiles
import asyncio
import logging
import os

import tekore as tk

from utils import spotify
from utils import store

class FatalError(Exception):
    pass

#######
# SYNC OPERATIONS
#######
async def check_new(leader, current_id, current_playing):
    new = await spotify.get_current_track(leader)
    new_id = new.item.id if new else None
    new_playing = new.is_playing if new else False
    changed = (new_id != current_id or new_playing != current_playing)
    if changed:
        new_track = new.item.name if new  else "Not Playing"
        logging.info(f"New track: {new_track}")
        await store.write_song(new.item.json() if new else "null")
    return changed, new_id, new_playing

async def sync(leader, followers, song_id, playing):
    if song_id == None or playing == False:
        logging.info("leader stopped.")
        await stop_all(followers)
    else:
        logging.info(f"Got new track: {song_id}")
        await play_to_all(song_id, leader, followers)

async def play_to_all(track_id, leader, followers):
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

async def stop_all(followers):
    await asyncio.gather(*[
        spotify.stop(client) for client in followers.values()
    ])


#######
# Leader and Follower Setup
#######
async def setup_follower(username, client):
    try:
        token_str = await store.get_token(username)
        if client is not None and token_str == client.token.refresh_token:
            return username, client
        display_name, client = await spotify.get_user(token_str) 
        await spotify.set_device(client)
        return username, client
    except Exception as err:
        logging.exception("Could not set up user %s", username)
        return username, None

async def check_followers(followers):
    users = [u for u in await store.list_tokens() if u != "main"]
    loaded_users = await asyncio.gather(*[
        setup_follower(username, followers.get(username))
        for username in users])
    followers = {user:client for user, client in loaded_users if client is not None}
    logging.info(followers)
    return followers

async def check_leader(leader):
    if not await store.have_token("main"):
        return None
    try:
        token = await store.get_token("main")
        if leader is None or token != leader.token.refresh_token:
            username, leader = await spotify.get_user(token)
            logging.info(f"Got leader user: {username}")
        return leader
    except Exception as err:
        logging.exception("Error getting leader user.")
        return None

#######
# And now the magic.
#######
async def main():
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
    asyncio.run(main())