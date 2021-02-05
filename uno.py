import socket,threading,ctypes,hashlib,json,os,sys,time,math,traceback,re,ipaddress,random

PORT=51000
IDLE_TIMEOUT=60
BUFFER_SIZE=1024

turn=threading.Event()

# Status Codes

ControlCodes={
    "JOIN":2,
    "DRAW":3,
    "PLAY":4,
    "CHALLENGE":5,
    "SELECT_COLOR":6,
    "REFRESH_HAND":7,
    "REFRESH_BOARD":8,
    "WINNER":9,
    "MSG":10,
    "START_TURN":11,
    "EFFECT":12,
    "END_TURN":13,
    "LOBBY_INFO",14
    
}
# Effect indicates some type of card is in effect in your turn.
# Start Turn will be proceeded by a valid color or number you can play, but for Draw2 or WildDraw4, your actions will be limited.

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
    "SKIP":10,
    "REVERSE":11,
    "WILD":12,
    "DRAW_TWO":13,
    "WILD_DRAW_4":14
}

Colors={
    "BLUE":0,
    "GREEN":1,
    "RED":2,
    "YELLOW":4
}
        
StatusCodes={
    "in_lobby":0,
    "waiting":1,
    "in_game":2
}

ErrorCodes={
    "SUCCESS":0,
    "NO_GAME_FOUND":1,
    "GAME_IN_PROGRESS":2,
    "PLAYER_LIMIT":3
}

class Game:
    def __init__(self):
        try:
            self.root="/home/uno/"
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(None)
            self.port = PORT
            self.players = {}
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', self.port))                 # Now wait for client connection.
            self.lobby={}
            self.online=True
            while self.online:
                try:
                    self.sock.listen(1)
                    conn, addr = self.sock.accept()
                    self.lobby[conn] = player = Player(len(self.players), conn, addr, self)
                    conn_thread = threading.Thread(target=player.handle_connection)
                    conn_thread.start()
                except KeyboardInterrupt:
                    self.online=False
                    pass
                except:
                    print(traceback.format_exc(limit=None, chain=True))
        except:
            print(traceback.format_exc(limit=None, chain=True))
            
        
    def start_game(self):
        direction=randint(0,1)
        self.active=False
        self.players={}
        time.sleep(30)
        self.room["active"]=True
        self.turn=randint(0,len(self.players)-1)
        self.direction = 1 if randint(0,1) else -1
        self.drawthis={"count":0, "type":0}
        self.top_card={"value":randint(0, len(Cards)-1), "color":randint(0, len(Colors)-1)}
        for player in self.players.keys():
            self.players[player].draw(7)
        self.broadcast_board()
        while 1:
            self.players[self.turn].start_turn()
            turn.wait()
            turn.clear()
            self.broadcast_board()
            self.next_turn()
            uno=self.is_uno()
            if not uno==None:
                break
        self.declare_winner(uno)
        self.send_all_to_lobby()
        
    def is_uno(self):
        ct=0
        for p in self.players.keys():
            player=self.players[p]
            if not len(player.cards):
                return ct
            ct+=1
        return None
        
    def broadcast_board(self):
        for p in self.players.keys():
            self.players[p].broadcast_board(self.players)
        
                    

class Player:
    def __init__(self, id, conn, addr, server):
        self.conn=conn
        self.addr=addr
        self.id=id+1
        self.server=server
        self.status=StatusCodes["in_lobby"]
        self.cards=[]
        player.lobby_info()
        
    def send(self, data):
        try:
            bytes_sent = self.conn.send(bytes(data))
        except:
            print(traceback.format_exc(limit=None, chain=True))
        
    
    def join(self):
        if hasattr(self.server, "active"):
            if self.server.active:
                self.send([ControlCodes["JOIN"], ErrorCodes["GAME_IN_PROGRESS"]])
                return
            if len(self.server.players)>=8:
                self.send([ControlCodes["JOIN"], ErrorCodes["PLAYER_LIMIT"]])
                return
            self.status=StatusCodes["waiting"]
            self.send([ControlCodes["JOIN"], ErrorCodes["SUCCESS"]])
            return
        self.send([ControlCodes["JOIN"], ErrorCodes["NO_GAME_FOUND"]])
        
        
    def self.broadcast_board(self, players):
        odata=[]
        odata.append(self.server.turn, self.server.top_card["value"], self.server.top_card["color"])
        for p in players.keys():
            player=players[p]
            odata.append(player.id, len(player.cards))
        self.send([ControlCodes["REFRESH_BOARD"]] + odata)
    
    
    def start_turn(self):
        self.refresh_hand()
        if not self.server.drawthis["count"]:
            self.send([ControlCodes["START_TURN"], self.server.top_card["value"], self.server.top_card["color"]])
            return
        else:
            for c in self.cards:
                if self.cards[c]["value"] == self.server.drawthis["type"]:
                    self.send([ControlCodes["EFFECT"], self.server.top_card["value"]])
                    return
            self.draw(self.server.drawthis["count"])
            
            
    def refresh_hand(self):
        odata=[]
        for c in self.cards:
            odata.append(self.cards[c]["value"], self.cards[c]["color"])
        self.send([ControlCodes["REFRESH_HAND"]] + odata)
        
        
    def draw(self, count):
        for c in range(count):
            card={}
            card["value"]=randint(0, len(Cards)-1)
            card["color"]=randint(0, len(Colors)-1)
            self.cards.append(card)
    
    
    def playcard(self, card):
        value=card[0]
        color=card[1]
        if value==self.server.top_card["value"] or
            color==self.server.top_card["color"] or
            value==Cards["WILD"] or
            value==Cards["WILD_DRAW_4"]:
            self.server.top_card["value"]=value
            self.server.top_card["color"]=color
            if value>9:
                self.process_effect(value)
                
                
    def process_effect(self, value):
        if value==Cards["SKIP"]:
            self.server.next_turn()
        elif value==Cards["REVERSE"]:
            self.server.direction = 1 if self.server.direction==-1 else -1
            self.server.next_turn()
        elif value==Cards["WILD"]:
            self.send([ControlCodes["SELECT_COLOR"]])
        elif value==Cards["DRAW_TWO"]:
            self.server.drawthis["value"]+=2
            self.server.drawthis["type"]=Cards["DRAW_TWO"]
        elif value==Cards["WILD_DRAW_4"]:
            self.send([ControlCodes["SELECT_COLOR"]])
            self.server.drawthis["value"]+=4
            self.server.drawthis["type"]=Cards["WILD_DRAW_4"]
        else: return
            
            
                
                
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
                elif data[0]==ControlCodes["DRAW"]:
                    self.draw(1)
                elif data[0]==ControlCodes["PLAY"]:
                    self.playcard()
                elif data[0]==ControlCodes["CHALLENGE"]:
                    self.challenge()
                elif data[0]==ControlCodes["SELECT_COLOR"]:
                    self.select_color()
            except:
                print(traceback.format_exc(limit=None, chain=True))
        
    
        
