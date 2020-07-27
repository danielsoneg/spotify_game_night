import asyncio
import json
import logging
import os
import random
import string

import tekore as tk

from quart import Quart, escape, request, redirect, url_for, session, render_template

from utils import store
from utils import spotify

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
app.secret_key = str(random.choices(string.printable, k=128))

config_path = "./config.ini"

spotify.configure(config_path)
store.configure(config_path)

def set_session_token(token):
    session["r_t"] = token.refresh_token

def current_track_info(now_playing):
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
    return {"title": title, "artist": artist, "playing": playing, "device":device, "art":art}


@app.route("/main", methods=["GET"])
async def main():
    try:
        main_token = await store.get_token("main")
    except:
        return f"No token for main user. Please <a href='{url_for('main_register')}'>log in to register as main user</a>."
    try:
        token = await spotify.refresh_token(main_token)
        client = await spotify.get_client(token)
    except:
        "Bad token for main user. Please reset and register main user"
    else:
        current_user, now_playing, followers = await asyncio.gather(
            client.current_user(), client.playback(), store.list_tokens())
        track_info = current_track_info(now_playing)
        return await render_template("main.html", track_info=track_info, name=current_user.display_name, followers=followers)

@app.route("/main/register")
async def main_register():
    if await store.have_token("main"):
        return f"Already have a main user. Go to <a href='{url_for('main_reset')}'>reset</a> to clear main."
    return redirect(spotify.auth_url("main"))
        

@app.route("/main/reset")
async def main_reset():
    logging.info("Deregistering main user")
    await store.delete_token("main")
    return "Reset main"

@app.route("/logout")
async def logout():
    async def logout_process(token_str):
        logging.info("Starting logout")
        if not token_str:
            return
        try:
            token = await spotify.refresh_token(token_str)
            user_id = await spotify.get_user_id(token)
            logging.info("Deregistering %s", user_id)
            await store.delete_token(user_id)
        except:
            logging.exception("Failed to deregister user")
    asyncio.create_task(logout_process(session.get("r_t")))
    return "Logged out."

@app.route("/auth", methods=["GET"])
async def auth():
    logging.info("[AUTH FLOW] Got code: %s", request.args["code"])
    token = await spotify.token_from_code(request.args["code"])
    logging.info("[AUTH FLOW] Got token: %s", token.access_token)
    if request.args["state"] == "main":
        logging.info("[AUTH FLOW] Auth is for main user.")
        await store.write_token("main", token.refresh_token)
        logging.info("[AUTH FLOW] Redirect to /main")
        return redirect("/main")
    else:
        logging.info("[AUTH FLOW] Auth is for a follower.")
        logging.info("[AUTH FLOW] refresh token: %s", token.refresh_token)
        set_session_token(token)
        logging.info("[AUTH FLOW] Session cookie: %s", session["r_t"])
        user_id = await spotify.get_user_id(token)
        await store.write_token(user_id, token.refresh_token)
        logging.info("[AUTH FLOW] Redirect to /.")
        return redirect(f"/")

@app.route("/token", methods=["GET"])
async def token():
    logging.info("[AUTH FLOW: Token] Checking Token")
    if not session.get("r_t"):
        logging.info("[AUTH FLOW: Token] Missing cookie")
        return "Missing cookie", 400
    try:
        token = await spotify.refresh_token(session["r_t"])
        user_id = await spotify.get_user_id(token)
    except:
        logging.exception("[AUTH FLOW: Token] Couldn't refresh token")
        return "Bad Token", 400
    logging.info("[AUTH FLOW: Token] Got token: %s", token.refresh_token)
    await store.write_token(user_id, token.refresh_token)
    set_session_token(token)
    return token.access_token

@app.route('/', methods=["POST", "GET", "PUT"])
async def index():
    logging.info("[AUTH FLOW: index] Hit Index")
    if not session.get("r_t"):
        logging.info("[AUTH FLOW: index] No Session cookie. Redirecting to auth")
        return redirect(spotify.auth_url("follow"))
    else:
        logging.info("[AUTH FLOW: index] Session cookie: %s", session.get("r_t"))
        return await render_template("index.html")

if __name__ == "__main__":
    app.run()
