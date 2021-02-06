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
    "LOBBY_INFO":14
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
                    print(f"Got new client from {addr}")
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
        self.prior_card={}
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
            
    def next_turn(self):
        self.turn+=self.direction
        if self.turn<0:
            self.turn=len(self.players)-1
        elif self.turn>(len(self.players)-1):
            self.turn=0
            
    def last_turn(self):
        last_turn=self.turn
        last_turn-=self.direction
        if last_turn<0:
            last_turn=len(self.players)-1
        elif last_turn>(len(self.players)-1):
            last_turn=0
        return last_turn
        
                    

class Player:
    def __init__(self, id, conn, addr, server):
        self.conn=conn
        self.addr=addr
        self.id=id+1
        self.server=server
        self.status=StatusCodes["in_lobby"]
        self.cards=[]
        self.lobby_info()
        
    def lobby_info(self):
        # OUT:
        #   Players in Lobby
        #   Game Thread Up?
        #   ID + Status for each person in Lobby
        odata=[]
        odata.append(len(self.server.lobby))
        if not hasattr(self.server, "active"):
            odata.append(False)
        else: odata.append(True)
        for l in self.server.lobby.keys():
            player=self.server.lobby[l]
            odata.append(self.id, self.status)
        self.send([ControlCodes["LOBBY_INFO"]] + odata)
        
    def send(self, data):
        try:
            print(f"sending packet: {data}")
            bytes_sent = self.conn.send(bytes(data))
        except:
            print(traceback.format_exc(limit=None, chain=True))
        
    
    def join(self):
        # OUT:
        #   Success or Error joining Game
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
        
        
    def broadcast_board(self, players):
        # OUT:
        #   Current Turn #
        #   Current Pile Top Card/Value
        #   Player Count
        #   Player ID/Hand Size for all players
        odata=[]
        odata.append(self.server.turn, self.server.top_card["value"], self.server.top_card["color"], len(self.server.players))
        for p in players.keys():
            player=players[p]
            odata.append(player.id, len(player.cards))
        self.send([ControlCodes["REFRESH_BOARD"]] + odata)
    
    
    def start_turn(self):
        self.refresh_hand()
        if not self.server.drawthis["count"]:
            # OUT:
            #   Value/Color Top Card
            self.send([ControlCodes["START_TURN"], self.server.top_card["value"], self.server.top_card["color"]])
            return
        else:
            for c in self.cards:
                if self.cards[c]["value"] == self.server.drawthis["type"]:
                    # OUT:
                    #   Effect CTL code
                    #   Value of Card you must supply (should only recv this if you can play it)
                    self.send([ControlCodes["EFFECT"], self.server.top_card["value"]])
                    return
            self.draw(self.server.drawthis["count"])
            self.server.drawthis={"count":0, "type":0}
            turn.set()
            
            
    def refresh_hand(self):
        # OUT:
        #   Value/Color for each card in hand
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
        self.refresh_hand()
    
    
    def playcard(self, card):
        value=card[0]
        color=card[1]
        if value==self.server.top_card["value"] or color==self.server.top_card["color"] or value==Cards["WILD"] or value==Cards["WILD_DRAW_4"]:
            self.server.prior_card=self.server.top_card
            self.server.top_card["value"]=value
            self.server.top_card["color"]=color
            if value>9:
                self.process_effect(value)
            else: turn.set()
                
                
    def process_effect(self, value):
        if value==Cards["SKIP"]:
            self.server.next_turn()
            turn.set()
        elif value==Cards["REVERSE"]:
            self.server.direction = 1 if self.server.direction==-1 else -1
            turn.set()
        elif value==Cards["WILD"]:
            self.send([ControlCodes["SELECT_COLOR"]])
        elif value==Cards["DRAW_TWO"]:
            self.server.drawthis["value"]+=2
            self.server.drawthis["type"]=Cards["DRAW_TWO"]
            turn.set()
        elif value==Cards["WILD_DRAW_4"]:
            self.send([ControlCodes["SELECT_COLOR"]])
            self.server.drawthis["value"]+=4
            self.server.drawthis["type"]=Cards["WILD_DRAW_4"]
        else: return
            
    def find_card(self, card):
        color=card["color"]
        value=card["value"]
        for c in self.cards:
            if c["color"]==color or c["value"]==value or c["value"]==Cards["WILD"]:
                return True
        return False
                
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
                    self.playcard(data[1:])
                elif data[0]==ControlCodes["CHALLENGE"]:
                    last_turn=self.server.last_turn()
                    last_player=self.server.players[last_player]
                    if last_player.find_card(self.server.prior_card):
                        last_player.draw(4)
                        self.server.drawthis["count"]-=4
                    else:
                        self.server.drawthis["count"]+=2
                elif data[0]==ControlCodes["SELECT_COLOR"]:
                    self.server.top_card["color"]=data[1]
                    turn.set()
            except:
                print(traceback.format_exc(limit=None, chain=True))
        
    
if __name__ == '__main__':
	
	server = Game()
