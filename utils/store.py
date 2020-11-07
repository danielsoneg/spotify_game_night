"""
Store for user tokens and current song.

If this were a production service, this is the module that would
handle reading and writing from the datastore. In this service,
it reads and writes from the filesystem.
"""
import aiofiles
import aiofiles.os
import asyncio
import configparser
import json
import logging
import os

from typing import List

StorePath = "./.store"
_token_dir = "tokens"
_song_path = "current_song"


async def configure(config_path: str) -> None:
    """Configure the store.

    Reads the "path" configuration from the STORE section
    of the given config file. Creates the directories if necessary.

    Parameters
    ----------
    config_path: str
        Path to the configuration file.
    """
    global StorePath
    c = configparser.ConfigParser()
    with open(config_path) as fh:
        c.read_file(fh)
    store_path = c["STORE"]["path"]
    if not os.path.isdir(store_path):
        os.mkdir(store_path)
    if not os.path.isdir(token_path()):
        os.mkdir(token_path())
    StorePath = store_path


def song_path() -> str:
    """Convenience method to get the song path"""
    return f"{StorePath}/{_song_path}"


def token_path(user_id: str = "") -> str:
    """Convenience method to get the path to a token for a given user

    Note this does not check if the token exists.

    Parameters
    ----------
    user_id: str
        ID of the user

    Returns
    -------
    str: File path of the user's token.
    """
    return f"{StorePath}/{_token_dir}/{user_id}"


async def list_tokens() -> List[str]:
    """List all user IDs for which we have a token.

    Returns
    -------
    List[str]: List of user IDs
    """
    return os.listdir(token_path())


async def have_token(user_id: str) -> bool:
    """Check if we have a token for a given user ID.

    Parameters
    ----------
    user_id: str
        User ID to check

    Returns
    -------
    bool: True if we have a token for the user.
    """
    return os.path.isfile(token_path(user_id))


async def get_token(user_id: str) -> str:
    """Get the token for a given user ID.

    Parameters
    ----------
    user_id: str
        User to get token for

    Returns
    -------
    str: token string

    Raises
    ------
    Standard python errors for reading a file.
    """
    async with aiofiles.open(token_path(user_id)) as fh:
        token = await fh.read()
    return token.strip()


async def write_token(user_id: str, token: str) -> None:
    """Write a token for a given user ID.

    Parameters
    ----------
    user_id: str
        User to write token for
    token: str
        Token to write

    Raises
    ------
    Standard python errors for writing a file.
    """
    logging.info("Writing")
    async with aiofiles.open(token_path(user_id), "w") as fh:
        await fh.write(token)


async def delete_token(user_id: str) -> None:
    """Delete a token for a given user ID.

    Parameters
    ----------
    user_id: str
        User to delete token for

    Raises
    ------
    Standard python errors for deleting a file.
    """
    path = token_path(user_id)
    if await have_token(user_id):
        await aiofiles.os.remove(path)


async def write_song(song_info: str) -> None:
    """Write the current song information to disk.

    song_info is expected to be in JSON form. It is JSON and not
    an object because tekore's .json() method produces strings.
    However, the method will happily write whatever string you provide,
    and then just as happily fail when you try to read it later.

    Parameters
    ----------
    song_info: str
        JSON blob to write out

    Raises
    ------
    Standard Python errors for writing files.
    """
    async with aiofiles.open(song_path(), "w") as fh:
        await fh.write(song_info)


async def get_song() -> str:
    """Read song information from disk.

    The song information is assumed to be a json encoded object.

    Returns
    -------
    dict or encodable: parsed representation of stored data.

    Raises
    ------
    Standard python errors for reading a file, standard json errors
    for unparseable strings.
    """
    async with aiofiles.open(song_path()) as fh:
        song_info = await fh.read()
    return json.loads(song_info)
