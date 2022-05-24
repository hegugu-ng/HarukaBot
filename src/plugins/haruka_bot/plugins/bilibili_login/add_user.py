# 添加哔哩哔哩用户 所需权限必须为 super user
# 使用账号密码登录必须为私聊环境

import re

from nonebot import on_command
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp.event import (GroupMessageEvent, MessageEvent,
                                           PrivateMessageEvent)
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ...utils import to_me
from .api import BiliReq
from .database import DB

# 使用密码登录账号
add_user_password = on_command('登录B站', aliases={'登录b站', '上号'}, rule=to_me(),
                               permission=SUPERUSER,
                               priority=5)
add_user_password.__doc__ = """上号 -> 使用密码登录B站"""


@add_user_password.handle()
async def user_password(bot: Bot, event: MessageEvent,
            state: T_State):
    """使用账号密码登录哔哩哔哩账号"""
    if isinstance(event, GroupMessageEvent):
        await add_user_password.finish("为了你的账号安全，请不要在群里使用账号密码登录bilibili")
        await add_user_password.stop_propagation()


@add_user_password.got("loginname", prompt="请输入用户名:\n回复【取消】可以取消操作哦！")
async def got_loginname(bot: Bot, event: MessageEvent, state: T_State):
    loginname = state['loginname']
    if loginname == "取消":
        await add_user_password.finish("登录已取消~")
        await add_user_password.stop_propagation()

    mail_reg = r"^\w+@(\w+.)+(com|cn|net)$"
    phone_reg = r"^(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}$"
    print(re.match(mail_reg, loginname) is None,
          re.match(phone_reg, loginname) is None)
    if re.match(mail_reg, loginname) is None and re.match(phone_reg, loginname) is None:
        await add_user_password.reject("用户名应该是手机号或者邮箱号哦！\n请重新输入~")
    async with DB() as db:
        data = await db._get_user(loginname=loginname)
    if data:
        b = BiliReq()
        await add_user_password.send(f"用户【{data[0].name}】已经存在数据库中啦!\n不用再登录了哦！\n您可以输入【帮助】\n查看更多账号操作哦！")
        userinfo = await b.login_info(data[0].access_token)
        if userinfo['code'] == -101:
            await add_user_password.send(f"用户【{data[0].name}】登录凭据已过期\n将为您尝试自动刷新")
            testcount = 3
            while testcount:
                password = data[0].password
                logindata = await b._pwd_login(loginname, password)
                if logindata["code"] != 0:
                    await add_user_password.send(f"登录失败！错误是【{logindata['message']}】")
                    if logindata['message'] == "用户名或密码错误":
                        async with DB() as db:
                            await db.delete_loginuser(loginname)
                            await add_user_password.finish(f"检测到密码或登录名被修改，用户【{data[0].name}】将会被删除")
                        break

                else:
                    logindata = await b.refresh_token(logindata["access_token"], logindata["refresh_token"])
                    userinfo = await b.login_info(logindata["access_token"])
                    async with DB() as db:
                        await db.update_loginuser(
                            loginname=loginname,
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
                    await add_user_password.send(f"【{userinfo['uname']}】登录状态刷新成功")
                    break
                testcount -= 1
        if logindata["code"] != 0:
            await add_user_password.finish(f"更新用户【{userinfo['uname']}】登录状态失败，请删除后重新添加再试。")
        await add_user_password.finish(f"用户【{userinfo['uname']}】  UID:{userinfo['mid']}\n登录有效期：{secs2day(userinfo['expires_in'])}")


@add_user_password.got("password", prompt="请输入密码: \n \n回复【取消】可以取消操作哦！")
async def got_pass(bot: Bot, event: MessageEvent, state: T_State):
    loginname = state['loginname']
    password = state['password']
    if password == "取消":
        await add_user_password.finish("登录已取消~")
        await add_user_password.stop_propagation()

    if len(password) > 16 or len(password) < 6:
        await add_user_password.reject("密码应该是6-16位字符组成的哦！\n请重新输入~")
    b = BiliReq()
    logindata = await b._pwd_login(loginname, password)
    if logindata["code"] != 0:
        await add_user_password.finish(f"出错啦！\n 错误是：{logindata['message']}")
    logindata = await b.refresh_token(logindata["access_token"], logindata["refresh_token"])
    if logindata["code"] != 0:
        await add_user_password.finish(f"出错啦！\n 错误是：{logindata['message']}")
    userinfo = await b.login_info(logindata["access_token"])
    async with DB() as db:
        data = await db._get_user(uid=logindata["mid"])
    if data:
        await add_user_password.send("找到相同用户，将会进行覆盖。")
        await db.update_loginuser(
            loginname=loginname,
            password=password,
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
    else:
        await db.add_bilibili(
            loginname=loginname,
            password=password,
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
    await add_user_password.finish(f"登录成功！\n欢迎【{userinfo['uname']}】~")


def secs2day(insecs: int) -> str:
    """秒数转换为天"""
    assert insecs >= 0
    day, hour, min = 24*60*60, 60*60, 60
    days, hours, mins, secs = 0, 0, 0, 0
    timestr = ''
    if insecs >= day:
        days, insecs = divmod(insecs, day)
        timestr += f'{days}天'
    if insecs >= hour:
        hours, insecs = divmod(insecs, hour)
        timestr = f'{timestr}{hours}小时'
    if insecs >= min:
        mins, insecs = divmod(insecs, min)
        timestr += f'{mins}分钟'
    if insecs > 0:
        timestr += f'{insecs}秒'
    return timestr
