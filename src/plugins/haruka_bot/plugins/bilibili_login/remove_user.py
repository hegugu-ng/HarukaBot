# 移除并登出哔哩哔哩用户 所需权限必须为 super user
import re

from nonebot import on_command
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp.event import (GroupMessageEvent, MessageEvent,
                                           PrivateMessageEvent)
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from tortoise.backends.base.client import BaseDBAsyncClient

from ...utils import to_me
from .api import BiliReq
from .database import DB

# 使用密码登录账号
remove_user = on_command('登出并删除账号', aliases={'下号', }, rule=to_me(),
                         permission=SUPERUSER,
                         priority=5)
remove_user.__doc__ = """下号 -> 移除并登出B站"""


@remove_user.handle()
async def remove(bot: Bot, event: MessageEvent,
                 state: T_State):
    """登出并删除哔哩哔哩账号"""
    async with DB() as db:
        users = await db.get_alluser()
    if len(users) == 0 or users is None:
        await remove_user.finish("数据库为空")
        await remove_user.stop_propagation()
    strtab = "|    UID     |      用户名      |"
    for user in users:
        strtab = f"{strtab}\n{user.uid}    {user.name}"
    await remove_user.send(strtab)


@remove_user.got("uid", prompt="请输入需要删除的id:\n回复【取消】可以取消操作\n回复【all】可以删除所有")
async def got_loginname(bot: Bot, event: MessageEvent, state: T_State):
    uid = state["uid"]
    if uid == "取消":
        await remove_user.finish("已取消")
    b = BiliReq()
    if uid == "all":
        async with DB() as db:
            users = await db.get_alluser()
            for user in users:
                await b._logout(user.access_token)
                await db.delete_loginuser(user.loginname)
        await remove_user.finish("操作完成")
    async with DB() as db:
        data = await db._get_user(uid=uid)
    if data:
        user = data[0]
        await b._logout(user.access_token)
        await db.delete_loginuser(user.loginname)
        await remove_user.finish("操作完成")
    else:
        await remove_user.reject("不存在的uid，请重试")
