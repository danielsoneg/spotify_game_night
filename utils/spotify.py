"""
Spotify utility functions.

These functions are somewhat opinionated, in that they provide a standard way
of loading spotify clients and tokens. However, they are generally usage-agnostic
and do not perform any of the actual main and follower syncing.
"""
import logging

from typing import Optional, Tuple

import tekore as tk

from utils import config


class Spotify:
    Credentials = None

    Scopes = " ".join((
        "user-read-playback-state",
        "user-modify-playback-state",
        "streaming", "user-read-email", "user-read-private"
    ))

    class BadToken(Exception):
        pass

    class BadClient(Exception):
        pass

    class NoDevices(Exception):
        pass

    def __init__(self):
        """Read the "SPOTIFY" section from the given config path and configure the Credentials object.

        Parameters
        ----------
        config_path: str
            Path to the configuration file.
        """
        client_id = config.SPOTIFY_CLIENT_ID
        client_secret = config.SPOTIFY_CLIENT_SECRET
        redirect_uri = config.SPOTIFY_REDIRECT_URI
        logging.info(redirect_uri)
        self.Credentials = tk.Credentials(
            client_id, client_secret, redirect_uri, asynchronous=True)

    def auth_url(self, state: str) -> str:
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
        return self.Credentials.user_authorisation_url(scope=self.Scopes, state=state)

    ########
    # PLAYBACK
    ########

    async def play_track(self, user: str, client: tk.Spotify, track_id: str, retry: bool = False) -> Tuple[str, bool]:
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
            await client.playback_start_tracks([track_id, ])
            return user, True
        except:
            logging.exception("Error playng track for user %s", user)
            if retry:
                return user, False
            try:
                _, client = await self.get_user(client.token.refresh_token)
                await self.set_device(client)
                return await self.play_track(user, client, track_id, retry=True)
            except:
                logging.exception(
                    "Error refreshing user %s during play attempt", user)
                return user, False

    @staticmethod
    async def stop(client: tk.Spotify) -> None:
        """Stop playback for the given client.

        This function swallows exceptions, since the spotify API throws an error
        when you try to stop an already stopped client, instead of just saying
        "yes sure that's fine" and going and sipping tea or something.

        Parameters
        ----------
        client: tk.Spotify
            Client to stop playback on

        Raises
        ------
        Nothing
        """
        try:
            await client.playback_pause()
        except:
            pass

    async def get_current_track(self, client: tk.Spotify, retry: bool = False) -> Optional[tk.model.CurrentlyPlaying]:
        """Get the currently-playing track.

        This function will retry once, attempting to reload the client to get past
        token freshness issues.

        Parameters
        ----------
        client: tk.Spotify
            Spotify client to query
        retry: bool
            Whether this query is a retry. If False, client will be reloaded and a retry
            will be attempted if Spotify returns Unauthorized.

        Returns
        -------
        tk.model.CurrentlyPlaying or None: Info about the currently playing track. Tekore
            returns None if nothing is playing, so we do as well.

        Raises
        ------
        tk.Unauthorised if the client could not be authorized.
        """
        try:
            current = await client.playback_currently_playing()
        except tk.Unauthorised:
            if retry:
                logging.exception("Could not get current track")
                raise
            _, client = await self.get_user(client.token.refresh_token)
            return await self.get_current_track(client, retry=True)
        if not current:
            return None
        else:
            return current

    #######
    # BASIC USER SETUP
    #######

    async def token_from_code(self, auth_code: str) -> tk.Token:
        """Get a spotify token from an authorization code.

        Parameters
        ----------
        auth_code: str
            Authorization code returned from Spotify.

        Returns
        -------
        tk.Token: Token generated from the authorization code.
        """
        return await self.Credentials.request_user_token(auth_code)

    async def get_user(self, token_str: str) -> Tuple[str, tk.Spotify]:
        """Get a client with a token string

        Parameters
        ----------
        token_str: str
            String of a refresh token.

        Returns
        -------
        (str, tk.Spotify): Tuple of the user's display name and a spotify client. 
        """
        try:
            token = await self.refresh_token(token_str)
            client = await self.get_client(token)
            user = await client.current_user()
        except Exception:
            logging.exception("Could not refresh token")
            raise
        else:
            display_name = user.display_name
            logging.info(f"Got client for {display_name}")
            return display_name, client

    async def get_user_id(self, token: tk.Token) -> str:
        """Return a user's ID from their token.

        Parameters
        ----------
        token: tk.Token
            Spotify Token to query

        Returns
        -------
        str: The user's ID.
        """
        try:
            client = await self.get_client(token)
            user = await client.current_user()
        except Exception:
            logging.exception(f"Could not get client or user from token")
            raise
        else:
            return user.id

    async def refresh_token(self, token_str: str) -> tk.Token:
        """Return a refreshed Token given a token refresh string

        Parameters
        ----------
        token_str: str
            Refresh token string

        Returns
        -------
        tk.Token: A refreshed Token

        Raises
        ------
        BadToken for any issues refreshing the token.
        """
        try:
            token = await self.Credentials.refresh_user_token(token_str)
        except:
            logging.exception("Failed to refresh token")
            raise BadToken("Couldn't refresh token")
        else:
            return token

    @staticmethod
    async def get_client(token: tk.Token) -> tk.Spotify:
        """Get a spotify client from a token.

        Parameters
        ----------
        token: tk.Token
            An up-to-date token to generate a client from

        Returns
        -------
        tk.Spotify: Spotify client

        Raises
        ------
        BadClient for issues creating the client.
        """
        try:
            client = tk.Spotify(token, asynchronous=True)
        except:
            logging.exception("Could not create client")
            raise BadClient("Couldn't create client")
        else:
            return client

    @staticmethod
    async def set_device(client: tk.Spotify, device_name: str = "Game Night") -> None:
        """Set the active device for the client to a device that matches the provided name.

        If multiple matching devices are found, the first one will be used. 

        Parameters
        ----------
        client: tk.Spotify
            Client to set the device on
        device_name: str = "Game Night"
            Name of the device to make active.

        Raises
        ------
        NoDevices if no devices are found.
        """
        devices = await client.playback_devices()
        devices = [device for device in devices if device.name == device_name]
        if not devices:
            raise NoDevices("No valid devices found")
        else:
            device = devices[0].id
            await client.playback_transfer(device)

    #########
    # Utility
    #########

    async def refresh_client(self, client: tk.Spotify) -> tk.Spotify:
        """Return a new client using the given client's token.

        Parameters
        ----------
        client: tk.Spotify
            The client to be refreshed

        Returns
        -------
        tk.Spotify: a new client built from the given client's refresh token.

        Raises
        ------
        BadToken if the client couldn't be refreshed
        """
        try:
            _, client = await self.get_user(client.token.refresh_token)
        except Exception as err:
            logging.exception("Error refreshing client")
            raise BadToken(
                "Could not refresh client using client's token") from err
        else:
            return client

    @staticmethod
    def client_is_good(client: Optional[tk.Spotify], token_str: str) -> bool:
        """Check if a client is still good.

        NOTE: this is not an async function.

        "Good" here means the access token has not expired and matches
        the provided token_str. "None" is allowed as a convenience, if "None"
        is passed in as the client, the function returns False.

        Parameters
        ----------
        client: tk.Spotify or None
            Client to check if we have one.
        token_str: str
            Token from the store to check against the client

        Returns
        -------
        bool: True if provided a client, that client has a token that matches
            the provided string, and the access token has not expired.
        """
        if client is None:
            # We got passed no client, which is obviously bad
            return False
        if token_str != client.token.refresh_token:
            # The token in the client doesn't match the one on disk.
            return False
        if client.token.is_expiring:
            # The access token is 60sec away from expiring
            return False
        return True
