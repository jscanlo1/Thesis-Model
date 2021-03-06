import numpy as np
import pickle
import bcolz
import dataset
import torch
import time
import torch.nn as nn
from torchtext import data, datasets, vocab
import torch.nn.functional as F
import pandas as pd
from keras.preprocessing import text
from keras.preprocessing.sequence import pad_sequences
from models.sent2emoModel import sent2emoModel
from keras.preprocessing.text import Tokenizer
from sklearn.metrics import f1_score,precision_score,accuracy_score

#########################################################
# Download necessary GLOVE vectors and details

vectors = bcolz.open(f'glove/6B.50.dat')[:]
words = pickle.load(open(f'glove/6B.50_words.pkl', 'rb'))
word2idx = pickle.load(open(f'glove/6B.50_idx.pkl', 'rb'))

glove = {w: vectors[word2idx[w]] for w in words}

#########################################################
# Create a vocab and dataset

# Convert Labels to ints
#vocab_ = dataset.Vocabulary_LIAR()
#vocab_ = dataset.Vocabulary_TWITTER()
vocab_ = dataset.Vocabulary_MELD()
# Paths to data files
# Paths should be to TWITTER file for sense training

'''
train_path = 'data/liar_dataset/train.tsv'
val_path = 'data/liar_dataset/valid.tsv'
test_path = 'data/liar_dataset/test.tsv'
'''
#train_path = 'data/TWITTER/twitter_training.csv'
#val_path = 'data/TWITTER/twitter_validation.csv'

train_path = 'data/MELD_Dyadic_dataset/train_sent_emo_dya.csv'
val_path = 'data/MELD_Dyadic_dataset/dev_sent_emo_dya.csv'

def ProcessingData(path,vocab):
    #For LIAR dataset
    '''
    data = pd.read_csv(path, sep='\t',header=None)

    text_items = data.iloc[:,2]
    text_labels = data.iloc[:,1]
    text_items = text_items.map(lambda x: dataset.cleantext(x))
    '''
    #For TWITTER dataset
    '''
    data = pd.read_csv(path,header=None)

    text_items = data.iloc[:,2]
    text_labels = data.iloc[:,1]
    text_items = text_items.map(lambda x: dataset.cleantext(x))
    '''
    
    #For Meld
    data = pd.read_csv(path, encoding="utf-8")
    text_items = data["Utterance"]
    text_labels = data["Emotion"]
    text_items = text_items.map(lambda x: dataset.cleantext(x))

    text_item_words = []
    text_item_label = []
    for i,(text_,label_) in enumerate(zip(text_items,text_labels)):
    #    print(f"TEXT: {text_} \t EMOTION: {label_}")
        _text_item = text_
        _label = [vocab.label2id[label_]]

        text_item_words.append(_text_item)
        text_item_label.append(_label)


    #Possibly make tensors
    return text_item_words, text_item_label


train_text,train_labels = ProcessingData(train_path,vocab_)
val_text,val_labels = ProcessingData(val_path,vocab_)
#test_text,test_labels = ProcessingData(test_path,vocab_)

dataset_vocab = set()

for text_ in train_text:
    for x in text_:
        dataset_vocab.update(x)



#t = Tokenizer(oov_token=1)
t = Tokenizer()
t.fit_on_texts(list(train_text) + list(val_text))
vocab_size = len(t.word_index) + 1
encoded_train = t.texts_to_sequences(train_text)
padded_train = pad_sequences(encoded_train, maxlen=128, truncating="post", padding='post')

encoded_val = t.texts_to_sequences(val_text)
padded_val = pad_sequences(encoded_val, maxlen=128, truncating="post", padding='post')

vocab_size = len(t.word_index) + 1


#Save tokenizer
with open("tokenizer.pickle","wb") as handle:
    pickle.dump(t,handle,protocol=pickle.HIGHEST_PROTOCOL)

######################################################
# Create a Glove Matrix for the Vocab
# Use a set so no repeats

matrix_len = len(dataset_vocab)
weights_matrix = np.zeros((matrix_len, 50))
words_found = 0

embedding_matrix = np.zeros((vocab_size, 50))
for word, i in t.word_index.items():
    try:
        embedding_vector = glove[word]
        embedding_matrix[i] = embedding_vector
    except KeyError:
        embedding_vector = np.random.normal(scale=0.6, size=(50,))
        
        embedding_matrix[i] = embedding_vector
'''
for i, word in enumerate(dataset_vocab):
    try: 
        weights_matrix[i] = glove[word]
        words_found += 1
    except KeyError:
        weights_matrix[i] = np.random.normal(scale=0.6, size=(50, ))

'''


#Pad the sequences
#padded_train_text = pad_sequences(train_text, maxlen=128, padding='post')
#padded_train_text = pad_sequences(train_text, maxlen=128, dtype="string", truncating="post", padding="post")


