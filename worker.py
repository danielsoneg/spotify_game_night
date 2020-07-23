import logging
import os
import tekore as tk
import asyncio
import aiofiles

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

def read_tokens():
    with open(f"{token_dir}/main") as fh:
        main = fh.read().strip()
    followers = {}
    for follower_token in os.listdir(token_dir):
        if follower_token == "main":
            continue
        with open(f"{token_dir}/{follower_token}") as fh:
            followers[follower_token] = fh.read().strip()
    return main, followers

def token_path(username):
    if not (token_dir and username):
        raise Exception("called for token_path without username or token_dir, avoiding potential CALAMITY")
    return f"./{token_dir}/{username}"

async def del_token(name):
    path = token_path(name)
    if not os.path.isfile(path):
        return
    await aiofiles.os.remove(path)

async def read_token(name):
    async with aiofiles.open(token_path(name)) as fh:
        token = await fh.read()
    return token.strip()

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

async def get_main(token_str):
    try:
        token = await refresh_token(token_str)
        spotify = await get_spotify(token)
        user = await spotify.current_user()
    except:
        raise FatalError("Could not get main user")
    else:
        return user.display_name, spotify

async def setup_follower(username):
    try:
        token_str = await read_token(username)
        display_name, spotify = await get_follower(username, token_str)
    except:
        logging.exception(f"Failed to get user {username}")
        return username, None
    _, success = await set_device(display_name, spotify)
    if not success:
        return username, None
    
        


async def get_follower(username, token_str):
    try:
        token = await refresh_token(token_str)
        spotify = await get_spotify(token)
        user = await spotify.current_user()
    except Exception:
        logging.exception(f"Could not refresh token for {username}, skipping")
        return None, None
    else:
        display_name = user.display_name
        logging.info(f"Got client for {display_name}")
        return display_name, spotify

async def get_followers(followers, main_token):
    followers = await asyncio.gather(*[
        get_follower(username, token) for username, token in followers.items()
                if token != main_token])
    return {user:token for user, token in followers if user is not None}

async def get_clients():
    logging.info("Hello")
    main_token_str, follower_token_strings = read_tokens()
    name, main = await get_main(main_token_str)
    logging.info(f"Got main user: {name}")
    followers = await get_followers(follower_token_strings, main_token_str)
    logging.info(f"Got {len(followers)} followers:")
    for follower in followers:
        logging.info(f" - {follower}")
    return main, followers

async def play_track(user, spotify, track_id, retry=False):
    try:
        await spotify.playback_start_tracks([track_id,])
        return user, True
    except tk.NotFound:
        if retry:
            return user, False
        _, updated = await set_device("", spotify)
        if updated:
            return await play_track(user, spotify, track_id, retry=True)
        else:
            return user, False

async def sync(track_id, main, followers):
    try:
        await main.playback_pause()
    except:
        pass
    await main.playback_seek(0)
    results = await asyncio.gather(*[
        play_track(user, spotify, track_id) for (user, spotify) in followers.items()
    ])
    try:
        await main.playback_resume()
    except:
        logging.exception("Couldn't make user continue. Oh well.")
    for user, success in results:
        if not success:
            logging.info(f"couldn't play track for {user}")

async def get_current_track(spotify):
    current = await spotify.playback_currently_playing()
    if not current:
        return None, None, False
    else:
        return current.item.name, current.item.id, current.is_playing

async def set_device(user, spotify):
    devices = await spotify.playback_devices()
    devices = [device for device in devices if device.name == "Game Night"]
    if not devices:
        return user, False
    else:
        device = devices[0].id
        await spotify.playback_transfer(device)
        return user, True

async def setup_followers(followers):
    tasks = []
    for follower, spotify in followers.items():
        tasks.append(set_device(follower, spotify))
    results = await asyncio.gather(*tasks)
    for (user, success) in results:
        if not success:
            logging.info(f"Could not set device for {user}")
            del(followers[user])

async def stop(spotify):
    try:
        await spotify.playback_pause()
    except:
        pass


async def stop_all(followers):
    await asyncio.gather(*[
        stop(spotify) for spotify in followers.values()
    ])


async def main():
    main, followers = await get_clients()
    await setup_followers(followers)
    current_name, current_id, current_playing = await get_current_track(main)
    while True:
        await asyncio.sleep(2)
        new_name, new_id, new_playing = await get_current_track(main)
        if new_id != current_id or new_playing != current_playing:
            if new_id == None or new_playing == False:
                logging.info("Main stopped.")
                await stop_all(followers)
            else:
                logging.info(f"Got new track: {new_name}")
                await sync(new_id, main, followers)
            current_name, current_id, current_playing = new_name, new_id, new_playing


if __name__ == "__main__":
    asyncio.run(main())