"""
Main API server
"""
import argparse
import asyncio
import logging
import random
import string

from typing import Optional, Dict, Union

import tekore as tk

from quart import Quart, request, redirect, url_for, session, render_template

# from utils import store
from utils import config
from utils.store import get_store
from utils.spotify import Spotify

app = Quart(__name__)
app.secret_key = str(random.choices(string.printable, k=128))


def set_session_token(token: tk.Token) -> None:
    """Helper function to add the token to the current session

    Parameters
    ----------
    token: tk.Token
        Spotify token. The refresh_token field is saved to the current session.
    """
    session["r_t"] = token.refresh_token


def get_session_token() -> Optional[str]:
    """Helper function to get the current session token.

    Returns
    -------
    str or None: The refresh token string stored in the session
    """
    return session.get("r_t")


def current_track_info(now_playing: Optional[tk.model.CurrentlyPlaying]) -> Dict[str, Union[str, bool]]:
    """Format current track info from Spotify

    This function standardizes the output from spotify's currently_playing api,
    accounting for its unaccountable tendency to return "None."

    Parameters
    ----------
    now_playing: tk.model.CurrentlyPlaying or None
        The object returned from the spotify client

    Returns
    -------
    {str: str or bool}: Formatted dictionary containing the current track, artist,
        device, and album art, as well as whether the player is playing.
    """
    if now_playing is None:
        title = "Not Playing"
        artist = ""
        playing = False
        device = "None"
        art = ""
    else:
        song = now_playing.item
        title = song.name
        artist = ", ".join([artist.name for artist in song.artists])
        playing = now_playing.is_playing
        device = now_playing.device.name
        art = song.album.images[2].url
    return {"title": title, "artist": artist, "playing": playing, "device": device, "art": art}


@app.route("/main", methods=["GET"])
async def main():
    """Display any available information about the main user."""
    try:
        main_token = await app.store.get_token("main")
        logging.info(main_token)
    except:
        return f"No token for main user. Please <a href='{url_for('main_register')}'>log in to register as main user</a>."
    try:
        token = await app.spotify.refresh_token(main_token)
        client = await app.spotify.get_client(token)
    except:
        "Bad token for main user. Please reset and register main user"
    else:
        current_user, now_playing, followers = await asyncio.gather(
            client.current_user(), client.playback(), app.store.list_tokens())
        track_info = current_track_info(now_playing)
        return await render_template("main.html", track_info=track_info, name=current_user.display_name, followers=followers)


@app.route("/main/register")
async def main_register():
    """Register a main user

    Unlike followers, this is separate from the display flow to allow
    easier debugging.
    """
    if await app.store.have_token("main"):
        return f"Already have a main user. Go to <a href='{url_for('main_reset')}'>reset</a> to clear main."
    return redirect(app.spotify.auth_url("main"))


@app.route("/main/reset")
async def main_reset():
    """Deregister a main user."""
    logging.info("Deregistering main user")
    await app.store.delete_token("main")
    return "Reset main"


@app.route("/logout")
async def logout():
    """Delete the tokens in the store matching the session token, if one is present.

    The logout itself is scheduled as a separate task on the event loop because
    quart interrupts the function immediately if the client disconnects.
    """
    async def logout_process(token_str: str):
        """Remove a given token from the store.

        Note we need to get a new client for the token first, since tokens are
        stored by user_id.

        Parameters
        ----------
        token_str: The token string to remove from the store.
        """
        logging.info("Starting logout")
        if not token_str:
            return
        try:
            token = await app.spotify.refresh_token(token_str)
            user_id = await app.spotify.get_user_id(token)
            logging.info("Deregistering %s", user_id)
            await app.store.delete_token(user_id)
        except:
            logging.exception("Failed to deregister user")
    asyncio.create_task(logout_process(get_session_token()))
    return "Logged out."


@app.route("/auth", methods=["GET"])
async def auth():
    """Spotify Auth callback. Expects a 'code' argument on the url."""
    logging.info("[AUTH FLOW] Got code: %s", request.args["code"])
    token = await app.spotify.token_from_code(request.args["code"])
    logging.info("[AUTH FLOW] Got token: %s", token.access_token)
    if request.args["state"] == "main":
        logging.info("[AUTH FLOW] Auth is for main user.")
        await app.store.write_token("main", token.refresh_token)
        logging.info("[AUTH FLOW] Redirect to /main")
        return redirect("/main")
    else:
        logging.info("[AUTH FLOW] Auth is for a follower.")
        logging.info("[AUTH FLOW] refresh token: %s", token.refresh_token)
        set_session_token(token)
        logging.info("[AUTH FLOW] Session cookie: %s", get_session_token())
        user_id = await app.spotify.get_user_id(token)
        await app.store.write_token(user_id, token.refresh_token)
        logging.info("[AUTH FLOW] Redirect to /.")
        return redirect(f"/")


@app.route("/token", methods=["GET"])
async def token():
    """Return an access token generated from the refresh token in the session cookie.

    This endpoint is used by the web player to obtain an updated token.
    """
    logging.info("[AUTH FLOW: Token] Checking Token")
    session_token = get_session_token()
    if not session_token:
        logging.info("[AUTH FLOW: Token] Missing cookie")
        return "Missing cookie", 400
    try:
        token = await app.spotify.refresh_token(session_token)
        user_id = await app.spotify.get_user_id(token)
    except:
        logging.exception("[AUTH FLOW: Token] Couldn't refresh token")
        return "Bad Token", 400
    logging.info("[AUTH FLOW: Token] Got token: %s", token.refresh_token)
    await app.store.write_token(user_id, token.refresh_token)
    set_session_token(token)
    return token.access_token


@app.route('/', methods=["POST", "GET", "PUT"])
async def index():
    """Main index page. Redirects into the auth flow if no session token is found"""
    logging.info("[AUTH FLOW: index] Hit Index")
    session_token = get_session_token()
    if not session_token:
        logging.info(
            "[AUTH FLOW: index] No Session cookie. Redirecting to auth")
        return redirect(app.spotify.auth_url("follow"))
    else:
        logging.info("[AUTH FLOW: index] Session cookie: %s", session_token)
        return await render_template("index.html")


@app.before_serving
async def setup():
    store = await get_store()
    spotify = Spotify()
    app.spotify = spotify
    app.store = store


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default=None,
                        help="Supplemental config file to load")
    args = parser.parse_args()
    if args.config:
        config.load(args.config)
    logging.basicConfig(level=config.LOG_LEVEL)
    app.run()
