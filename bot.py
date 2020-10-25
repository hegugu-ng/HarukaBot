#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
import os
from os import path
from nonebot.log import logger, default_format


logger.add(path.join('log', "error.log"),
           rotation="00:00",
           retention='1 week',
           diagnose=False,
           level="ERROR",
           format=default_format)

# You can pass some keyword args config to init function
nonebot.init()
app = nonebot.get_asgi()

nonebot.load_builtin_plugins()
nonebot.load_plugins("src/plugins")

# Modify some config / config depends on loaded configs
# 
# config = nonebot.get_driver().config
# do something...


if __name__ == "__main__":
    nonebot.run(app="bot:app")