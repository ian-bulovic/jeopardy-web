import web
import socket
import sys
import logging
import datetime


class EmptyLog:
    def __init__(self, xapp, logname="wsgi"):
        class O:
            def __init__(self, xapp, logname="wsgi"):
                self.logger = logging.getLogger(logname)
            def write(self, s):
                if s[-1] == '\n':
                    s = s[:-1]
                if s == "":
                    return
                if self.ignore(s):
                    return
                self.logger.debug(s)
            def ignore(self, s):
                if not all([web.config.get('debug_http', False), any(['"HTTP/1.1 GET ' in s, '"HTTP/1.1 POST ' in s])]):
                    return True
                return False
        self.app = xapp
        self.f = O(logname)
    def __call__(self, environ, start_response):
        environ['wsgi.errors'] = self.f
        return self.app(environ, start_response)

render = web.template.render('templates/')

urls = (
    '/'      , 'index' ,
    '/join'  , 'join'  ,
    '/buzzer', 'buzzer',
    '/buzz'  , 'buzz'  ,
    '/host'  , 'host'  ,
    '/state' , 'state' ,
    '/finaljeopardy' , 'finaljeopardy' ,
    '/finalhost'     , 'finalhost'     ,
)

scores = {}
bets = {}
guesses = {}
buzz_list = []
last_buzz_time = {}
lockout_time = datetime.timedelta(seconds=0.25)

game_status = {"status": "normal"}

def join_if_absent(name):
    if (name not in scores.keys()):
        print(name + " joined the game.")
        scores[name] = 0
        bets[name] = ""
        guesses[name] = ""

def try_buzz(name, timestamp):
    dt = lockout_time

    join_if_absent(name)
    
    if name in last_buzz_time.keys():
        dt = timestamp - last_buzz_time[name]
    
    last_buzz_time[name] = timestamp
    
    if dt >= lockout_time:
        print(f"{name} buzzed!")
        buzz_list.append(name)

class index:
    def GET(self):
        return render.index()

class join:
    def POST(self):
        name = web.input().name;
        web.setcookie("name", name)
        join_if_absent(name)
        raise web.seeother("/buzzer")

class buzzer:
    def GET(self):
        # score = scores[web.cookies().get("name")]
        return render.buzzer()
    def POST(self):
        playername = web.cookies().get("name")
        if playername is None:  # if the player doesn't have a name, redirect to login
            raise web.seeother("/join")
        if playername not in buzz_list:
            try_buzz(playername, datetime.datetime.now())

class buzz:
    def POST(self):
        playername = web.cookies().get("name")
        if playername is None:  # if the player doesn't have a name, redirect to login
            raise web.seeother("/join")
        if playername not in buzz_list:
            try_buzz(playername, datetime.datetime.now())
        raise web.seeother("/buzzer")

class host:
    def GET(self):
        return render.host()
    def POST(self):
        if len(buzz_list) > 0:
            buzz_list.clear()
        raise web.seeother("/host")

class state:
    def GET(self):
        return render.state(buzz_list, scores, bets, guesses, game_status["status"])
    def POST(self):            
        try:
            player = web.input().player
            score_change = int(web.input().scoreChange)
            scores[player] = scores[player] + score_change
            verb = "lost" if score_change < 0 else "gained"
            host_name = web.cookies().get("name")
            if host_name is None:
                host_name = "host"
            print(f"{player} {verb} {abs(score_change)} points. ({host_name})")
        finally:
            return render.state(buzz_list, scores, bets, guesses, game_status["status"])

class finaljeopardy:
    def GET(self):
        return render.finaljeopardy()
    def POST(self):
        playername = web.cookies().get("name")
        bet_value = int(web.input().bet)
        answer = web.input().answer
        bets[playername] = bet_value
        guesses[playername] = answer

class finalhost:
    def GET(self):
        return render.finalhost()
    def POST(self):
        game_status["status"] = web.input().status
        return render.state(buzz_list, scores, bets, guesses, game_status["status"])

# found on stackoverflow
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def launch_server():
    print("Server started!\n")
    print(f"Connection address:")
    sys.argv.append(get_ip())
    # sys.argv.append("127.0.0.1:5500")

    app = web.application(urls, globals())
    app.run(EmptyLog)
    # app.run() # print http info to console


if __name__ == "__main__":
    launch_server()
