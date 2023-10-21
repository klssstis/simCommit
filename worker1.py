import requests
import sys
import os
from github import Github
from github import Auth
import datetime

fileText = './results/text_corpus'
fileSha = './results/sha_corpus'
try:
    token = sys.argv[1]
    bot_token = sys.argv[2]
    bot_chatID = sys.argv[3]
except IndexError:
    print("not all parameters")
    os._exit(0)



if os.path.exists(fileText):
    with open(fileText) as f:
        text_corpus = f.read().split('_|_')
    text_corpus.pop()
else:
    text_corpus = []

if os.path.exists(fileSha):
    with open(fileSha) as f:
        sha_corpus = f.read().splitlines()
else:
    sha_corpus = []

if len(text_corpus)!=len(sha_corpus):
    print('BBAADD: not correct sha')
    sys.exit(0)
repoName = 'postgres'
userName = 'postgres'

auth = Auth.Token(token)
g = Github(auth=auth)
repo = g.get_repo(userName+"/"+repoName)
since = datetime.now() - timedelta(days=1)
commits = repo.get_commits(since=since)

dictCheckCommit = dict()
for i in commits:
    if 'Discussion:' in i.commit.message:
        for j in i.commit.message.split('Discussion:')[1:]:
            if not 'https://' in j:
                continue
            a = 'https://'+j.split('https://')[1].splitlines()[0]
            try:
                r = requests.get(a)
            except:
                continue
            if r.status_code == 200:
                if 'span class=\"listname\"' in str(r.content):
                    typeList = str(r.content).split('span class=\"listname\"')[1].split('/span')[0].split('\">')[1].split('</a')[0]
                    if 'pgsql-bugs' in typeList:
                        text_corpus.append(i.commit.message)
                        sha_corpus.append(i.sha)
                    else:
                        dictCheckCommit[i.sha] = i.commit.message      
    else:
        dictCheckCommit[i.sha] = i.commit.message   



file = open('text_corpus','w')
for item in text_corpus:
	file.write(item+"_|_")
file.close()

file = open('sha_corpus','w')
for item in sha_corpus:
	file.write(item+"\n")
file.close()

stoplist = set('for a of the and to in'.split(' '))
texts = [[word for word in document.lower().split() if word not in stoplist]
         for document in text_corpus]

from collections import defaultdict
frequency = defaultdict(int)
for text in texts:
    for token in text:
        frequency[token] += 1

processed_corpus = [[token for token in text if frequency[token] > 1] for text in texts]

from gensim import corpora

dictionary = corpora.Dictionary(processed_corpus)
bow_corpus = [dictionary.doc2bow(text) for text in processed_corpus]

from gensim import models

tfidf = models.TfidfModel(bow_corpus)
from gensim import similarities

index = similarities.SparseMatrixSimilarity(tfidf[bow_corpus], num_features=len(dictionary))

fileOut = open('./results/gensim_'+datetime.date.today().strftime("%d%m%Y")+'_'+userName+'_'+repoName,'w')

for i in dictCheckCommit:
    query_document = dictCheckCommit[i].split()
    query_bow = dictionary.doc2bow(query_document)
    sims = index[tfidf[query_bow]]
    for document_number, score in sorted(enumerate(sims), key=lambda x: x[1], reverse=True):
        fileOut.write(str(score)+' '+str(i)[:6]+' '+str(sha_corpus[document_number])[:6]+'\n')
        if score>0.2:
            bot_message = 'new:https://github.com/'+userName+'/'+repoName+'/commit/'+str(i)[:6] +'\n'+'old:https://github.com/'+userName+'/'+repoName+'/commit/'+str(sha_corpus[document_number])[:6]+'\n'+str(score)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
    fileOut.write('\n')
fileOut.close()
