# -*- coding: utf-8 -*-
"""scotus_decision_dpp.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/12fD6Dt5Awk4TtOEPPNpVfCLNR11ggWhT
"""

!pip install textacy

import nltk
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords  
from nltk.tokenize import word_tokenize  
from gensim import corpora, models
from gensim.models import LdaModel, LdaMulticore

nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer() 

import re
import pandas as pd
import textacy.datasets
import matplotlib.pyplot as plt
import numpy as np
import gensim
from sklearn.model_selection import train_test_split

def data_extraction():
    ds = textacy.datasets.SupremeCourt()
    ds.download()   

    decisions = ds.records()
    scotus_issue_area = []
    scotus_issue = []
    scotus_text = []
    issue_freq = {}
    issue_area_freq = {}

    for text, details in decisions:
        if details['issue_area'] == -1:
            continue
        if details['issue'] == 'none':
            continue

        scotus_issue_area.append(details['issue_area'])
        scotus_issue.append(details['issue'])
        scotus_text.append(text)

        if details['issue'] in issue_freq:
            issue_freq[details['issue']] = issue_freq[details['issue']] + 1
        else:
            issue_freq[details['issue']] = 1

        if details['issue_area'] in issue_area_freq:
            issue_area_freq[details['issue_area']] = issue_area_freq[details['issue_area']] + 1
        else:
            issue_area_freq[details['issue_area']] = 1

    plot_issue_freq(issue_freq, issue_area_freq)
    return ds, decisions, scotus_issue_area, scotus_issue, scotus_text, issue_freq, issue_area_freq

def get_true_labels(ds, decisions):
    issue_label = []
    decision_text = []

    issue_label_index = {}  # dictionary mapping issues to a numeric index
    issue_codes = list(ds.issue_codes.keys())
    issue_codes.append('-1')
    issue_codes.sort()
    labels_index = dict(zip(issue_codes, np.arange(len(issue_codes))))

    for text, details in decisions:
        if details['issue'] == None:
            issue_label.append(-1)
        else:
            issue_label.append(details['issue'])
        decision_text.append(text)
        
    return labels_index, issue_label, decision_text

def plot_issue_freq(issue_freq, issue_area_freq):
    fig, ax = plt.subplots(2, figsize=[20.0, 4.0])
    ax[0].bar (issue_area_freq.keys(), issue_area_freq.values())
    ax[1].bar (issue_freq.keys(), issue_freq.values())
    
    plt.show()

def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts"""
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}

    return tag_dict.get(tag, wordnet.NOUN)

def data_preprocess(scotus_issue_area, scotus_issue, scotus_text):
    stop_words = set(stopwords.words('english'))  
  
    # word_tokens = word_tokenize(input_str)  
    clean_scotus_text = []
    scotus_processed_text = []

    for text in scotus_text:  
        text_without_punct = re.sub(r'[^\w\s]', ' ', text)
        word_tokens = nltk.word_tokenize(text_without_punct.lower()) 
        word_tokens = [w for w in word_tokens if not w in stop_words if w.isalpha()]  
        processed_tokens = [lemmatizer.lemmatize(w, get_wordnet_pos(w)) for w in word_tokens]
        
        clean_scotus_text.append(word_tokens)
        scotus_processed_text.append(processed_tokens)

    mydict = corpora.Dictionary(scotus_processed_text)
    mydict.filter_extremes()

    mydict.save('scotus.dict')  # save dict to disk
    print("Dictionary:")
    print(mydict.token2id)

    bow_corpus = [mydict.doc2bow(doc, allow_update=True) for doc in scotus_processed_text]
    sample = open('mydict_to_bow.txt', 'w') 
    print("Bag of words:")
    print(bow_corpus)

    word_counts = [[(mydict[id], count) for id, count in line] for line in bow_corpus]
    corpora.MmCorpus.serialize('bow_corpus.mm', bow_corpus)  # save corpus to disk

    return scotus_processed_text, mydict, bow_corpus

def tfdif(bow_corpus):
    tfidf = models.TfidfModel(bow_corpus, smartirs='ntc')
    tfidf_corpus = tfidf[bow_corpus]

    print()
    print("Corpus of bag of words:")
    for doc in tfidf_corpus:
        print(doc)
    
    # for doc in tfidf[bow_corpus]:
    #     print([[mydict[id], np.around(freq, decimals=3)] for id, freq in doc])

    return tfidf_corpus

def lda(corpus):
    lda_model = LdaMulticore(corpus, num_topics=250, id2word=mydict)
    corpus_lda = lda_model[corpus]
    lda_model.save('scotus.lda')

    for idx, topic in lda_model.print_topics(-1):
        print('Topic: {} \nWords: {}'.format(idx, topic))

    return lda_model, corpus_lda

def lda_comparison(tfidf_corpus, bow_corpus):
    # using TF-IDF
    print()
    print("LDA using TF-IDF:")
    lda_model1, tfidf_corpus_lda = lda(tfidf_corpus)

    print()
    print("Performance evaluation by classifying sample document using LDA TF-IDF model:")
    for index, score in sorted(lda_model1[bow_corpus[10]], key=lambda tup: -1*tup[1]):
        print("\nScore: {}\t \nTopic: {}".format(score, lda_model1.print_topic(index, 10)))

    print()
    print("************************************************************************************************************************************************************************")
    # using bag of words
    print()
    print("LDA using Bag of Words:")
    lda_model2, bow_corpus_lda = lda(bow_corpus)

    print()
    print("Performance evaluation by classifying sample document using LDA Bag of Words model:")
    for index, score in sorted(lda_model2[bow_corpus[10]], key=lambda tup: -1*tup[1]):
        print("\nScore: {}\t \nTopic: {}".format(score, lda_model2.print_topic(index, 10)))

    return tfidf_corpus_lda, bow_corpus_lda

ds, decisions, scotus_issue_area, scotus_issue, scotus_text, issue_freq, issue_area_freq = data_extraction()
labels_index, issue_label, decision_text = get_true_labels(ds, decisions)

scotus_processed_text, mydict, bow_corpus = data_preprocess(scotus_issue_area, scotus_issue, scotus_text)

# Load them back
loaded_dict = corpora.Dictionary.load('/content/drive/MyDrive/SCOTUS/scotus.dict')
bow_corpus = corpora.MmCorpus('/content/drive/MyDrive/SCOTUS/bow_corpus.mm')

tfidf_corpus = tfdif(bow_corpus)

tfidf_corpus_lda, bow_corpus_lda = lda_comparison(tfidf_corpus, bow_corpus)

print(len(input_corpus))
input_corpus = np.transpose(gensim.matutils.corpus2dense(tfidf_corpus_lda, num_terms=90018))
print(input_corpus)
expected_labels = np.array(issue_label)

X_train, X_test, y_train, y_test = train_test_split(input_corpus, expected_labels, test_size=0.2, random_state=42)


print ('Training data')
print(X_train.shape)
print(y_train.shape)
