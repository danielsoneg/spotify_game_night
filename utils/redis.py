import aioredis

import configparser
import json
import logging
import os

from typing import List

# This is Bad, I'm aware, but it's a transition step to get
# Redis backing work before reworking the backends.
REDIS = None


async def configure(config_path: str) -> None:
    global REDIS
    c = configparser.ConfigParser()
    with open(config_path) as fh:
        c.read_file(fh)
    config = c["REDIS"]
    host = config["HOST"]
    port = config.getint("PORT")
    db = config.getint("DB")
    REDIS = await aioredis.create_redis_pool(
        (host, port),
        db=db,
        encoding="utf-8",
    )
    try:
        REDIS.ping()
    except aioredis.ConnectionClosedError as err:
        logging.exception("Could not connect to Redis!")
        raise  # TODO: Store exceptions
    else:
        logging.info("Connected to redis on %s:%s/%s", host, port, db)


def song_path() -> str:
    return "current_song"


def token_path(user_id: str = "") -> str:
    return f"token/{user_id}"


async def list_tokens() -> List[str]:
    tokens = await REDIS.keys(token_path("*"))
    logging.info(tokens)
    logging.info([token.partition("/")[2] for token in tokens])
    return [token.partition("/")[2] for token in tokens]


async def have_token(user_id: str) -> bool:
    return bool(await REDIS.exists(token_path(user_id)))


async def get_token(user_id: str) -> str:
    token = await REDIS.get(token_path(user_id))
    if not token:
        # TODO: Fix exceptions.
        raise Exception("No token for user %s" % user_id)
    else:
        return token


async def write_token(user_id: str, token: str) -> None:
    await REDIS.set(token_path(user_id), token)


async def delete_token(user_id: str) -> None:
    await REDIS.delete(token_path(user_id))


async def write_song(song_info: str) -> None:
    # TODO: This should be taking a flat dictionary, not JSON
    await REDIS.set(song_path(), song_info)


async def get_song() -> str:
    await REDIS.get(song_path())
