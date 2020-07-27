"""
Spotify utility functions.

These functions are somewhat opinionated, in that they provide a standard way
of loading spotify clients and tokens. However, they are generally usage-agnostic
and do not perform any of the actual main and follower syncing.
"""
import logging

from typing import Tuple

import tekore as tk

Credentials = None

Scopes = " ".join((
    "user-read-playback-state",
    "user-modify-playback-state",
    "streaming", "user-read-email", "user-read-private"
    ))

def configure(config_path: str):
    """Read the "SPOTIFY" section from the given config path and configure the Credentials object.

    Parameters
    ----------
    config_path: str
        Path to the configuration file.
    """
    client_id, client_secret, redirect_uri = tk.config_from_file(config_path, section="SPOTIFY")
    global Credentials
    Credentials = tk.Credentials(client_id, client_secret, redirect_uri, asynchronous=True)

def auth_url(state: str) -> str:
    """Generate an authorization URL

    Parameters
    ----------
    state: str
        The State parameter is added to the URL and returned by Spotify as part
        of the authorization flow.

    Returns
    -------
    str: Url to redirect the client to for authorization.
    """
    return Credentials.user_authorisation_url(scope=Scopes, state=state)

########
# PLAYBACK
########
async def play_track(user: str, client: tk.Spotify, track_id: str, retry: bool=False) -> Tuple[str, bool]:
    """Play a track for a client.

    This method will attempt to reload the client if it fails the first time.
    Often, the token needs refreshing, or the user has changed browser windows,
    or the sun hit the clouds just wrong, or some other stupid thing. A single
    refresh/retry tends to eliminate most transient errors

    Parameters
    ----------
    user: str
        user to play the song for. primarily used for logging and capturing failures.
    client: tk.Spotify
        Spotify client class. This actually determines where the song will play, not user.
    track_id: str
        Track ID to play.
    retry: bool=False
        If this is a retry. If retry is set to False, a failure to play will
        trigger a user reload attempt.
    
    Returns
    -------
    (str, bool): The user id and whether track was started successfully.

    Raises
    ------
    Nothing. This function intentionally swallows errors.
    """
    try:
        await client.playback_start_tracks([track_id,])
        return user, True
    except:
        logging.exception("Error playng track for user %s", user)
        if retry:
            return user, False
        try:
            _, client = await spotify.get_user(client.token.refresh_token) 
            await spotify.set_device(client)
            return await play_track(user, client, track_id, retry=True)
        except:
            logging.exception("Error refreshing user %s during play attempt", user)
            return user, False

async def stop(client: tk.Spotify) -> None:
    """Stop playback for the given client.
    
    This function swallows exceptions, since the spotify API throws an error
    when you try to stop an already stopped client, instead of just saying
    "yes sure that's fine" and going and sipping tea or something.

    Parameters:
    client    

    """
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
async def token_from_code(auth_code):
    return await Credentials.request_user_token(auth_code)

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

async def get_user_id(token):
    try:
        client = await get_client(token)
        user = await client.current_user()
    except Exception:
        logging.exception(f"Could not refresh token for {username}")
        raise
    else:
        return user.id

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
