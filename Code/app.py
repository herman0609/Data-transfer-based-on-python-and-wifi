import socketserver

from flask import Flask, request, jsonify
from flask import render_template
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError
import json
import datetime

app = Flask(__name__)
user_socket_dict = {}

# 提示消息
records = [{
    "type": 1,
    "nickName": "【系统提示】",
    "msg": "为了区分传输主机，请在发送时填写主机名称！",
    "dateTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
}]


# 解析消息体:     主机:消息
def parseMsg(msgObject):
    if msgObject is None or msgObject == "":
        return None
    index = str(msgObject).find(":")
    if index == -1:
        return None
    msgStr = str(msgObject)[index + 1:]
    if msgStr.strip() == "":
        return None
    msg = {
        "type": 1,
        "nickName": str(msgObject)[:index],
        "msg": msgStr,
        "dateTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    records.append(msg)
    return msg

def user_msg_handler(user_msg):
    try:
        msgObject = parseMsg(user_msg)
        if msgObject is None:
            return False
        jsonMsg = json.dumps(msgObject)
        for user_name, u_socket in user_socket_dict.items():
            u_socket.send(jsonMsg)
        return True
    except WebSocketError:
        return False

def sys_msg_handler(sys_msg, sys_data):
    try:
        if sys_msg is None or sys_data is None:
            return False
        jsonMsg = json.dumps({
            "msg": sys_msg,
            "data": sys_data,
            "type": 0
        })
        for user_name, u_socket in user_socket_dict.items():
            u_socket.send(jsonMsg)
        return True
    except WebSocketError:
        return False


def record_msg_handler(user_socket):
    try:
        if len(records) == 0:
            return False
        jsonMsg = json.dumps({
            "type": 2,
            "data": records
        })
        user_socket.send(jsonMsg)
        return True
    except WebSocketError:
        return False


@app.route('/ws/<username>')
def socket(username):
    user_socket = request.environ.get("wsgi.websocket")
    if not user_socket:
        return "NO WEBSOCKET"

    user_socket_dict[username] = user_socket
    sys_msg_handler(f"当前主机数量：{len(user_socket_dict)}", [k for k, v in user_socket_dict.items()])
    record_msg_handler(user_socket)
    print(f"{username} into ...")
    print("当前主机数量:", len(user_socket_dict))
    while True:
        try:
            user_msg = user_socket.receive()
        except WebSocketError:
            break
        if user_msg_handler(user_msg) == False:
            continue
    user_socket_dict.pop(username)
    sys_msg_handler(f"当前主机数量：{len(user_socket_dict)}", [k for k, v in user_socket_dict.items()])
    print("剩余主机数量:", len(user_socket_dict))
    return "close"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users')
def get_user_list():
    return jsonify([k for k, v in user_socket_dict.items()])


if __name__ == '__main__':
    server = pywsgi.WSGIServer(("0.0.0.0", 80), app, handler_class=WebSocketHandler)
    print("web server start ... ")
    server.serve_forever()
