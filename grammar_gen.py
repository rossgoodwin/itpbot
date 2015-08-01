import random
import json
import sys
from pattern.en import sentiment
# from firstnames_m import mFirstNames
# from firstnames_f import fFirstNames

def generate(grammar, axiom):
    """Generate a list of tokens from grammar, starting with axiom. The grammar
       should take the form of a dictionary, mapping rules (strings) to lists
       of expansions for those rules. Expansions will be split on whitespace.
       Any token in the expansion that doesn't name a rule in the grammar will
       be included in the expansion as-is."""
    s = list()
    if axiom in grammar: # Termination condition
        # try:
        expansion = random.choice(grammar[axiom])
        # except IndexError:
        #     s.append(random.choice(mFirstNames+fFirstNames).lower()+"\'s")
        # else:
        for token in expansion.split():
            s.extend(generate(grammar, token)) # RECURSION!
    else:
        s.append(axiom)
    return s

def make_sentence(grammar_dict):
    sentList = generate(grammar_dict, 'S')
    rawSentence = ' '.join(sentList)
    return rawSentence[0].upper() + rawSentence[1:] + '.'

def main(grammar_dict, count):
    sentences = []
    for _ in range(int(count)):
        sentList = generate(grammar_dict, 'S')
        rawSentence = '_'.join(sentList)
        # sentence = rawSentence[0].upper() + rawSentence[1:] + '.'
        sentences.append(rawSentence)
    return '\n'.join(sentences)

def make_polar(grammar_dict, count, sent=1):
    # print int(count)
    sentences = sorted(
        [make_sentence(grammar_dict) for _ in range(abs(int(count)))],
        key=lambda x: sentiment(x)[0]
    )
    # print sentences
    if sent:
        return sentences[-1]
    else:
        return sentences[0]



if __name__ == '__main__':
    script, grammarFile, count = sys.argv
    grammarDict = json.load( open(grammarFile, 'r') )
    print make_polar(grammarDict, count)