import socket
import re
import sys
import json
import requests
from random import choice as rc
from string import Template
from datetime import datetime
from time import sleep
from collections import defaultdict

# YouTube API Stuff
import yt_key
from apiclient.discovery import build
from apiclient.errors import HttpError

# Context-free grammar
from pattern.en import sentiment
from pattern.en import parsetree
from pattern.vector import stem, PORTER, LEMMA
from pattern.search import match
from grammar_gen import make_sentence, make_polar

# Parse fill
from parse_fill import make_sentences as pf_sentences

def rand_itp_acronym():
    jsonFile = open('itp_acronyms.json', 'r')
    jsonObj = json.load(jsonFile)
    jsonFile.close()

    def get_word(l):
        word = rc(jsonObj[l])
        return word[0].upper() + word[1:]

    acro = map(get_word, ['i', 't', 'p'])
    return " ".join(acro)

def get_gif(wordlist):
    endpt = "http://api.giphy.com/v1/gifs/search"
    payload = {
        'q': wordlist,
        'api_key': "dc6zaTOxFJmzC"
    }
    r = requests.get(endpt, params=payload)
    try:
        gifs_data = r.json()['data']
        gif_choice = rc(gifs_data)
        return gif_choice['images']['fixed_height']['url']
    except:
        return "Something went wrong... I'm sorry."

def get_wiki_article(word):
    url = 'http://en.wikipedia.org/w/api.php'
    payload = {'format': 'json', 'action': 'query', 'titles': word, 'prop': 'extracts', 'explaintext': 1}
    headers = {'Api-User-Agent': 'itpbot/0.1 (http://rossgoodwin.com; ross.goodwin@gmail.com)'}
    r = requests.get(url, params=payload, headers=headers)
    json_obj = r.json()
    pages = json_obj['query']['pages']
    tgt_obj = pages.values()[0]
    tgt_url = "http://en.wikipedia.org/wiki/"+tgt_obj['title'].replace(' ', '_')
    tgt_text = tgt_obj['extract']
    return tgt_url, tgt_text

def youtube_search(keywords):
    DEVELOPER_KEY = yt_key.ytKey
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    developerKey=DEVELOPER_KEY)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
        q=keywords,
        part="id,snippet",
        maxResults=5
    ).execute()

    videos = []

    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            videos.append((search_result["snippet"]["title"],
                           search_result["snippet"]["description"],
                           search_result["id"]["videoId"]))

    return videos[0]


