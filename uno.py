import socket,threading,ctypes,hashlib,json,os,sys,time,math,traceback,re,ipaddress,random

PORT=51000
IDLE_TIMEOUT=60
BUFFER_SIZE=1024

ControlCodes={
    "JOIN":2,
    "READY":3,
    "DRAW":4,
    "PLAY":5,
    "CHALLENGE":6,
    "SELECT_COLOR":7,
    "SHOW_HAND":8,
    "WINNER":9
    
}

Cards={
    "ZERO":0,
    "ONE":1,
    "TWO":2,
    "THREE":3,
    "FOUR":4,
    "FIVE":5,
    "SIX":6,
    "SEVEN":7,
    "EIGHT":8,
    "NINE":9,
    "TEN":10,
    "SKIP":11,
    "REVERSE":12,
    "DRAW_TWO":13,
    "WILD":14,
    "WILD_DRAW_4":15
}

Colors={
    "BLUE":0,
    "GREEN":1,
    "RED":2,
    "YELLOW":4
}

class GameServer:
    def __init__(self):
        try:
            self.root="/home/uno/"
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(None)
            self.port = PORT
            self.players = {}
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', self.port))                 # Now wait for client connection.
        except:
            print(traceback.format_exc(limit=None, chain=True))
            
            
    def run(self):
        try:
            self.online=True
            self.running=False
            print(f"Server running on port {PORT}")
            while self.online:
                try:
                    self.sock.listen(1)
                    conn, addr = self.sock.accept()
                    self.players[conn] = player = Player(len(self.players), conn, addr, self)
                    conn_thread = threading.Thread(target=player.handle_connection)
                    conn_thread.start()
                    if len(self.players)>=3:
                        game_thread=threading.Thread(target=self.game_loop)
                        game_thread.start()
                except KeyboardInterrupt:
                    self.online=False
                    pass
                except:
                    print(traceback.format_exc(limit=None, chain=True))
                    
    def game_loop(self):
        # wait for all players to become ready
        while 1:
            players_ready=0
            for player in self.players.keys():
                if self.players[player].ready:
                    players_ready+=1
            if players_ready==len(self.players):
                break
        
        # all players draw starting hand
        for player in self.players.keys():
            self.players[player].start()
        
        #set starting top card
        self.top_card={"value":randint(0, len(Cards)-1), "color":randint(0, len(Colors)-1)}
        
        #set starting direction of play
        self.direction=randint(0,1)     # 0=CW, 1=CCW
        
        #set current turn
        self.turn=randint(0,len(self.players)-1)
        self.running=True
        while self.running:
            ct=0
            for player in self.players.keys():
                if len(self.players[player].cards)==0:
                    self.win(ct+1)
                    continue
                ct+=1
                    
                    
    def win(self, winner):
        for player in self.players.keys():
            self.players[player].send([ControlCodes["WINNER"], winner])
        self.running=False
        
                    

class Player:
    def __init__(self, id, conn, addr, server):
        self.conn=conn
        self.addr=addr
        self.id=id+1
        self.server=server
        self.ready=False
        self.cards=[]
        
    def send(self, data):
        try:
            bytes_sent = self.conn.send(bytes(data))
        except:
            print(traceback.format_exc(limit=None, chain=True))
    
    def setready(self):
        self.ready=True
    
    def start(self):
        newcard=self.drawcard()
        self.cards.append()
        
    def drawcard(self):
        card={}
        card["value"]=randint(0, len(Cards)-1)
        card["color"]=randint(0, len(Colors)-1)
        return card
    
    def playcard(self, card):
        value=card[0]
        color=card[1]
        if value==self.server.top_card["value"] or
            color==self.server.top_card["color"] or
            value==Cards["WILD"] or
            value==Cards["WILD_DRAW_4"]:
            self.server.top_card["value"]=value
            self.server.top_card["color"]=color
            if value==Cards["WILD"] or value==Cards["WILD_DRAW_4"]:
                self.send([ControlCodes["SELECT_COLOR"]]
            else: self.server.turn+=1
                
    def handle_connection(self):
        self.conn.settimeout(IDLE_TIMEOUT)
		while self.server.online:
            try:
                data = list(self.conn.recv(BUFFER_SIZE))
                if not data:
			  raise ClientDisconnectErr(f"Player {self.id} disconnected!")
                if not len(data):
			  continue
                if data[0]==ControlCodes["JOIN"]:
                    self.join()
                elif data[0]==ControlCodes["READY"]:
                    self.setready()
                elif data[0]==ControlCodes["DRAW"]:
                    self.drawcard()
                elif data[0]==ControlCodes["PLAY"]:
                    self.playcard()
                elif data[0]==ControlCodes["CHALLENGE"]:
                    self.challenge()
                elif data[0]==ControlCodes["SELECT_COLOR"]:
                    self.select_color()
                elif data[0]==ControlCodes["SHOW_HAND"]:
                    odata=[]
                    for card in self.cards:
                        odata.append(card["value"], card["color"])
                    self.send([ControlCodes["SHOW_HAND"]]+odata)
            except:
                print(traceback.format_exc(limit=None, chain=True))
        
    
        
