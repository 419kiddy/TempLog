#chennel secret
#a7c24d4ed69fd8b714e639ed8bd4e25f

#UserID
#U026cdb8e7a15bdfc128f8c482973839c

#token
#k0o5m0gn/YSvukOL+aekioyf4+q+4THuo1eGa5s3n4EPzPgkFUzsEJZkHCFCI49riiXB2rK67kq21QlQQF8NpF4Mn/VBvgnf7AXbvs5of74F/mpBOdOBeR4y/mC7Whx8JEeq4AKoxHXsffrWzTyCSgdB04t89/1O/w1cDnyilFU=
#クラウドファンクション上に置いているコードです

import os
import sys
from linebot import LineBotApi
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

TEXT = 'おはようございます。\n今日の体温報告をお願いします。\n半角数字のみで入力してください\n（例： 36.7）'

def get_line_api(credentials):
    return LineBotApi(credentials['channel_access_token'])

def hello_pubsub(event, context):
    try:
        line_bot_api = get_line_api(os.environ)
        line_bot_api.broadcast(TextSendMessage(text=TEXT))
    except:
        print(str(sys.exc_info()))