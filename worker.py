import logging
import os
import tekore as tk
import asyncio
import aiofiles

from utils import store

logging.basicConfig(level=logging.DEBUG)

client_id, client_secret, redirect_uri = tk.config_from_file("./config.ini")
creds = tk.Credentials(client_id, client_secret, redirect_uri, asynchronous=True)

token_dir = "tokens"

class FatalError(Exception):
    pass

class BadToken(Exception):
    pass

class BadClient(Exception):
    pass

class NoDevices(Exception):
    pass

# In a real environment we'd be using a data store. In here, we're sharing a dictionary.
followers = {}

########
# PLAYBACK
########


async def play_track(user, spotify, track_id, retry=False):
    try:
        await spotify.playback_start_tracks([track_id,])
        return user, True
    except tk.NotFound:
        if retry:
            return user, False
        user = await setup_follower(user, None)
        return await play_track(user, spotify, track_id, retry=True)

async def play_to_all(track_id, leader, followers):
    try:
        await leader.playback_pause()
    except:
        pass
    await leader.playback_seek(0)
    results = await asyncio.gather(*[
        play_track(user, spotify, track_id) for (user, spotify) in followers.items()
    ])
    try:
        await leader.playback_resume()
    except:
        logging.exception("Couldn't make user continue. Oh well.")
    for user, success in results:
        if not success:
            logging.info(f"couldn't play track for {user}")

async def stop(spotify):
    try:
        await spotify.playback_pause()
    except:
        pass

async def stop_all(followers):
    await asyncio.gather(*[
        stop(spotify) for spotify in followers.values()
    ])

#######
# BASIC USER SETUP
#######
async def get_user(token_str):
    try:
        token = await refresh_token(token_str)
        spotify = await get_spotify(token)
        user = await spotify.current_user()
    except Exception:
        logging.exception(f"Could not refresh token for {username}")
        raise
    else:
        display_name = user.display_name
        logging.info(f"Got client for {display_name}")
        return display_name, spotify

async def refresh_token(token_str):
    try:
        token = await creds.refresh_user_token(token_str)
    except:
        raise BadToken("Couldn't refresh token")
    else:
        return token

async def get_spotify(token):
    try:
        spotify = tk.Spotify(token, asynchronous=True)
    except:
        raise BadClient("Couldn't create client")
    else:
        return spotify

async def set_device(spotify):
    devices = await spotify.playback_devices()
    devices = [device for device in devices if device.name == "Game Night"]
    if not devices:
        raise NoDevices("No valid devices found")
    else:
        device = devices[0].id
        await spotify.playback_transfer(device)

#######
# SYNC OPERATIONS
#######
async def get_current_track(spotify):
    current = await spotify.playback_currently_playing()
    if not current:
        return None, None, False
    else:
        artists = ", ".join([a.name for a in current.item.artists])
        song_name = f"{current.item.name} - {artists}"
        return song_name, current.item.id, current.is_playing

async def check_new(leader, current_id, current_playing):
    new_name, new_id, new_playing = await get_current_track(leader)
    changed = (new_id != current_id or new_playing != current_playing)
    if changed:
        logging.info(f"New track: {new_name}")
        await store.write_song(new_name if new_name else "Not Playing")
    return changed, new_id, new_playing

async def sync(leader, followers, song_id, playing):
    if song_id == None or playing == False:
        logging.info("leader stopped.")
        await stop_all(followers)
    else:
        logging.info(f"Got new track: {song_id}")
        await play_to_all(song_id, leader, followers)

#######
# Leader and Follower Setup
#######
async def setup_follower(username, spotify):
    try:
        token_str = await store.get_token(username)
        if spotify is not None and token_str == spotify.token.refresh_token:
            return username, spotify
        display_name, spotify = await get_user(token_str) 
        await set_device(spotify)
        return username, spotify
    except Exception as err:
        logging.exception("Could not set up user %s", username)
        return username, None

async def check_followers(followers):
    users = [u for u in await store.list_tokens() if u != "main"]
    loaded_users = await asyncio.gather(*[
        setup_follower(username, followers.get(username))
        for username in users])
    followers = {user:spotify for user, spotify in loaded_users if spotify is not None}
    logging.info(followers)
    return followers

async def check_leader(leader):
    if not await store.have_token("main"):
        return None
    try:
        token = await store.get_token("main")
        if leader is None or token != leader.token.refresh_token:
            username, leader = await get_user(token)
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