import logging
import json
import tekore as tk
from flask import Flask, escape, request, redirect, url_for, session, render_template

app = Flask(__name__)
app.secret_key = "asdfjdashlgjsad"

client_id, client_secret, redirect_uri = tk.config_from_file("./config.ini")
creds = tk.RefreshingCredentials(client_id, client_secret, redirect_uri)

scopes = (
    "user-read-playback-state",
    "user-modify-playback-state",
    "streaming", "user-read-email", "user-read-private"
    )

def write_tokens(user, token):
    with open(f"tokens/{user}", "w") as fh:
        fh.write(token.refresh_token)

@app.route("/auth", methods=["GET"])
def auth():
    logging.warn("Got token: ", request.args)
    token = creds.request_user_token(request.args["code"])
    logging.warn(token)
    set_session_token(token)
    logging.warn(token.access_token)
    user = tk.Spotify(token).current_user().id
    write_tokens(user, token)
    return redirect(f"/player")

def set_session_token(token):
    session["r_t"] = token.refresh_token

@app.route("/token", methods=["GET"])
def token():
    if not session.get("r_t"):
        return "Missing Token", 400
    token = creds.refresh_user_token(session["r_t"])
    set_session_token(token)
    return token.access_token

@app.route('/', methods=["POST", "GET", "PUT"])
def do_auth():
    if not session.get("r_t"):
        return redirect(creds.user_authorisation_url(scope=scopes))
    else:
        return redirect(url_for("player"))

@app.route("/player")
def player():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
