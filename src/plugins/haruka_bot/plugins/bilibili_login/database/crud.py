from tortoise.query_utils import Q
from tortoise.queryset import QuerySet
from typing import Optional

from .models import login


class DB:
    """数据库交互类，与增删改查无关的部分不应该在这里面实现"""
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _get_user(self,
                  uid: Optional[int] = None,
                  loginname: Optional[str] = None,
                  name: Optional[str] = None) -> QuerySet[login]:
        """获取指定的用户数据"""
        kw = locals()
        del kw['self']
        filters = [Q(**{key: value}) for key, value in kw.items()
                   if value != None]
        return login.filter(Q(*filters, join_type='AND'))

    async def add_bilibili(self,
                           loginname: str,
                           password: str,
                           name: str,
                           uid: int,
                           DedeUserID: int,
                           DedeUserID__ckMd5: str,
                           SESSDATA: str,
                           bili_jct: str,
                           sid: str,
                           access_token: str,
                           refresh_token: str) -> bool:
        "给数据库中添加登录用户 - 增"
        if await self._get_user(uid, loginname):
            # 已经存在这个用户了
            return False

        await login.create(
            loginname=loginname,
            name=name,
            password=password,
            uid=uid,
            DedeUserID=DedeUserID,
            DedeUserID__ckMd5=DedeUserID__ckMd5,
            SESSDATA=SESSDATA,
            bili_jct=bili_jct,
            sid=sid,
            access_token=access_token,
            refresh_token=refresh_token
        )
        return True

    async def delete_loginuser(self, loginname: Optional[str]) -> bool:
        """删除用户 - 删"""
        await login.filter(loginname=str(loginname)).delete()
        return True

    async def update_loginuser(self,
                               uid: Optional[int] = None,
                               loginname: Optional[str] = None,
                               name: Optional[str] = None,
                               password: Optional[str] = None,
                               DedeUserID: Optional[int] = None,
                               DedeUserID__ckMd5: Optional[str] = None,
                               SESSDATA: Optional[str] = None,
                               bili_jct: Optional[str] = None,
                               sid: Optional[str] = None,
                               access_token: Optional[str] = None,
                               refresh_token: Optional[str] = None):
        """更新已有用户的各项数据 - 改"""
        kw = locals()
        del kw['self']
        filters = {key: value for key, value in kw.items()
                   if value != None}
        query = login.filter(Q(loginname=loginname))
        await query.update(**filters)
        return True

    async def get_loginuser(self,  uid: Optional[int], loginname: Optional[str], name: Optional[str]):
        """获取指定位置的用户信息 - 查"""
        return await self._get_user(uid, loginname, name).first()

    @classmethod
    async def get_alluser(cls):
        """获取全部登录账号"""

        user = await login.all()

        return user

    @classmethod
    async def get_allcookie(cls):
        users = await login.all()
        if len(users) == 0 or users is None:
            return None

        return [
            {
                "DedeUserID": str(user.DedeUserID),
                "DedeUserID__ckMd5": user.DedeUserID__ckMd5,
                "SESSDATA": user.SESSDATA,
                "bili_jct": user.bili_jct,
                "sid": user.sid,
                "access_token": user.access_token,
                "refresh_token": user.refresh_token,
            }
            for user in users
        ]
