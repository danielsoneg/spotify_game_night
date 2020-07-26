import asyncio
import os
import logging
import json
import tekore as tk
from quart import Quart, escape, request, redirect, url_for, session, render_template

from utils import store
from utils import spotify

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
app.secret_key = "asdfjdashlgjsad"

config_path = "./config.ini"

spotify.configure(config_path)
store.configure(config_path)

def set_session_token(token):
    session["r_t"] = token.refresh_token

@app.route("/main", methods=["GET"])
async def main():
    try:
        main_token = await store.get_token("main")
    except:
        return "No token for main user. Please register a main user."
    try:
        token = await spotify.refresh_token(main_token)
        client = await spotify.get_client(token)
    except:
        "Bad token for main user. Please reset and register main user"
    else:
        current_user, now_playing = await asyncio.gather(
            client.current_user(), client.playback())
        return f"{current_user}\n{now_playing}"

@app.route("/main/register")
async def main_register():
    if await store.have_token("main"):
        return f"Already have a main user. Go to <a href='{url_for('main_reset')}'>reset</a> to clear main."
    return redirect(spotify.auth_url())
        

@app.route("/main/reset")
async def main_reset():
    logging.info("ok, delete?")
    await store.delete_token("main")
    return "Reset main"

#@app.route("/main/nowplaying")
#def main_np():

@app.route("/logout")
async def logout():
    try:
        token = await spotify.get_token(session["r_t"])
        user_id = await spotify.get_user_id(token)
        await store.delete_token(user)
    except:
        return "Could not log out. Are you sure you're logged in?"
    else:
        return "Logged out."

@app.route("/auth", methods=["GET"])
async def auth():
    logging.warning("Got code: %s", request.args["code"])
    token = await spotify.token_from_code(request.args["code"])
    logging.warning(token.access_token)
    if request.args["state"] == "main":
        logging.info("state = main")
        await store.write_token("main", token.refresh_token)
        return redirect("/main")
    else:
        logging.info("state != main")
        logging.info("refresh token: %s", token.refresh_token)
        set_session_token(token)
        logging.info(session["r_t"])
        user_id = await spotify.get_user_id(token)
        await store.write_token(user_id, token.refresh_token)
        logging.info("OK here we are")
        return redirect(f"/")

@app.route("/token", methods=["GET"])
async def token():
    if not session.get("r_t"):
        logging.info("Missing token")
        return "Missing Token", 400
    try:
        token = await spotify.refresh_token(session["r_t"])
        user_id = await spotify.get_user_id(token)
    except:
        logging.exception("Couldn't refresh token")
        return "Bad Token", 400
    await store.write_token(user_id, token.refresh_token)
    set_session_token(token)
    return token.access_token

@app.route('/', methods=["POST", "GET", "PUT"])
async def do_auth():
    logging.info("Back here")
    logging.info(session.get("r_t"))
    if not session.get("r_t"):
        logging.info("Redirecting")
        return redirect(spotify.auth_url("follow"))
    else:
        return await render_template("index.html")

if __name__ == "__main__":
    app.run()
