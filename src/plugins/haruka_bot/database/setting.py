from ..utils import get_path
from ..plugins.bilibili_login.database import models as loginmodle

setting = {
    "connections": {
        "bilipassword": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {
                "file_path": get_path('bilipassword.sqlite3')
            }
        }
    },
    "apps": {
        "bilipassword": {
            "models": [locals()['loginmodle']],
            # 链接到的数据库
            'default_connection': 'bilipassword'
        }
    }
}
