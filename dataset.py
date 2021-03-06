import os
import re
import torch
import json
import numpy as np
from transformers import BertTokenizer
from torch.utils.data import Dataset
import pandas as pd
#import matplotlib.pyplot as plt
from collections import defaultdict
from keras.preprocessing.sequence import pad_sequences
from nltk.corpus import stopwords
#from torchMoji.torchmoji.sentence_tokenizer import SentenceTokenizer
#from torchMoji.torchmoji.model_def import torchmoji_emojis
#from torchMoji.torchmoji.global_variables import PRETRAINED_PATH, VOCAB_PATH



#Function for cleaning text can be tweaked
stops = set(stopwords.words("english"))
def cleantext(string):
    text = string.lower().split()
    text = " ".join(text)
    text = re.sub(r"http(\S)+",' ',text)    
    text = re.sub(r"www(\S)+",' ',text)
    text = re.sub(r"&",' and ',text)  
    tx = text.replace('&amp',' ')
    text = re.sub(r"[^0-9a-zA-Z]+",' ',text)
    text = text.split()
    text = [w for w in text if not w in stops]
    text = " ".join(text)
    return text

class Vocabulary_AAAI(object):
    def __init__(self):
        self.label2id = {"fake": 0,
                         "real": 1,
                         }
        self.id2label = {value: key for key, value in self.label2id.items()}

    def num_labels(self):
        return len(self.label2id)

class Vocabulary_LIAR(object):
    def __init__(self):
        self.label2id = {"pants-fire": 0,
                         "false": 1,
                         "barely-true": 2,
                         "half-true": 3,
                         "mostly-true": 4,
                         "true": 5
                         }
        self.id2label = {value: key for key, value in self.label2id.items()}

    def num_labels(self):
        return len(self.label2id)

class Vocabulary_MELD(object):
    def __init__(self):
        self.label2id = {"neutral": 0,
                         "surprise": 1,
                         "fear": 2,
                         "sadness": 3,
                         "joy": 4,
                         "anger": 5,
                         "disgust": 6}
        self.id2label = {value: key for key, value in self.label2id.items()}

    def num_labels(self):
        return len(self.label2id)

class Vocabulary_TSA(object):
    def __init__(self):
        self.label2id = {"Negative": 0,
                         "Neutral": 1,
                         "Positive": 2,
                         "Irrelevant": 3}
        self.id2label = {value: key for key, value in self.label2id.items()}

    def num_labels(self):
        return len(self.label2id)


class CustomDataset(Dataset):
    def __init__(self, text, deepMoji_input ,truth_labels, token_type_ids ,attention_masks, transform=None, target_transform=None):
        self.text = text
        self.truth_labels = truth_labels
        self.attention_masks = attention_masks
        self.token_type_ids = token_type_ids
        self.deepMoji_input = deepMoji_input
        #Dunno what transforms are
        self.transform = transform
        self.target_transform = target_transform

    def __len__(self):
        return len(self.truth_labels)

    def __getitem__(self, idx):
        
        text_item = self.text[idx]
        label = self.truth_labels[idx]

        emo_item = self.deepMoji_input[idx]


        if self.transform:
            image = self.transform(text_item)
        if self.target_transform:
            label = self.target_transform(label)

            #Potentially move conversion to tensors to init
            #

        return torch.LongTensor(text_item), torch.DoubleTensor(emo_item) ,torch.LongTensor(self.attention_masks[idx]), torch.LongTensor(self.token_type_ids[idx]), torch.LongTensor(label)




