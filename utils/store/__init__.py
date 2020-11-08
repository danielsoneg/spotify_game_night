import importlib

from utils import config


async def get_store():
    store_module = importlib.import_module(
        "utils.store.%s" % config.STORE_NAME)
    store = store_module.Store()
    await store.init()
    return store
