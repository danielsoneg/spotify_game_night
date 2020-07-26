import configparser
import os
import asyncio
import aiofiles
import aiofiles.os
import json
import logging

from typing import List

StorePath = "./.store"
_token_dir = "tokens"
_song_path = "current_song"

def configure(config_path):
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

def song_path():
    return f"{StorePath}/{_song_path}"

def token_path(user=""):
    return f"{StorePath}/{_token_dir}/{user}"

async def list_tokens() -> List[str]:
    return os.listdir(token_path())

async def have_token(user: str) -> bool:
    return os.path.isfile(token_path(user))

async def get_token(user: str) -> str:
    async with aiofiles.open(token_path(user)) as fh:
        token = await fh.read()
    return token.strip()

async def write_token(user: str, token: str):
    logging.info("Writing")
    async with aiofiles.open(token_path(user), "w") as fh:
        await fh.write(token)
    return

async def delete_token(user: str):
    path = token_path(user)
    if await have_token(user):
        await aiofiles.os.remove(path)
    return

async def write_song(song_info):
    async with aiofiles.open(song_path(), "w") as fh:
        await fh.write(song_info)

async def get_song():
    async with aiofiles.open(song_path()) as fh:
        song_info = await fh.read()
    return json.loads(song_info)