import re
import string

class InlineTokenizer:
    def __init__(self, data):
        self.data = data

    def punctuation(self):
        puncts = [ '[', ']', '{', '}' ]
        for punct in puncts:
            if self.data[0] == punct:
                self.data = self.data[1:]
                return punct

    def up_to_comma(self):
        match = re.match('(.*?)\s*, (.*)', self.data)
        if match: 
            self.data = match.groups()[1]
            return match.groups()[0]

    def up_to_end_brace(self):
        match = re.match('(.*?)(\s*[\]}].*)', self.data)
        if match: 
            self.data = match.groups()[1]
            return match.groups()[0]

    def next(self):
        self.data = string.strip(self.data)
        productions = [
            self.punctuation,
            self.up_to_comma,
            self.up_to_end_brace
        ]
        for production in productions:
            token = production()
            if token:
                return token

