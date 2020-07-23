import os
import logging
import json
import tekore as tk
from flask import Flask, escape, request, redirect, url_for, session, render_template

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "asdfjdashlgjsad"

client_id, client_secret, redirect_uri = tk.config_from_file("./config.ini")
creds = tk.RefreshingCredentials(client_id, client_secret, redirect_uri)

scopes = " ".join((
    "user-read-playback-state",
    "user-modify-playback-state",
    "streaming", "user-read-email", "user-read-private"
    ))

def write_tokens(user, token):
    with open(f"tokens/{user}", "w") as fh:
        fh.write(token.refresh_token)

def get_main_token():
    with open("tokens/main") as fh:
        return fh.read().strip()

@app.route("/main", methods=["GET"])
def main():
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
def main_reset():
    logging.info("ok, delete?")
    os.unlink("./tokens/main")
    return "Reset main"

#@app.route("/main/nowplaying")
#def main_np():

@app.route("/auth", methods=["GET"])
def auth():
    logging.warn("Got token: ", request.args)
    token = creds.request_user_token(request.args["code"])
    logging.warn(token.access_token)
    if request.args["state"] == "main":
        write_tokens("main", token)
        return redirect("/main")
    else:
        set_session_token(token)
        user = tk.Spotify(token).current_user().id
        write_tokens(user, token)
        return redirect(f"/")

def set_session_token(token):
    session["r_t"] = token.refresh_token

@app.route("/token", methods=["GET"])
def token():
    if not session.get("r_t"):
        return "Missing Token", 400
    try:
        token = creds.refresh_user_token(session["r_t"])
    except:
        return "Bad Token", 400
    set_session_token(token)
    return token.access_token

@app.route('/', methods=["POST", "GET", "PUT"])
def do_auth():
    if not session.get("r_t"):
        return redirect(creds.user_authorisation_url(scope=scopes, state="follow"))
    else:
        return render_template("index.html")



@app.route("/player")
def player():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
