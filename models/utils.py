import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical

def load_data(filename):
    data=pd.read_csv(filename,encoding="latin1")
    data=data.fillna(method="ffill") # 用前一个非缺失值去填充该缺失值
    return data


class SentenceGetter(object):

    def __init__(self, data):
        self.n_sent = 1
        self.data = data
        self.empty = False
        agg_func = lambda s: [(w, p, t) for w, p, t in zip(s["Word"].values.tolist(),
                                                           s["POS"].values.tolist(),
                                                           s["Tag"].values.tolist())]
        self.grouped = self.data.groupby("Sentence #").apply(agg_func)
        self.sentences = [s for s in self.grouped]

    def get_next(self):
        try:
            s = self.grouped["Sentence: {}".format(self.n_sent)]
            self.n_sent += 1
            return s
        except:
            return None

# 2 提取特征
def word2features(sent,i):
    word=sent[i][0]
    postag=sent[i][1]

    features={
        'bias':1.0,
        'word.lower()':word.lower(),
        'word[-3:]': word[-3:],
        'word[-2:]': word[-2:],
        'word.isupper()':word.isupper(),
        'word.istitle()':word.istitle(),
        'word.isdigit()':word.isdigit(),
        'postag':postag,
        'postag[:2]':postag[:2]
    }

    if i>0:
        word1=sent[i-1][0]
        postag1=sent[i-1][1]
        features.update({
            '-1:word.lower()': word1.lower(),
            '-1:word.istitle()': word1.istitle(),
            '-1:word.isupper()': word1.isupper(),
            '-1:postag': postag1,
            '-1:postag[:2]': postag1[:2],
        })
    else:
        features['BOS']=True

    if i<len(sent)-1:
        word1=sent[i+1][0]
        postag1=sent[i+1][1]
        features.update({
            '+1:word.lower()': word1.lower(),
            '+1:word.istitle()': word1.istitle(),
            '+1:word.isupper()': word1.isupper(),
            '+1:postag': postag1,
            '+1:postag[:2]': postag1[:2],
        })
    else:
        features['EOS']=True

    return features

def sent2features(sent):
    return [word2features(sent,i) for i in range(len(sent))]

def sent2labels(sent):
    return [label for token,postag,label in sent]

# def sent2tokens(sent):
#     return [token for token,postag,label in sent]


def bulid_dataset(ner_dataset_dir,dataset_dir,max_len=50):

    """
    构建数据
    :param data:
    :return:
    """
    data = pd.read_csv(ner_dataset_dir, encoding="latin1")
    data = data.fillna(method="ffill")  # 用前一个非缺失值去填充该缺失值

    # dataset_dir="../data/dataset.pkl"

    if os.path.exists(dataset_dir):
        print("正在加载旧数据")
        with open(dataset_dir,'rb') as in_data:
            data=pickle.load(in_data)
            return data


    # 标签和单词
    words = list(set(data["Word"].values))
    words.append("ENDPAD")
    n_words = len(words)
    tags = list(set(data["Tag"].values))
    n_tags = len(tags)
    getter = SentenceGetter(data)
    sentences = getter.sentences
    # print(sentences[0])

    # plt.hist([len(s) for s in sentences], bins=50)
    # plt.show()

    # 输入长度等长，统一设置为50
    max_len = 50
    word2idx = {w: i for i, w in enumerate(words)}
    tag2idx = {t: i for i, t in enumerate(tags)}

    # print(word2idx['Obama'])
    # print(tag2idx['B-geo'])

    # 填充句子
    X = [[word2idx[w[0]] for w in s] for s in sentences]
    X = pad_sequences(maxlen=max_len, sequences=X, padding="post", value=n_words - 1)
    # print(X[1])

    # 填充标签
    y = [[tag2idx[w[2]] for w in s] for s in sentences]
    y = pad_sequences(maxlen=max_len, sequences=y, padding="post", value=tag2idx["O"])
    # print(y[1])

    # 将label转为categorial
    y = [to_categorical(i, num_classes=n_tags) for i in y]

    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)
    print(X_train.shape, np.array(y_test).shape)
    print("正在保存数据")
    with open(dataset_dir,'wb') as out_data:
        pickle.dump([n_words, n_tags, max_len, words,tags,X_train, X_test, y_train, y_test],
                    out_data,pickle.HIGHEST_PROTOCOL)

    return n_words, n_tags, max_len, words,tags,X_train, X_test, y_train, y_test