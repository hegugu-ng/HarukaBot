import json
import re
import time
import base64
import rsa
from logging import exception
from hashlib import md5
from typing import Any, Dict
from urllib.parse import urlencode

import httpx
from httpx import ConnectTimeout, ReadTimeout, ConnectError
from nonebot.log import logger
from httpx._types import URLTypes

# from ...database import DB


class RequestError(Exception):
    def __init__(self, code, message=None, data=None):
        self.code = code
        self.message = message
        self.data = data
    
    def __repr__(self):
        return f"<RequestError code={self.code} message={self.message}>"
    
    def __str__(self):
        return self.__repr__()


class BiliReq():
    """bilibiliAPI实现"""
    def __init__(self):
        self.appkey = "4409e2ce8ffd12b8"
        self.appsec = "59b43e04ad6965f34319062b478f83dd"
        self.default_headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)\
             AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88\
              Safari/537.36 Edg/87.0.664.60',
            'Referer': 'https://www.bilibili.com/'
        }
        # self.login = Config.get_login()
        self.proxies: Dict[URLTypes, Any] = {'all://': None}

    # TODO 制作一个装饰器捕获请求时的异常并用更友好的方式打印出来
    async def request(self, method, url, **kw) -> Dict:
        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                r = await client.request(method, url, **kw)
                r.encoding = 'utf-8'
                res: Dict = r.json()
            except ConnectTimeout:
                logger.error(f"连接超时（{url}）")
                raise
            except ReadTimeout:
                logger.error(f"接收超时（{url}）")
                raise
            except exception as e:
                logger.error(f"未知错误（url）")
                raise 
            
            # if res['code'] != 0:
            #     raise RequestError(code=res['code'],
            #                         message=res['message'],
            #                         data=res.get('data'))
            return res
    
    async def get(self, url, **kw):
        return await self.request('GET', url, **kw)

    async def post(self, url, **kw):
        return await self.request('POST', url, **kw)
    
    async def get_info(self, uid):
        url = f'https://api.bilibili.com/x/space/acc/info?mid={uid}'
        return await self.get(url, headers=self.default_headers)

    async def _get_sign(self, params):
        '签名'
        items = sorted(params.items())
        return md5(f"{urlencode(items)}{self.appsec}".encode('utf-8')).hexdigest()

    async def _encrypt_pwd(self, pwd):
        '加密密码'
        params = {
            'appkey': self.appkey,
            'ts': int(time.time())
        }
        params['sign'] = await self._get_sign(params)
        url = "https://passport.bilibili.com/api/oauth2/getKey"
        res = await self.post(url, params = params)
        hash_s, rsa_pub = res["data"]["hash"], res["data"]["key"]
        return base64.b64encode(
            rsa.encrypt(
                (hash_s + pwd).encode(),
                rsa.PublicKey.load_pkcs1_openssl_pem(
                    rsa_pub.encode("utf-8")),
            )).decode('ascii')
            
    async def qr_info(self):
        url = "https://passport.bilibili.com/qrcode/getLoginInfo"
        res = await self.post(url)
        return res

    
    async def _pwd_login(self, username, password):
        """
        :说明:

          通过tv端api进行账号密码登录

        :参数:

          * username: 用户名
          * password: 密码

        :返回:
            'code': 状态码
            'mid': UID
            'access_token': 上报token
            'refresh_token': 刷新token
            'expires_in': token 的剩余有效期(秒数)

        """
        params = {
            'appkey': self.appkey,
            'local_id': 0,
            'username': username,
            'ts': int(time.time())
        }

        # 加密
        params['password'] = await self._encrypt_pwd(password)
        params['sign'] = await self._get_sign(params)

        url = "https://passport.bilibili.com/x/passport-tv-login/login"

        res = await self.post(url, params = params)

        if res['code'] != 0:
            return {"code":res['code'], "message":res['message']}
        else:
            res['data']['code'] = res['code']
            return res['data']
    
    async def refresh_token(self, ACCESS_TOKEN, REFRESH_TOKEN):
        """
        :说明:

          获取新的 token (令牌)，同时获得满血 cookie

        :参数:

          * ACCESS_TOKEN: 上报token
          * REFRESH_TOKEN: 刷新token

        :返回:
            'code': 状态码
            'mid': UID
            'access_token': 新的上报token
            'refresh_token': 新的刷新token
            'expires_in': token 的剩余有效期(秒数)
            'bili_jct': bili_jct
            'DedeUserID': DedeUserID
            'DedeUserID__ckMd5': DedeUserID__ckMd5
            'sid': sid
            'SESSDATA': SESSDATA
            'cookie_expires_in': cookie 的到期时间(时间戳)

        :注意:
            cookie 的有效期 (时间戳) 与 token 的到期时间 (秒数) 单位不一样，但都是30天。

        """
        params = {
            'access_token': ACCESS_TOKEN,
            'appkey': self.appkey,
            'refresh_token': REFRESH_TOKEN
        }
        params['sign'] = await self._get_sign(params)

        url = "https://passport.bilibili.com/api/v2/oauth2/refresh_token"
        res = await self.post(url, params = params)
        if res['code'] != 0:
            return {"code":res['code'], "message":res['message']}
        else:
            # 这个返回的东西太多了，这里整理一下，新建一个 dict
            data = {}
            # 把状态码搬下来
            data['code'] = res['code']
            # 把 access_token 和 refresh_token 整出来
            for key in res['data']['token_info']:
                data[key] = res['data']['token_info'][key]
            # 把 cookie 整理出来
            for cookiesdict in res['data']['cookie_info']['cookies']:
                data[cookiesdict['name']] = cookiesdict['value']
                data['cookie_expires_in'] = cookiesdict['expires']
            return data
    
    async def _logout(self, ACCESS_TOKEN):
        """
        :说明:

          登出

        :参数:

          * access_key: 上报token

        :返回:
            'code': 状态码
            'ts': 时间戳
        """
        params = {
            'access_key': ACCESS_TOKEN,
            'appkey': self.appkey
        }
        params['sign'] = await self._get_sign(params)

        url = "https://passport.bilibili.com/api/oauth2/revoke"
        return (await self.post(url, params = params))

    # async def adduser_and_login(self, username, password):
    #     """
    #     :说明:

    #       登录并添加到数据库 先通过给定账号登录，成功后才会添加到数据库。

    #     :参数:

    #       * username: 用户名
    #       * password: 密码

    #     """
    #     # 使用账号密码进行登录
    #     logindata = await self._pwd_login(username,password)
    #     # 如果发生错误 结束并发送异常
    #     if logindata["code"] != 0:
        #     return logindata
        # # 成功则获取账号进一步信息
        # # 先刷新 获取cookie
        # logindata = await self.refresh_token(logindata["access_token"],logindata["refresh_token"])
        # # 如果刷新出错 即刻结束
        # if logindata["code"] != 0:
        #     return logindata
        # async with DB() as db:
        #     await db.add_bilibili(
        #             loginname=username,
        #             password=password,
        #             uid=logindata["mid"],
        #             DedeUserID = logindata["DedeUserID"],
        #             DedeUserID__ckMd5=logindata["DedeUserID__ckMd5"],
        #             SESSDATA=logindata["SESSDATA"],
        #             sid=logindata["sid"],
        #             access_token=logindata["access_token"],
        #             refresh_token=logindata["refresh_token"]
        #         )
        # return True
    
    async def login_info(self, ACCESS_TOKEN):
        """
        :说明:

          查看登录信息

        :参数:

          * ACCESS_TOKEN: 上报token

        :返回:
            'code': 状态码
            'mid': UID
            'access_token': 上报token
            'expires_in': token 的剩余有效期(秒数)
            'userid': userid
            'uname': 用户名
        """
        params = {
            'appkey': self.appkey,
            'access_token': ACCESS_TOKEN
        }
        params['sign'] = await self._get_sign(params)

        url = "https://passport.bilibili.com/api/oauth2/info"
        res = await self.get(url, params = params)
        if res['code'] != 0:
            return {"code":res['code'], "message":res['message']}
        else:
            data = {}
            data['code'] = res['code']
            for key in res['data']:
                data[key] = res['data'][key]
            return data

    async def getflowing(self,cookie):
        """
        获取本账号的全部关注
        """
        uid = cookie['DedeUserID']
        params = {
            'uid':uid,
        }
        params['sign'] = await self._get_sign(params)
        url = f"https://api.vc.bilibili.com/feed/v1/feed/get_attention_list"

        res = await self.get(url, params = params)

        return res
    
    async def dynamic_history(self, cookie,dynamic_id):
        """
        :说明:

          获取指定 dynamic_id 后的历史动态，验证方式 cookie

        :参数:

          * offset_dynamic_id: 指定 dynamic_id
          * cookie：cookie
          * uid：uid
        :返回:
            返回一个包含动态信息的数组，元素为该动态有关信息的字典，最多20条
        """
        uid = cookie['DedeUserID']
        params = {'uid':uid,'type_list':268435455,'offset_dynamic_id':dynamic_id}

        url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/dynamic_history"
        res = await self.get(url, params = params, cookies = cookie)
        if res['code'] != 0:
            return {"code":res['code'], "message":res['message']}
        else:
            # res['data']['code'] = res['code']
            # data = await self.dynamic_json_translate(res)
            return res['data']
    async def dynamic_new(self,cookie, dynamic_id):
        """
        :说明:

          获取指定 dynamic_id 前的动态，验证方式 cookie

        :参数:

          * current_dynamic_id: 指定 dynamic_id
          * cookie：cookie
          * uid：uid
        :返回:
            返回一个包含动态信息的数组，元素为该动态有关信息的字典，最多20条
        """
        uid = cookie['DedeUserID']
        params = {'uid':uid,'type_list':268435455,'current_dynamic_id':dynamic_id}
        url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/dynamic_new"
        res = await self.get(url, params = params, cookies = cookie, headers = self.default_headers)
        if res['code'] != 0:
            return {"code":res['code'], "message":res['message']}
        else:
            # res['data']['code'] = res['code']
            # data = await self.dynamic_json_translate(res)

            # print(data)
            return res['data']


        
        







    