import os
import logging
import json
import tekore as tk
from quart import Quart, escape, request, redirect, url_for, session, render_template

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
app.secret_key = "asdfjdashlgjsad"

client_id, client_secret, redirect_uri = tk.config_from_file("./config.ini")
creds = tk.RefreshingCredentials(client_id, client_secret, redirect_uri)

scopes = " ".join((
    "user-read-playback-state",
    "user-modify-playback-state",
    "streaming", "user-read-email", "user-read-private"
    ))

def write_tokens(user, token):
    logging.info(f"Asked to write tokens for {user}")
    with open(f"tokens/{user}", "w") as fh:
        fh.write(token.refresh_token)

def get_main_token():
    logging.info(f"Asked to read main token")
    with open("tokens/main") as fh:
        return fh.read().strip()

@app.route("/main", methods=["GET"])
async def main():
    try:
        token = creds.refresh_user_token(get_main_token())
        spotify = tk.Spotify(token)
    except:
        return redirect(creds.user_authorisation_url(scope=scopes, state="main"))
    else:
        current_user = spotify.current_user()
        now_playing = spotify.playback()
        return f"{current_user}\n{now_playing}"

@app.route("/main/reset")
async def main_reset():
    logging.info("ok, delete?")
    os.unlink("./tokens/main")
    return "Reset main"

#@app.route("/main/nowplaying")
#def main_np():

@app.route("/logout")
async def logout():
    try:
        token = creds.refresh_user_token(session["r_t"])
        user = tk.Spotify(token).current_user().id
        if user:
            os.unlink(f"./tokens/{user}")
    except:
        return "Could not log out. Are you sure you're logged in?"
    else:
        return "Logged out."

@app.route("/auth", methods=["GET"])
async def auth():
    logging.warning("Got code: %s", request.args["code"])
    token = creds.request_user_token(request.args["code"])
    logging.warning(token.access_token)
    if request.args["state"] == "main":
        logging.info("state = main")
        write_tokens("main", token)
        return redirect("/main")
    else:
        logging.info("state != main")
        logging.info("refresh token: %s", token.refresh_token)
        set_session_token(token)
        logging.info(session["r_t"])
        user = tk.Spotify(token).current_user().id
        await write_tokens(user, token)
        logging.info("OK here we are")
        return redirect(f"/")

def set_session_token(token):
    session["r_t"] = token.refresh_token

@app.route("/token", methods=["GET"])
async def token():
    if not session.get("r_t"):
        return "Missing Token", 400
    try:
        token = creds.refresh_user_token(session["r_t"])
    except:
        return "Bad Token", 400
    set_session_token(token)
    return token.access_token

@app.route('/', methods=["POST", "GET", "PUT"])
async def do_auth():
    logging.info("Back here")
    logging.info(session.get("r_t"))
    if not session.get("r_t"):
        return redirect(creds.user_authorisation_url(scope=scopes, state="follow"))
    else:
        logging.info("Else...")
        return await render_template("index.html")

if __name__ == "__main__":
    app.run()
