#!/usr/bin/env python
#ehab.hussein@ioactive.co.uk ;  @__obzy__
#ahmed@abdelrahman.net

from sys import argv

import time
import random
hosts = []
class Probability():
    def __init__(self):
        self.charset = list()
        #self.readwords = list(set([i for i in open(raw_input("enter filename: "),'r').xreadlines()]))
        self.readwords = list(set([i for i in open(argv[1],'r').xreadlines()]))
        self.alphaupperindexes = list()
        self.alphalowerindexes = list()
        self.integerindexes = list()
        self.nonalphanumindexes = list()
        self.frequencies = dict()
        self.fullkeyboard = list("`1234567890-=qwertyuiop[]\\asdfghjkl;\'zxcvbnm,./~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?")
        self.discardedcharset = list()
        self.unusedindexes = list(range(len(max(self.readwords, key=len).strip())))
        self.finalcharset = list()
        self.countUpper = 0
        self.countLower = 0
        self.countDigits = 0
        self.countOther = 0
        self.pppc = 1
        self.word_dct = dict()

    def getdifflist(self,full,thelist):
        return list(set(full) - set(thelist))

    def getcharset(self):
        for word in self.readwords:
            for char in word.strip():
                if char not in self.charset:
                    self.charset.append(char)
        self.discardedcharset = self.getdifflist(self.fullkeyboard,self.charset)

    def getindexes(self):
        print "\n\nKeys: {U = Uppercase, l = Lowercase , n = Integers , @ = symbols}\n\n[+] Finding Character types with positions in each word"
        for word in self.readwords:
            word = word.strip()
            self.word_dct[word] = []
            for index,char in enumerate(word.strip()):
                if char.isupper():
                    print "U |",
                    self.countUpper+=1
                    self.word_dct[word] += 'U'
                    if index not in self.alphaupperindexes:
                        self.alphaupperindexes.append(index)
                elif char.islower():
                    print "l |",
                    self.countLower +=1
                    self.word_dct[word] += 'l'
                    if index not in self.alphalowerindexes:
                        self.alphalowerindexes.append(index)
                elif char.isdigit():
                    print "n |",
                    self.countDigits +=1
                    self.word_dct[word] += "n"
                    if index not in self.integerindexes:
                        self.integerindexes.append(index)
                elif not char.isupper() and not char.islower() and not char.isdigit():
                    print "@ |",
                    self.countOther +=1
                    self.word_dct[word] += '@'
                    if index not in self.nonalphanumindexes:
                        self.nonalphanumindexes.append(index)
                self.frequencies[char] = self.frequencies.get(char, 0) + 1
            print " "+word
        if len(self.getdifflist(self.unusedindexes,self.alphaupperindexes)) == 0 and \
            len(self.getdifflist(self.unusedindexes,self.alphalowerindexes)) == 0 and \
            len(self.getdifflist(self.unusedindexes,self.integerindexes)) == 0 and \
            len(self.getdifflist(self.unusedindexes,self.nonalphanumindexes)) == 0:
                print "All indexes have been used by all types of characters.(Truly Random)\n"
        self.finalcharset = self.getdifflist(self.fullkeyboard,self.discardedcharset)
        self.maxcombinationwordsgenerator = len(self.finalcharset) ** len(self.unusedindexes)

    def frequency_index_vertical(self):
        print "\n\n\n[+] Starting frequency with index analysis(vertical)"
        self.word_list_v = list()
        self.analysis_dct_v = dict()
        for key, val in self.word_dct.items():
            self.word_list_v += [val]
        for l in self.word_list_v:
            for i, w in enumerate(l):
                if not self.analysis_dct_v.get(i):
                    self.analysis_dct_v[i] = dict()
                    if not self.analysis_dct_v[i].get('U'):
                        self.analysis_dct_v[i]['U'] = 0
                    if not self.analysis_dct_v[i].get('l'):
                        self.analysis_dct_v[i]['l'] = 0
                    if not self.analysis_dct_v[i].get('n'):
                        self.analysis_dct_v[i]['n'] = 0
                    if not self.analysis_dct_v[i].get('@'):
                        self.analysis_dct_v[i]['@'] = 0
                self.analysis_dct_v[i][w] += 1
        for k,v in self.analysis_dct_v.items():
            print "index: ", k, v

    def frequency_index_horizontal(self):
        print "\n\n[+] Starting frequency with index analysis(horizontal)"
        self.word_list_h = list()
        self.analysis_dct_h = dict()
        for key, val in self.word_dct.items():
            self.word_list_h += [val]
        for w in self.readwords:
            word = w.strip()
            if not self.analysis_dct_h.get(word):
                self.analysis_dct_h[word] = dict()
                if not self.analysis_dct_h[word].get('U'):
                    self.analysis_dct_h[word]['U'] = 0
                if not self.analysis_dct_h[word].get('l'):
                    self.analysis_dct_h[word]['l'] = 0
                if not self.analysis_dct_h[word].get('n'):
                    self.analysis_dct_h[word]['n'] = 0
                if not self.analysis_dct_h[word].get('@'):
                    self.analysis_dct_h[word]['@'] = 0
            for char in word:
                if char.isupper():
                    self.analysis_dct_h[word]['U'] += 1
                elif char.isdigit():
                    self.analysis_dct_h[word]['n'] += 1
                elif char.islower():
                    self.analysis_dct_h[word]['l'] += 1
                elif not char.isupper() and not char.islower() and not char.isdigit():
                    self.analysis_dct_h[word]['@'] += 1
        for k,v in self.analysis_dct_h.items():
            print k, v

    def PrefinalAnalysis(self):
        print "\n\n[+]Calculating weights of each char in each word"
        self._charRelationMatrix= dict()
        self.wordweight = dict()
        self.maxweight = 0
        self.cweight = dict()
        for word in self.readwords:
            word = word.strip()
            for i, c in enumerate(word.strip()):
                if not self._charRelationMatrix.get(i):
                    self._charRelationMatrix[i] = dict()
                if not self._charRelationMatrix[i].get(c):
                    self._charRelationMatrix[i][c] = 0
                self._charRelationMatrix[i][c] += 1
        for word in self.readwords:
            word = word.strip()
            if not self.cweight.get(word):
                self.cweight[word] = dict()
            word = word.strip()
            for i, c in enumerate(word):
                if not self.cweight[word].get(c):
                    self.cweight[word][c] = dict()
                if not self.cweight[word][c].get(i):
                    self.cweight[word][c][i] = 0
                self.cweight[word][c][i] += self._charRelationMatrix[i][c]
        for word in self.readwords:
            word = word.strip()
            print word,":",
            for i, c in enumerate(word):
                self.maxweight += self.cweight[word][c][i]
                print "[", c, ":", self.cweight[word][c][i],"]",
            print "MaxWeight = (", self.maxweight, ")", '\n\n'
            self.maxweight = 0

        if not self.wordweight.get(word):
            self.wordweight[word] = dict()
        print "[+]Gathering weight of character in each index\n"
        for k,v in self._charRelationMatrix.items():
            print k, sorted(v.items(), key=lambda x: x[1], reverse=True), '\n\n'

    def charswithfriendswithwords(self):
        print "\n\n[+]Gathering relationship between each finalcharset and each word it was found in with their positions"
        self.charRelationMatrix= dict()
        for word in self.readwords:
            word = word.strip()
            self.charRelationMatrix[word]= dict()
            for i, c in enumerate(word):
                if not self.charRelationMatrix[word].get(c):
                    self.charRelationMatrix[word][c] = dict()
                    self.charRelationMatrix[word][c] = ([z for z,l in enumerate(word) if l == c])
        for k,v in self.charRelationMatrix.items():
            print "\"%s\""%k,"=",len(v)," values",v,"\n\n"

    def smartGenerator(self):
        self.maxweight = 0
        genIndex = list(range(len(max(self.readwords, key=len).strip())))
        self.smartDict = dict()
        self.strippedReadWords = []
        self.genList = ["" for i in genIndex]
        for word in self.readwords:
            word = word.strip()
            for i,c in enumerate(word):
                if not self.smartDict.get(c):
                    self.smartDict[c] = dict()
                if not self.smartDict[c].get(i):
                    self.smartDict[c][i] = dict()
                for ind, ch in enumerate(word):
                    if not self.smartDict[c][i].get(ind):
                        self.smartDict[c][i][ind] = set()
                    self.smartDict[c][i][ind].add(ch)
        indx = random.choice(genIndex)
        genIndex.remove(indx)
        self.genList[indx] = random.choice(self._charRelationMatrix[indx].keys())
        while genIndex:
            indx = random.choice(genIndex)
            randomC = random.choice(self._charRelationMatrix[indx].keys())
            for i, c in enumerate(self.genList):
                if c:
                    if randomC in self.smartDict[c][i][indx]:
                        self.maxweight += self._charRelationMatrix[indx][randomC]
                        self.genList[indx] = randomC
                        genIndex.remove(indx)
                        break
                    else:
                        break
        for word in self.readwords:
            self.strippedReadWords.append(word.strip())
        if "".join(self.genList) in self.strippedReadWords:
            print "Found word in wordList:", ''.join(self.genList) ,"weight= %d  "%self.maxweight
        else:
            print "Found new word:", ''.join(self.genList) ,"weight= %d  "%self.maxweight
            if "".join(self.genList) not in hosts:
                hosts.append("".join(self.genList))

    def printgeneralstats(self):
        print "\n\n[+]General Statistics"
        print "Full charset                :",''.join(sorted(self.fullkeyboard))
        print "Discarded charset           :",''.join(sorted(self.discardedcharset))
        print "Final charset               :", ''.join(sorted(self.finalcharset))
        print "Word Length                 :",len(self.unusedindexes)
        print "PreAnalysis Max Combinations:",self.maxcombinationwordsgenerator
        print "Lower Case index usage      : %d%%"%(100 * len(self.alphalowerindexes)/len(self.unusedindexes))
        print "Lower Case index locations  :",sorted(self.alphalowerindexes)
        print "Upper Case index usage      : %d%%"%(100 * len(self.alphaupperindexes)/len(self.unusedindexes))
        print "Upper Case index locations  :",sorted(self.alphaupperindexes)
        print "Digit index usage           : %d%%"%(100 * len(self.integerindexes)/len(self.unusedindexes))
        print "Digit index locations       :",sorted(self.integerindexes)
        print "NonAN index usage           : %d%%"%(100 * len(self.nonalphanumindexes)/len(self.unusedindexes))
        print "NonAN index locations       :",sorted(self.nonalphanumindexes)
        print "Counter statistics          : Uppercase: %d , Lowercase: %d, Digits:%d , NonAlphaNumeric:%d" %(self.countUpper ,self.countLower ,self.countDigits , self.countOther)
        print "All char Frequencies        : (\'Found Character\'  Repeated How many Times)"
        for i in (str(sorted(self.frequencies.items(), key=lambda x: x[1])).replace("[","").replace("]","").split(",")):
            print i.strip(),
            if self.pppc == 10:
                print "\n"
                self.pppc = 0
            self.pppc += 1


if __name__ == '__main__':
    print """
 ______           _           _     _ _  _
(_____ \         | |         | |   (_) |(_)  _
 _____) )___ ___ | |__  _____| |__  _| | _ _| |_ _   _
|  ____/ ___) _ \|  _ \(____ |  _ \| | || (_   _) | | |
| |   | |  | |_| | |_) ) ___ | |_) ) | || | | |_| |_| |
|_|   |_|   \___/|____/\_____|____/|_|\_)_|  \__)\__  |
           Efficient Dynamic Algorithms         (____/
         Ehab Hussein & Ahmed AbdelRahman
"""

    EDA = Probability()
    EDA.getcharset()
    EDA.getindexes()
    EDA.printgeneralstats()
    EDA.frequency_index_vertical()
    EDA.frequency_index_horizontal()
    EDA.charswithfriendswithwords()
    EDA.PrefinalAnalysis()
    print "[+] Here are your new strings:(from smart generator)\n"
    for i in range(int(argv[2])):
        EDA.smartGenerator()
    hosts = list(set(hosts))
    print "generated:%d"%(len(hosts))
    print '\n'.join(hosts)