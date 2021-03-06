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