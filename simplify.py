# -*- coding: utf-8 -*-
from akad.ttypes import Message
import threading,json
from collections import OrderedDict

class Simplify(object):
    CmdInterrupt = {}
    default = ""
    cmds = {}
    types = {}
    perms = {}
    users = {}
    
    """ Main """

    def __init__(self,client,default="ROM",prefix="!",cmds=None,types=None,perms=None,users=None,datas=None):
        self.err_msgs= {}
        self.prefix = prefix
        self.default = default
        if datas:
            self.prefix = datas['Prefix']
            self.cmds = datas['Commands']
            self.types = datas['Types']
            self.perms = datas['Permissions']
            self.users = datas['Users']
        elif cmds and types and perms and users:
            self.cmds = cmds
            self.types = types
            self.perms = perms
            self.users = users
        else:
            raise ValueError("Not enough arguments")
        self.cl = client
        
    #権限確認
    def perm_chk(self,cmd,user):
        #ユーザーリストに入っていなければ初期化
        if user not in self.users:
            self.users[user] = OrderedDict()
            self.users[user]["Permission"] = self.default
            self.users[user]["Count"] = OrderedDict()
        if cmd not in self.users[user]["Count"]:
            self.users[user]["Count"][cmd] = 1
        else:
            self.users[user]["Count"][cmd] += 1
        #権限が設定されていなければ誰でも使用可
        if cmd not in self.perms:
            return True
        else:
            #権限制限に指定された権限が入っていなければ使用不可
            if self.users[user]["Permission"] not in self.perms[cmd]:
                return False
            #入っているならカウント制限があれば確認
            if self.users[user]["Count"][cmd] <= self.perms[cmd][self.users[user]["Permission"]] or (self.users[user]["Permission"] in self.perms[cmd] and self.perms[cmd][self.users[user]["Permission"]] == -1):
                return True
            else:
                return False
                
    def process_reply(self,cmd,_msg):
        cmd_body = self.cmds[cmd]["body"]
        #権限確認
        if self.perm_chk(cmd,_msg._from):
            #グル返信有効 かつ グルからのメッセージ
            if "group" not in self.cmds[cmd] and "user" not in self.cmds[cmd]:
                if _msg.toType == 0 or "to" in self.cmds[cmd]: _msg.to = _msg._from
                self.send_reply(_msg.to,cmd_body,_msg)
            elif self.cmds[cmd]["group"] == True and _msg.toType == 2:
                #送信先がuser固定なら 送り先を_msg._fromにする
                if "to" in self.cmds[cmd]: _msg.to = _msg._from
                #送り先と内容を指定して処理
                self.send_reply(_msg.to,cmd_body,_msg)
            #ユーザー返信有効 かつ ユーザーからのメッセージ
            elif self.cmds[cmd]["user"] == True and _msg.toType == 0:
                try:
                    print(self.users[msg._from]["Count"][cmd])
                except:
                    pass
                self.send_reply(_msg._from,cmd_body,_msg)
        else:
            #実行できなかった場合
            if self.users[_msg._from]["Count"][cmd] >= self.perms[cmd][self.users[_msg._from]["Permission"]]:
                self.cl.sendMessage(_msg._from,"使用回数制限に達しました")
            else:
                self.cl.sendMessage(_msg._from,"あなたには権限がありません")
                
    #返信するかどうかの処理
    def reply(self,_msg):
        bye = False
        if _msg.contentType == 0:
            for cmd in self.cmds:
                #ループ脱出用
                if bye: break
                #完全一致したら実行
                if ("group" not in self.cmds[cmd] and "user" not in self.cmds[cmd]):
                    if _msg.text == self.prefix+cmd or ("prefix" in self.cmds[cmd] and _msg.text == cmd):
                        self.process_reply(cmd,_msg)
                        break
                    elif "alt" in self.cmds[cmd]:
                        for altc in self.cmds[cmd]["alt"]:
                            #完全一致したら実行
                            if _msg.text == self.prefix+altc or ("prefix" in self.cmds[cmd] and _msg.text == altc):
                                self.process_reply(cmd,_msg)
                                break
                elif _msg.text == self.prefix+cmd and self.cmds[cmd]["pm"] == True or ("prefix" in self.cmds[cmd] and _msg.text == cmd):
                    self.process_reply(cmd,_msg)
                    break
                #不完全一致OK かつ 文字列が一致
                elif self.cmds[cmd]["pm"] == False and (_msg.text[len(self.prefix):len(self.prefix+cmd)] == cmd or ("prefix" in self.cmds[cmd] and cmd in _msg.text)):
                    self.process_reply(cmd,_msg)
                    break
                elif "alt" in self.cmds[cmd]:
                    for altc in self.cmds[cmd]["alt"]:
                        #完全一致したら実行
                        if _msg.text == self.prefix+altc and self.cmds[cmd]["pm"] == True or ("prefix" in self.cmds[cmd] and _msg.text == altc):
                            bye = True
                            self.process_reply(cmd,_msg)
                            break
                        #不完全一致OK かつ 文字列が一致
                        elif self.cmds[cmd]["pm"] == False and (_msg.text[len(self.prefix):len(self.prefix+altc)] == altc or ("prefix" in self.cmds[cmd] and altc in _msg.text)):
                            bye = True
                            self.process_reply(cmd,_msg)
                            break
        elif str(_msg.contentType) in self.types:
                    if _msg.toType == 0:
                        self.send_reply(_msg._from,self.types[str(_msg.contentType)],_msg)
                    else:
                        self.send_reply(_msg.to,self.types[str(_msg.contentType)],_msg)
                
    """ Utility """

    def addFuncInterrupt(self,func_name,DisposeFunc):
        self.CmdInterrupt[func_name] = DisposeFunc

    #返信を送る
    def send_reply(self,to,cmd_body,data=None):
        if cmd_body[len(cmd_body)-2:] == "()":
            if "thread" not in cmd_body:
                self.CmdInterrupt[cmd_body[:len(cmd_body)-2]](data)
            else:
                _td = threading.Thread(target=self.CmdInterrupt[cmd_body[:len(cmd_body)-2]](data))
                _td.daemon = False
                _td.start()
        elif cmd_body[len(cmd_body)-4:] == ".gif":
            self.cl.sendGif(to,cmd_body)
        elif cmd_body[len(cmd_body)-4:] in [".jpg",".png"]:
            self.cl.sendImage(to,cmd_body)
        elif cmd_body[len(cmd_body)-4:] == ".mp3":
            self.cl.sendVoice(to,cmd_body)
        elif cmd_body[len(cmd_body)-4:] == ".mp4":
            self.cl.sendVideo(to,cmd_body)
        else:
            self.cl.sendMessage(to,cmd_body)
            
    #保存する
    def save_datas(self,filename):
        datas = OrderedDict()
        datas['Prefix'] = self.prefix
        datas['Commands'] = self.cmds
        datas['Types'] = self.types
        datas['Permissions'] = self.perms
        datas['Users'] = self.users
        with open(filename,"w",encoding='utf8') as f:
            json.dump(datas, f, ensure_ascii=False, indent=4,separators=(',', ': '))
        return True
            
    #グルならグル個人なら個人に送る
    def send_text(self,_msg):
        if _msg.toType == 2:
            self.cl.sendMessage(msg.to,msg.text)
            return True
        elif _msg.toType == 0:
            self.cl.sendMessage(msg._from,msg.text)
            return True
        else:
            return False