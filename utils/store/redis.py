import aioredis

import json
import logging

from typing import List

from utils import config


class Store:
    async def init(self):
        self._redis = await aioredis.create_redis_pool(
            (config.REDIS_HOST, int(config.REDIS_PORT)),
            db=int(config.REDIS_DB),
            encoding="utf-8",
        )
        try:
            self._redis.ping()
        except aioredis.ConnectionClosedError as err:
            logging.exception("Could not connect to Redis!")
            raise  # TODO: Store exceptions
        else:
            logging.info("Connected to redis on %s:%s/%s",
                         self._redis.address[0], self._redis.address[1], self._redis.db)

    def song_path(self) -> str:
        return "current_song"

    def token_path(self, user_id: str = "") -> str:
        return f"token/{user_id}"

    async def list_tokens(self) -> List[str]:
        tokens = await self._redis.keys(self.token_path("*"))
        logging.info(tokens)
        logging.info([token.partition("/")[2] for token in tokens])
        return [token.partition("/")[2] for token in tokens]

    async def have_token(self, user_id: str) -> bool:
        return bool(await self._redis.exists(self.token_path(user_id)))

    async def get_token(self, user_id: str) -> str:
        token = await self._redis.get(self.token_path(user_id))
        if not token:
            # TODO: Fix exceptions.
            raise Exception("No token for user %s" % user_id)
        else:
            return token

    async def write_token(self, user_id: str, token: str) -> None:
        await self._redis.set(self.token_path(user_id), token)

    async def delete_token(self, user_id: str) -> None:
        await self._redis.delete(self.token_path(user_id))

    async def write_song(self, song_info: str) -> None:
        # TODO: This should be taking a flat dictionary, not JSON
        await self._redis.set(self.song_path(), song_info)

    async def get_song(self) -> str:
        await self._redis.get(self.song_path())
