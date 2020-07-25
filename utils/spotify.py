import functools
import logging
import tekore as tk

Credentials = None

def configure(config_path):
    client_id, client_secret, redirect_uri = tk.config_from_file(config_path, section="SPOTIFY")
    global Credentials
    Credentials = tk.Credentials(client_id, client_secret, redirect_uri, asynchronous=True)

########
# PLAYBACK
########
async def play_track(user, client, track_id, retry=False):
    try:
        await client.playback_start_tracks([track_id,])
        return user, True
    except tk.NotFound:
        if retry:
            return user, False
        _, client = await spotify.get_user(client.token.refresh_token) 
        await spotify.set_device(client)
        return await play_track(user, client, track_id, retry=True)

async def stop(client):
    try:
        await client.playback_pause()
    except:
        pass

async def get_current_track(client, retry=False):
    try:
        current = await client.playback_currently_playing()
    except tk.Unauthorised:
        if retry:
            logging.exception("Could not get current track")
            raise
        _, client = get_user(client.token.refresh_token)
        return await get_current_track(client, retry=True)
    if not current:
        return None
    else:
        return current

#######
# BASIC USER SETUP
#######

async def get_user(token_str):
    try:
        token = await refresh_token(token_str)
        client = await get_client(token)
        user = await client.current_user()
    except Exception:
        logging.exception(f"Could not refresh token for {username}")
        raise
    else:
        display_name = user.display_name
        logging.info(f"Got client for {display_name}")
        return display_name, client

async def refresh_token(token_str):
    try:
        token = await Credentials.refresh_user_token(token_str)
    except:
        raise BadToken("Couldn't refresh token")
    else:
        return token

async def get_client(token):
    try:
        client = tk.Spotify(token, asynchronous=True)
    except:
        raise BadClient("Couldn't create client")
    else:
        return client

async def set_device(client):
    devices = await client.playback_devices()
    devices = [device for device in devices if device.name == "Game Night"]
    if not devices:
        raise NoDevices("No valid devices found")
    else:
        device = devices[0].id
        await client.playback_transfer(device)