#datasettypetype refers to train test val
def load_data(input_max, dataset_type):
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    

    if dataset_type == 'AAAI':
        vocab = Vocabulary_AAAI()


        train_path = 'data/constraint_dataset/English_Train.xlsx'
        val_path = 'data/constraint_dataset/English_Val.xlsx'
        test_path = 'data/constraint_dataset/English_Test_With_Labels.xlsx'

    elif dataset_type == 'LIAR':
        vocab = Vocabulary_LIAR()
        train_path = 'data/liar_dataset/train.tsv'
        val_path = 'data/liar_dataset/valid.tsv'
        test_path = 'data/liar_dataset/test.tsv'

    elif dataset_type == 'FACEBUZZ':
        #Change to actual paths
        vocab = Vocabulary_AAAI()
        train_path = 'data/constraint_dataset/English_Train.xlsx'
        val_path = 'data/constraint_dataset/English_Val.xlsx'
        test_path = 'data/constraint_dataset/English_Test_With_Labels.xlsx'
    
    elif dataset_type == 'MELD':
        vocab = Vocabulary_MELD()
        
        train_path = 'data/MELD_Dyadic_dataset/test_sent_emo_dya.csv'
        val_path = 'data/MELD_Dyadic_dataset/dev_sent_emo_dya.csv'
        test_path = 'data/MELD_Dyadic_dataset/test_sent_emo_dya.csv'

    elif dataset_type == 'TSA':
        vocab = Vocabulary_TSA()
        
        train_path = 'data/Twitter_Sen_Analysis/twitter_training.csv'
        val_path = 'data/Twitter_Sen_Analysis/twitter_validation.csv'
        test_path = 'data/Twitter_Sen_Analysis/twitter_validation.csv'

    else:
        vocab = Vocabulary_AAAI()
        train_path = 'data/constraint_dataset/English_Train.xlsx'
        val_path = 'data/constraint_dataset/English_Val.xlsx'
        test_path = 'data/constraint_dataset/English_Test_With_Labels.xlsx'


    def processing_data(path, dataset_type_type):
        
        if dataset_type == 'AAAI':
            data = pd.read_excel(path)
            text_items = data["tweet"]
            text_labels = data["label"]

            if dataset_type_type == 'train':
                deepMoji_inputs = torch.load("deepMoji_inputs/AAAI/AAAI_train.pt")
            elif dataset_type_type == 'val':
                deepMoji_inputs = torch.load("deepMoji_inputs/AAAI/AAAI_val.pt")
            elif dataset_type_type == 'test':
                deepMoji_inputs = torch.load("deepMoji_inputs/AAAI/AAAI_test.pt")


        elif dataset_type == 'LIAR':
            data = pd.read_csv(path, sep='\t',header=None)
            text_items = data.iloc[:,2]
            text_labels = data.iloc[:,1]

            if dataset_type_type == 'train':
                deepMoji_inputs = torch.load("deepMoji_inputs/LIAR/LIAR_train.pt")
            elif dataset_type_type == 'val':
                deepMoji_inputs = torch.load("deepMoji_inputs/LIAR/LIAR_val.pt")
            elif dataset_type_type == 'test':
                deepMoji_inputs = torch.load("deepMoji_inputs/LIAR/LIAR_test.pt")


        elif dataset_type == 'MELD':
            data = pd.read_csv(path, encoding="utf-8")
            text_items = data["Utterance"]
            text_labels = data["Emotion"]


        else:
            print("INVALID DATASET TYPE")
            exit()

        #Handles Bert inputes
        text_input = []
        truth_label_input = []
        #emo_results = []
        
        for i, (text,label,emoji_probs) in enumerate(zip(text_items,text_labels,deepMoji_inputs)):
            #print(emoji_probs)
            BERT_text = tokenizer.encode(text)
            _truth_label_input = [vocab.label2id[label]]
            text_input.append(BERT_text)
            truth_label_input.append(_truth_label_input)

            #_emo_probs = [x for x in emoji_probs]
            #emo_results.append(_emo_probs)
            
        
        text_input = pad_sequences(text_input, maxlen=128, dtype="long", truncating="post", padding="post")
        attention_masks = []

        for seq in text_input:
            seq_mask = [float(i>0) for i in seq]
            attention_masks.append(seq_mask)

        #Possibly include token type ids
        #
        token_type_ids = []

        for x in text_input:
            seq_token_type_id = np.zeros_like(x)
            token_type_ids.append(seq_token_type_id)




        return CustomDataset(text_input, deepMoji_inputs, truth_label_input, token_type_ids, attention_masks)

    return (
               processing_data(train_path,'train'),
               processing_data(val_path, 'val'),
               processing_data(test_path, 'test')
           ), vocab
