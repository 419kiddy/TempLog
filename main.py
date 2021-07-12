from flask import Flask, request, abort

from oauth2client.service_account import ServiceAccountCredentials
import gspread
import json
import yaml
from datetime import datetime, timedelta

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FollowEvent, TemplateSendMessage, ConfirmTemplate, PostbackAction, MessageAction, PostbackEvent, ButtonsTemplate
)

app = Flask(__name__)

#機密変数へのアクセス
with open('secret.yaml', 'r') as yf:
    cf = yaml.safe_load(yf)
    line_bot_api = LineBotApi(cf["env_variables"]["CHANNEL_ACCESS_TOKEN"])
    handler = WebhookHandler(cf["env_variables"]["CHANNEL_SECRET"])
    JSONF = cf["env_variables"]["JSONF"]
    SPREADSHEET_KEY = cf["env_variables"]["SPREADSHEET_KEY"]

FOLLOW_TEXT = '初めまして。当botは毎朝8時半に体温と健康を確認するメッセージを送信します。安全な生活のためご協力お願いいたします。\n半角数字で体温を送信後、体調不良の有無を確認します。記録には数秒かかるため連打は避けるようお願いします。'

#スプレッドシートと接続
def connect_gspread(jsonf, key):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(jsonf, scope)
    gc = gspread.authorize(credentials)
    SPREADSHEET_KEY = key
    worksheet = gc.open_by_key(SPREADSHEET_KEY).sheet1
    return worksheet


#少数かどうかチェック
def is_float(string):
    try:
        float(string)  # 文字列をfloatにキャスト
        return True
    except ValueError:
        return False

def get_health(string):
    index = string.find("&")
    return string[index+1:]

def get_temp(string):
    index = string.find("&")
    return string[:index]

#スプレッドシートに書き込み
def write_temp(profile, event):
    ws = connect_gspread(JSONF, SPREADSHEET_KEY)
    write_point = len(ws.col_values(1))+1
    utc_dt = datetime.fromtimestamp(event.timestamp/1000)
    jst_dt = utc_dt + timedelta(hours=9)
    ws.update_cell(write_point, 1, jst_dt.strftime("%Y/%m/%d"))
    ws.update_cell(write_point, 2, jst_dt.strftime("%H:%M:%S"))
    ws.update_cell(write_point, 3, get_temp(event.postback.data))
    ws.update_cell(write_point, 4, profile.user_id)
    ws.update_cell(write_point, 5, profile.display_name)
    ws.update_cell(write_point, 6, get_health(event.postback.data))


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    buttons_template_message = TemplateSendMessage(
        alt_text='健康観察',
        template=ButtonsTemplate(
            type="buttons",
            text=event.message.text+'℃を記録します。ご自身または同居人に風邪の症状、倦怠感、息苦しさ、嗅覚・味覚異常、だるさに当てはまる症状がある、濃厚接触者がいる場合は体調不良有りを選んでください。(押してから数秒かかります。)', 
            actions=[
                PostbackAction(
                    label='体調不良無し',
                    data=event.message.text+"&fine"
                ),
                PostbackAction(
                    label='体調不良有り',
                    data=event.message.text+"&sick"
                ),
                PostbackAction(
                    label='cancel',
                    data='cancel'
                )
            ]
        )
    )
    if is_float(get_temp(event.message.text)) :
        line_bot_api.reply_message(
            event.reply_token,
            buttons_template_message
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="まず初めに体温を送ってください。半角数字・小数点のみ対応しています。"
            )
        )



@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=FOLLOW_TEXT)
    )


@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == 'cancel':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="キャンセルされました。"
            )
        )
    
    elif is_float(get_temp(event.postback.data)):
        profile = line_bot_api.get_profile(event.source.user_id)
        write_temp(profile, event)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="記録が完了しました。"
            )
        )
    
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="書式を確認してください。半角数字・小数点のみ対応しています。"
            )
        )


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)