class Bot(object):
    def __init__(self, nick="itpbot", serv="irc.freenode.net", chan="#itp"):
        self.ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.nick = nick
        self.serv = serv
        self.chan = chan

        pwdFile = open('pwd.txt', 'r')
        pwdText = pwdFile.read().strip()
        pwdFile.close()

        self.pwd = pwdText

        commandFile = open('commands.txt', 'r')
        commandText = commandFile.read()
        commandFile.close()

        self.commands = commandText

        snarkFile = open('snark.txt', 'r')
        snarkText = snarkFile.read()
        snarkFile.close()

        self.snarklist = snarkText.split('\n')

        tellsFile = open('tells_dict.json', 'r')
        tellsDict = json.load(tellsFile)
        tellsFile.close()

        self.tells_dict = tellsDict

        seenFile = open('seen_dict.json', 'r')
        seenDict = json.load(seenFile)
        seenFile.close()

        self.seen_dict = seenDict

    def activate(self):
        # Here we connect to the server using the port 6667
        self.ircsock.connect((self.serv, 6667)) 
        # user authentication
        self.ircsock.send("USER %s %s %s :NYU ITP IRC BOT\r\n" % (self.nick, self.nick, self.nick))
        # here we actually assign the nick to the bot
        self.ircsock.send("NICK %s\r\n" % self.nick)

        # Join #itp
        self.join_channel()

        # Identify
        self.send_msg("IDENTIFY %s" % self.pwd, channel="NickServ")

        # Receive data and respond
        self.communicate()

    def communicate(self):
        while 1: 
            # receive data from the server
            ircmsg = self.ircsock.recv(2048)

            # removing any unnecessary linebreaks.
            ircmsg = ircmsg.strip('\r\n')

            # Here we print what's coming from the server
            print ircmsg

            if ' PRIVMSG ' in ircmsg:
                usernick = ircmsg.split('!')[0][1:] # User's Nick
                vals = ircmsg.split(' PRIVMSG ')[-1].split(' :')
                channel, msgtext = vals[:2]

                timestamp = datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p GMT')

                if channel == self.chan:
                    self.seen_dict[usernick] = (timestamp, msgtext)
                    with open('seen_dict.json', 'w') as outfile:
                        json.dump(self.seen_dict, outfile)

                # This Try/Except Is A Nuclear Blast Shield
                try:
                    self.parse_message(msgtext, usernick, channel)
                except:
                    print sys.exc_info()

            if 'PING :' in ircmsg:
                self.ping()

    def parse_message(self, text, usernick, channel):
        if channel != self.chan:
            userOrFalse = usernick
        else:
            userOrFalse = False

        words = re.findall(r"\b[\w]+\b", text.lower())
        tokens = text.lower().split()

        original_words = words[:]

        try:
            words.remove(self.nick)
        except:
            pass

        try:
            words.remove('hst')
        except:
            pass

        try:
            tree = parsetree(' '.join(words))
            firstNoun = match('NN|NNS|NNP|NNPS', tree)
        except:
            firstNoun = None

        # print original_words
        if self.nick in original_words:

            if set(words) & set(['help', 'commands']):
                commandsTemp = Template(self.commands)
                self.send_msg(
                    commandsTemp.substitute(usernick=usernick, botnick=self.nick),
                    channel=userOrFalse
                )
            elif '?' in text or (set(words) & set(['who', 'where', 'when', 'what', 'why', 'how'])):
                fileObj = open('weird_grammar.json', 'r')
                jsonObj = json.load(fileObj)
                fileObj.close()
                s = sentiment(text)[0]
                if s > 0:
                    print s * 2500 + 1
                    self.send_msg(
                        make_polar(jsonObj, int(s * 2500 + 1)),
                        channel=userOrFalse
                    )
                else:
                    print s * 2500 - 1
                    self.send_msg(
                        make_polar(jsonObj, int(s * -2500 - 1), sent=0),
                        channel=userOrFalse
                    )

            elif firstNoun is not None:
                print firstNoun.string.replace('_', ' ')
                s = sentiment(text)[0]
                sentences = sorted(
                    pf_sentences(abs(s*1000+3), firstNoun.string.replace('_', ' ')),
                    key = lambda x: sentiment(x)[0]
                )

                if s > 0:
                    # print s * 2500 + 1
                    self.send_msg(
                        ' '.join(sentences[-3:]),
                        channel=userOrFalse
                    )
                else:
                    # print s * 2500 - 1
                    self.send_msg(
                        ' '.join(sentences[:3]),
                        channel=userOrFalse
                    )
            else:
                snarkTemp = Template(rc(self.snarklist))
                self.send_msg(
                    snarkTemp.substitute(usernick=usernick, botnick=self.nick),
                    channel=userOrFalse
                )

        if tokens[0] == '.seen':
            tgt_user = tokens[1]
            if tgt_user in self.seen_dict:
                last_time, last_msg = self.seen_dict[tgt_user]
                self.send_msg(
                    "%s: %s last seen on %s saying: %s" % (usernick, tgt_user, last_time, last_msg),
                    channel=userOrFalse
                )
            else:
                self.send_msg(
                    "%s: I haven't seen %s." % (usernick, tgt_user),
                    channel=userOrFalse
                )

        elif tokens[0] == '.tell':
            tgt_user = tokens[1]
            if not tgt_user in self.tells_dict:
                self.tells_dict[tgt_user] = []
            self.tells_dict[tgt_user].append((usernick, ' '.join(tokens[2:])))
            self.send_msg(
                "%s: Ok, I'll tell %s that for you." % (usernick, tgt_user),
                channel=userOrFalse
            )
            with open('tells_dict.json', 'w') as outfile:
                json.dump(self.tells_dict, outfile)

        elif tokens[0] == '.showtells':
            if not usernick in self.tells_dict or not self.tells_dict[usernick]:
                self.send_msg("%s: I have nothing for you." % usernick, channel=usernick)
            else:
                while self.tells_dict[usernick]:
                    src_user, tell_msg = self.tells_dict[usernick].pop()
                    self.send_msg("%s said: %s" % (src_user, tell_msg), channel=usernick)
            with open('tells_dict.json', 'w') as outfile:
                json.dump(self.tells_dict, outfile)

        elif tokens[0] == '.gif':
            gif_url = get_gif(tokens[1:])
            self.send_msg("%s: %s" % (usernick, gif_url), channel=userOrFalse)

        elif tokens[0] == '.wiki':
            try:
                wiki_url, wiki_text = get_wiki_article(tokens[1:])
            except:
                self.send_msg(
                    "%s: I'm sorry, but something went wrong!" % usernick,
                    channel=userOrFalse
                )
            else:
                if wiki_text:
                    safe_wiki_text = ''.join(list(wiki_text)[:300]).replace('\n', ' ') + '...'
                    safe_wiki_text = safe_wiki_text.encode('ascii', 'ignore')
                    self.send_msg(
                        "%s: %s | %s" % (usernick, wiki_url, safe_wiki_text),
                        channel=userOrFalse
                    )
                else:
                    self.send_msg(
                        "%s: I'm sorry, but something went wrong!" % usernick,
                        channel=userOrFalse
                    )
                    
        elif tokens[0] == '.yt':
            try:
                result = youtube_search(tokens[1:])
                result = map(lambda x: x.encode('ascii', 'ignore'), result)
                title, desc, vidId = result
                self.send_msg(
                    "%s: %s | %s | https://www.youtube.com/watch?v=%s" % (usernick, title, desc, vidId),
                    channel=userOrFalse
                )
            except:
                self.send_msg(
                    "%s: I'm sorry, but something went wrong!" % usernick,
                    channel=userOrFalse
                )

        elif tokens[0] == '.hst':
            # self.send_msg('/nick drgonzo')
            if firstNoun is not None:
                lookupFile = open("hst_lookup.json", 'r')
                lookup = json.load( lookupFile )
                lookupFile.close()

                nounStem = stem(firstNoun, stemmer=PORTER)
                idHash = None

                print nounStem

                try:
                    # switch to descending
                    idHash = rc(lookup[nounStem])
                    print idHash
                except KeyError:
                    pass

                try:
                    idHash = rc(lookup[firstNoun])
                    print idHash
                except KeyError:
                    pass
                
                if idHash is not None:
                    bookFile = open("hst_text.json", 'r')
                    books = json.load( bookFile )
                    bookFile.close()

                    text = books[idHash].encode('ascii', 'ignore')
                    # print text

                    self.send_msg("%s: %s"%(usernick,text), channel=userOrFalse)

                else:
                    self.send_msg("%s: Can't say I know it." % usernick, channel=userOrFalse)

            else:
                self.send_msg("%s: Nothing to say about that." % usernick, channel=userOrFalse)
            # self.send_msg('/nick itpbot')


        if "ross" in words:
            self.send_msg("%s: I hope you're not speaking ill of my creator." % usernick, channel=userOrFalse)

        if "itp" in words:
            message = rand_itp_acronym()
            self.send_msg(message, channel=userOrFalse)


    def join_channel(self, channel=False):
        if not channel:
            channel = self.chan
        self.ircsock.send("JOIN "+ channel +"\n")

    def ping(self):
        # This will respond to server Pings.
        self.ircsock.send("PONG :pingis\r\n")  

    def send_msg(self, message, channel=False): 
        if not channel:
            channel = self.chan
        # This is the send message function, it simply sends messages to the channel.
        self.ircsock.send("PRIVMSG %s :%s\r\n" % (channel, message))

if __name__ == '__main__':
    robot = Bot()
    robot.activate()


