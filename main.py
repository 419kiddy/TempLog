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
    MessageEvent, TextMessage, TextSendMessage, FollowEvent, TemplateSendMessage, ConfirmTemplate, PostbackAction, MessageAction, PostbackEvent
)

app = Flask(__name__)

#機密変数へのアクセス
with open('secret.yaml', 'r') as yf:
    cf = yaml.safe_load(yf)
    line_bot_api = LineBotApi(cf["env_variables"]["CHANNEL_ACCESS_TOKEN"])
    handler = WebhookHandler(cf["env_variables"]["CHANNEL_SECRET"])
    JSONF = cf["env_variables"]["JSONF"]
    SPREADSHEET_KEY = cf["env_variables"]["SPREADSHEET_KEY"]

FOLLOW_TEXT = '初めまして。当botは毎朝8時半に体温と健康を確認するメッセージを送信します。安全な生活のためご協力お願いいたします。半角数字で体温を送信すると記録することができます。'

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


#スプレッドシートに書き込み
def write_temp(profile, event):
    ws = connect_gspread(JSONF, SPREADSHEET_KEY)
    write_point = len(ws.col_values(1))+1
    utc_dt = datetime.fromtimestamp(event.timestamp/1000)
    jst_dt = utc_dt + timedelta(hours=9)
    ws.update_cell(write_point, 1, jst_dt.strftime("%Y/%m/%d"))
    ws.update_cell(write_point, 2, jst_dt.strftime("%H:%M:%S"))
    ws.update_cell(write_point, 3, event.postback.data)
    ws.update_cell(write_point, 4, profile.user_id)
    ws.update_cell(write_point, 5, profile.display_name)


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
    confirm_template_message = TemplateSendMessage(
        alt_text='Confirm',
        template=ConfirmTemplate(
            text=event.message.text+'℃を記録します。よろしいですか？',
            actions=[
                PostbackAction(
                    label='OK',
                    data=event.message.text
                ),
                PostbackAction(
                    label='cancel',
                    data='cancel'
                )
            ]
        )
    )
    line_bot_api.reply_message(
        event.reply_token,
        confirm_template_message
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
    
    elif is_float(event.postback.data):
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
