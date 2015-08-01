
# coding: utf-8

# In[1]:

from pattern.en import parsetree
from collections import defaultdict
from firstnames_m import mFirstNames
from firstnames_f import fFirstNames
from random import sample as rs
from random import choice as rc
import json
import re
import requests


# In[2]:

def get_wiki_article(word):
    url = 'http://en.wikipedia.org/w/api.php'
    payload = {'format': 'json', 'action': 'query', 'titles': word, 'prop': 'extracts', 'explaintext': 1}
    headers = {'Api-User-Agent': 'itpbot/0.1 (http://rossgoodwin.com; ross.goodwin@gmail.com)'}
    r = requests.get(url, params=payload, headers=headers)
    json_obj = r.json()
    print json_obj
    pages = json_obj['query']['pages']
    tgt_obj = pages.values()[0]
    return tgt_obj['extract']


# In[3]:

# get_wiki_article(['baseball', 'catcher'])


# In[4]:

def get_namepos(n):
    maleNames = rs(mFirstNames, n/2)
    femaleNames = rs(fFirstNames, n/2)
    return map(lambda s: s+"\'s", maleNames+femaleNames)


# In[5]:

def parse_fill(text):
    tree = parsetree(text, relations=True)
    grammar_dict = defaultdict(list)

    def parse_sentence(sentence):
        # Get complete transitive and intransitive
        # verb phrases
        relDict = sentence.relations
        objectNos = filter(lambda x: x is not None, relDict['OBJ'].keys())
        for idNo in relDict['VP']:
            phrase = relDict['VP'][idNo] # chunk
            if idNo is not None and idNo in objectNos: 
                grammar_dict['VP_trans'].append(phrase.string.lower())
            else:
                grammar_dict['VP_intrans'].append(phrase.string.lower())

        # Get complete preposition-noun phrases
        pnpList = sentence.pnp
        for chunk in pnpList:
            grammar_dict['PNP'].append(chunk.string.lower())

        # Get other chunks and individual words
        for chunk in sentence.chunks:
            grammar_dict[chunk.type].append(chunk.string.lower())
            for word in chunk.words:
                grammar_dict[word.type].append(word.string.lower())

    map(parse_sentence, tree)
    return grammar_dict


# In[6]:

def add_template(cur_dict):
    # cur_dict must be defaultdict(list)
    inJson = json.load( open('grammar_template.json', 'r') )
    namePos = get_namepos(100)
    for key in inJson:
        cur_dict[key].extend(inJson[key])
    cur_dict["NamePos"].extend(namePos)


# In[7]:

def generate(grammar, axiom):
    """Generate a list of tokens from grammar, starting with axiom. The grammar
       should take the form of a dictionary, mapping rules (strings) to lists
       of expansions for those rules. Expansions will be split on whitespace.
       Any token in the expansion that doesn't name a rule in the grammar will
       be included in the expansion as-is."""
    s = list()
    if grammar[axiom]: # Termination condition for defaultdict(list)
        expansion = rc(grammar[axiom])
        for token in expansion.split():
            if token in ['.', ',', ':']:
                s.append(token)
            else:
                s.extend(generate(grammar, token)) # RECURSION!
    else:
        s.append(axiom)
    return s


# In[8]:

def fix_punc(text):
    newText = re.sub(r' ([,;:\.\!\?])', r'\1', text)
    return newText[0].upper() + newText[1:]


# In[9]:

def make_sentences(n, tag):
    grammar_dict = parse_fill(get_wiki_article(tag))
    add_template(grammar_dict)
    sentences = []
    for _ in range(int(n)):
        sentList = generate(grammar_dict, "Sentence")
        sentences.append(fix_punc(' '.join(sentList)))
    return sentences


# In[10]:

if __name__ == '__main__':
    print ' '.join(make_sentences(5, 'time'))


# In[ ]:



