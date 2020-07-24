import os
import asyncio
import aiofiles
import aiofiles.os
import logging

from typing import List

token_dir = "tokens"
song_path = "current_song"

def token_path(user):
    return f"./{token_dir}/{user}"

async def list_tokens() -> List[str]:
    return os.listdir(token_dir)

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

async def write_song(title):
    async with aiofiles.open(f"./{song_path}", "w") as fh:
        logging.info("Writing song title: %s", title)
        await fh.write(title)
    return

async def get_song(title):
    async with aiofiles.open(f"./{song_path}") as fh:
        return fh.read()