num_labels = vocab_.num_labels()

embedding_matrix = torch.tensor(embedding_matrix)

torch.save(embedding_matrix,"glove/embedding_matrix.pt")
#print(np.shape(x_data))


#print(len(padded_tweets[0]))
#print(padded_tweets[0])

################################
# convery all datasets to tokens
train_text = padded_train
val_text = padded_val






#######################################################
# Set up training

n_epochs = 5
model = sent2emoModel(embedding_matrix=embedding_matrix,max_features = matrix_len ,num_labels=num_labels)
loss_fn = nn.CrossEntropyLoss(reduction='sum')
optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=0.0005, betas= [0.9,0.999])
#model.cuda()

batch_size = 16
# Load train and test in CUDA Memory
#Set these to CUDA with .cuda()
#print(train_text[0])
#train_text = torch.from_numpy(train_text)
x_train = torch.tensor(train_text, dtype=torch.long)
y_train = torch.tensor(train_labels, dtype=torch.long)
x_cv = torch.tensor(val_text, dtype=torch.long)
y_cv = torch.tensor(val_labels, dtype=torch.long)
# Create Torch datasets
train = torch.utils.data.TensorDataset(x_train, y_train)
valid = torch.utils.data.TensorDataset(x_cv, y_cv)
# Create Data Loaders
train_loader = torch.utils.data.DataLoader(train, batch_size=batch_size, shuffle=True)
valid_loader = torch.utils.data.DataLoader(valid, batch_size=batch_size, shuffle=False)
train_loss = []
valid_loss = []
for epoch in range(n_epochs):
    size = len(train_loader.dataset)
    start_time = time.time()
    # Set model to train configuration
    model.train()
    avg_loss = 0.  
    loss_array = []
    train_label_pred = []
    train_label_gold = []

    for i, (x_batch, y_batch) in enumerate(train_loader):
        # Predict/Forward Pass
        y_pred = model(x_batch)
        # Compute loss

        y_pred_maxed = torch.argmax(y_pred,-1)
        train_label_pred.append(y_pred_maxed.detach().cpu().numpy())
        train_label_gold.append(y_batch.cpu().numpy())

        loss = loss_fn(y_pred, y_batch.flatten())
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        #avg_loss += loss.item() / len(train_loader)
        loss_array.append(loss.item())

        if i % 20 == 0:
                loss, current = loss.item()/len(y_batch), i * len(x_batch)
                print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")
    # Set model to validation configuration -Doesn't get trained here
    avg_loss = np.mean(loss_array)/batch_size

    train_label_pred = np.concatenate(train_label_pred)
    train_label_gold = np.concatenate(train_label_gold)

    train_acc = accuracy_score(train_label_gold, train_label_pred)
    train_f1 = f1_score(train_label_gold, train_label_pred, average='weighted')
    print(f"EPOCH: {epoch+1} \t Train Loss: {avg_loss} \t Train Acc: {train_acc} \t Train F1: {train_f1}")


    model.eval()        
    avg_val_loss = 0.
    val_preds = np.zeros((len(x_cv),num_labels))
    for i, (x_batch, y_batch) in enumerate(valid_loader):
        y_pred = model(x_batch).detach()
        avg_val_loss += loss_fn(y_pred, y_batch.flatten())
        # keep/store predictions
        val_preds[i * batch_size:(i+1) * batch_size] = F.softmax(y_pred,dim=1).cpu().numpy()
    # Check Accuracy
    print(np.shape(val_preds))
    val_accuracy = sum(val_preds.argmax(axis=1)==val_labels)/len(val_labels)
    print(np.shape(val_accuracy))
    #train_loss.append(avg_loss)
    
    train_loss.append(avg_loss)
    avg_val_loss /= len(valid_loader.dataset)
    valid_loss.append(avg_val_loss)
    elapsed_time = time.time() - start_time

    pred_flat = np.argmax(val_preds, axis=1)
    #labels_flat = val_labels.to('cpu').numpy()

    f1 = f1_score(val_labels,pred_flat, average='weighted')
    acc = accuracy_score(val_labels,pred_flat)
    print(f'EPOCH: {epoch+1} \t val_loss = {avg_val_loss} \t Val_ACC = {acc} \t val F1: {f1}')
    #print('Epoch {}/{} \t loss={:.4f} \t val_loss={:.4f}  \t val_acc={:.4f}'.format(epoch + 1, n_epochs, avg_loss, avg_val_loss, val_accuracy))
    #print('Epoch {}/{} \t loss={:.4f} \t val_loss={:.4f}  \t val_acc={:.4f}  \t time={:.2f}s'.format(epoch + 1, n_epochs, avg_loss, avg_val_loss, val_accuracy, elapsed_time))






################################################################
# Save the model

#torch.save(model.state_dict(), "saved_models/sent2emo.pt")
