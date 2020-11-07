"""
NOTE: This is not a production-friendly way to do things, but it's a fast way,
and it's kind of clever and fun.

Module provides a config object that can either read from config files or
environment variable or both (preferring environment varaibles).

Usage:
    $ REDIS_DB=1 python
    >>> from utils import config
    >>> config.REDIS_DB
    '1'

    $ cat config.ini
    [REDIS]
    HOST = 127.0.0.1
    $ python
    >>> from utils import config
    >>> config.load("config.ini")
    >>> config.REDIS_HOST
    '127.0.0.1'
"""
import configparser
import os
import sys
from types import ModuleType


class ConfigModule(ModuleType):
    __config_object = configparser.ConfigParser()

    def load(self, config_file=None):
        if config_file:
            with open(config_file) as fh:
                self.__config_object.read_file(fh)

    def __getattr__(self, attr):
        if "_" in attr and attr != "__config_object":
            if attr in os.environ:
                return os.environ[attr]
            section, _, key = attr.partition("_")
            if section in self.__config_object:
                if key in self.__config_object[section]:
                    return self.__config_object[section][key]
        raise AttributeError("'%s' object has no attribute %s" %
                             (self.__class__.__name__, attr))


sys.modules[__name__].__class__ = ConfigModule
