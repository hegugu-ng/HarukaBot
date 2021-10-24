# 修改与刷新登录
# 移除并登出哔哩哔哩用户 所需权限必须为 super user
from re import U
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
from .add_user import secs2day

exp_user = on_command('查看账号信息', aliases={'查号', }, rule=to_me(),
                         permission=SUPERUSER,
                         priority=5)
exp_user.__doc__ = """查号 -> 查看登录的B站账号信息"""


@exp_user.handle()
async def exp(bot: Bot, event: MessageEvent,
                 state: T_State):
    """查看已登录账号信息"""
    b = BiliReq()
    async with DB() as db:
        users = await db.get_alluser()
    if len(users) == 0 or users is None:
        await exp_user.finish("数据库为空")
        await exp_user.stop_propagation()
    strtab = "|  UID  |   用户名   |  登录有效期  | 关注人数 |"
    for user in users:
        nav = await b.nav_info(user.access_token)
        userinfo = await b.login_info(user.access_token)
        if userinfo["code"] == -101:
            strtab = strtab + f"\n{user.uid} {user.name} 未登录，请刷新登录"
        else:
            strtab = strtab + f"\n{user.uid} {user.name} {secs2day(userinfo['expires_in'])}  {nav['data']['following']}关注"
    await exp_user.send(strtab)

# 使用密码登录账号
up_user = on_command('更新账号', aliases={'更新账号', }, rule=to_me(),
                         permission=SUPERUSER,
                         priority=5)
up_user.__doc__ = """更新账号 -> 更新B站账号登录有效期"""


@up_user.handle()
async def updat(bot: Bot, event: MessageEvent,
                 state: T_State):
    """登出并删除哔哩哔哩账号"""
    b = BiliReq()
    async with DB() as db:
        users = await db.get_alluser()
    if len(users) == 0 or users is None:
        await up_user.finish("数据库为空")
        await up_user.stop_propagation()
    strtab = "|  UID  |   用户名   |  登录有效期  |"
    for user in users:
        userinfo = await b.login_info(user.access_token)
        if userinfo["code"] == -101:
            strtab = strtab + f"\n{user.uid} {user.name} 未登录，请刷新登录"
        else:
            strtab = strtab + f"\n{user.uid} {user.name} {secs2day(userinfo['expires_in'])}"    
    await up_user.send(strtab)


@up_user.got("uid", prompt="请输入需要更新的id:\n回复【取消】可以取消操作\n回复【all】可以更新所有")
async def got_loginname(bot: Bot, event: MessageEvent, state: T_State):
    uid = state["uid"]
    if uid == "取消":
        await up_user.finish("已取消")
    b = BiliReq()
    if uid == "all":
        async with DB() as db:
            users = await db.get_alluser()
            for user in users:
                logindata = await b.refresh_token(user.access_token, user.refresh_token)
                if logindata["code"] == -101:
                    logindata = await b._pwd_login(user.loginname, user.password)
                    logindata = await b.refresh_token(logindata["access_token"], logindata["refresh_token"])
                userinfo = await b.login_info(logindata["access_token"])
                async with DB() as db:
                    await db.update_loginuser(
                        loginname= user.loginname,
                        name=userinfo['uname'],
                        uid=logindata["mid"],
                        DedeUserID=logindata["DedeUserID"],
                        DedeUserID__ckMd5=logindata["DedeUserID__ckMd5"],
                        SESSDATA=logindata["SESSDATA"],
                        bili_jct=logindata["bili_jct"],
                        sid=logindata["sid"],
                        access_token=logindata["access_token"],
                        refresh_token=logindata["refresh_token"]
                    )
                await up_user.send(f"【{userinfo['uname']}】登录状态刷新成功")
        await up_user.finish("全部操作完成")
    async with DB() as db:
        data = await db._get_user(uid=uid)
    if data:
        user = data[0]
        logindata = await b.refresh_token(user.access_token, user.refresh_token)
        if logindata["code"] == -101:
            logindata = await b._pwd_login(user.loginname, user.password)
            logindata = await b.refresh_token(logindata["access_token"], logindata["refresh_token"])
        userinfo = await b.login_info(logindata["access_token"])
        async with DB() as db:
            await db.update_loginuser(
                loginname= user.loginname,
                name=userinfo['uname'],
                uid=logindata["mid"],
                DedeUserID=logindata["DedeUserID"],
                DedeUserID__ckMd5=logindata["DedeUserID__ckMd5"],
                SESSDATA=logindata["SESSDATA"],
                bili_jct=logindata["bili_jct"],
                sid=logindata["sid"],
                access_token=logindata["access_token"],
                refresh_token=logindata["refresh_token"]
            )
        await up_user.send(f"【{userinfo['uname']}】登录状态刷新成功")
    else:
        await up_user.reject("不存在的uid，请重试")


