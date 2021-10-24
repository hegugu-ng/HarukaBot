# -*- coding:utf-8 -*-

from . import models
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError

from ..utils import get_path

from .setting import setting

# hb的基本数据库名称为 default,且此名称不能被用户使用
if 'default' in setting['connections'].keys():
    raise ConfigurationError("您不能将数据库命名为 default，请您更换名称")

# hb的基本数据库模型名称为 default,且此名称不能被用户注册
if 'default' in setting["apps"].keys():
    raise ConfigurationError("您不能将数据模型注册为 default，请您更换名称")

# 初始化 hb 数据库
setting["connections"]['default'] = {
    # engine 声明了数据库引擎类型 后续可以更换为 mysql 等其他数据库
    "engine": 'tortoise.backends.sqlite',
    # credentials 声明了数据库的配置选项 ip 端口 账号 密码 每种数据库的配置项不同，具体见文档
    "credentials": {
        "file_path": get_path('data.sqlite3')
    }
}

# 初始化 hb 数据库模型

setting["apps"]['default'] = {
    "models": [locals()['models']],
    # 链接到的数据库
    'default_connection': 'default'
}


async def get_db_session():
    '''数据库初始化方法'''
    print(setting)
    await Tortoise.init(config=setting)
    await Tortoise.generate_schemas()
    database =  {name: Tortoise.get_connection(name) for name in setting['connections'].keys()}
    print(database)
    return database
