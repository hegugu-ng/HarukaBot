from os import name
from tortoise.models import Model
from tortoise.fields.data import CharField,IntField


class login(Model):
    loginname =  CharField(max_length=30,unique=True)
    password = CharField(max_length=20)
    name = CharField(max_length=16,null = True)
    uid = IntField(unique=True,null = True)
    # DedeUserID 就是uid
    DedeUserID = IntField(unique=True,null = True)
    DedeUserID__ckMd5 = CharField(max_length=32,null = True)
    SESSDATA = CharField(max_length=32,null = True)
    bili_jct = CharField(max_length=32,null = True)
    sid = CharField(max_length=32,null = True)
    access_token = CharField(max_length=32,null = True)
    refresh_token = CharField(max_length=32,null = True)

    class Meta:
        app = "bilipassword"
