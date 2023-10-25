import requests
import sys
import os
from github import Github
from github import Auth
from datetime import datetime, timedelta

fileText = './results/body_corpus'
fileSha = './results/num_corpus'
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
repoName = 'openssl'
userName = 'openssl'

auth = Auth.Token(token)
g = Github(auth=auth)
repo = g.get_repo(userName+"/"+repoName)
since = datetime.now() - timedelta(days=1)
commits = repo.get_commits(since=since)

dictCheckCommit = dict()
for i in commits:
    dictCheckCommit[i.sha] = i.commit.message   


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

fileOut = open('./results/gensim_'+datetime.now().strftime("%d%m%Y")+'_'+userName+'_'+repoName,'w')

for i in dictCheckCommit:
    query_document = dictCheckCommit[i].split()
    query_bow = dictionary.doc2bow(query_document)
    sims = index[tfidf[query_bow]]
    for document_number, score in sorted(enumerate(sims), key=lambda x: x[1], reverse=True):
        fileOut.write(str(score)+' '+str(i)[:8]+' '+str(sha_corpus[document_number])+'\n')
        if score>0.5:
            bot_message = 'new:https://github.com/'+userName+'/'+repoName+'/commit/'+str(i)[:8] +'\n'+'old:https://github.com/'+userName+'/'+repoName+'/pull/'+str(sha_corpus[document_number])+'\n'+str(score)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
    fileOut.write('\n')
fileOut.close()
