import pandas as pd
import numpy as np
import re
import csv
import matplotlib.pyplot as plt
from keras.layers import Embedding, SpatialDropout1D, LSTM, Dense, Input, Concatenate
from keras.models import Model
from keras_preprocessing.sequence import pad_sequences
from keras_preprocessing.text import Tokenizer
from keras.callbacks.callbacks import History
from nltk.corpus import stopwords
from sklearn.model_selection import train_test_split
from split_data_and_labels import TEXT_FILENAME, LABELS_FILENAME

import features
from configure import *
import ast

REPLACE_BY_SPACE_RE = re.compile('[/(){}\[\]\|@,;]')
BAD_SYMBOLS_RE = re.compile('[^0-9a-z #+_]')
STOPWORDS = set(stopwords.words('english'))

MAX_NB_WORDS = 50000
MAX_SEQUENCE_LENGTH = 250
EMBEDDING_DIM = 100

NUMBER_OF_CLASSES = 15

SPECIAL_FEATURES = 539 - 250


def create_vector_labels(labels: np.ndarray) -> np.ndarray:
    """[summary]
    create vector of labels
    Arguments:
        labels {[numpy array]} -- the label string vector
    
    Returns:
        [numpy array] -- the label vectors
    """
    labels = [ast.literal_eval(label) for label in labels]
    all_characters = set()
    for label in labels:
        for ch in label:
            all_characters.add(ch)
    number_of_labels = len(labels)
    number_of_characters = len(all_characters)
    all_characters = list(all_characters)
    all_characters_dict = {all_characters[i]: i for i in range(number_of_characters)}
    new_labels = np.zeros((number_of_labels, number_of_characters))
    for i, label in enumerate(labels):
        for ch in label:
            ch_idx = all_characters_dict[ch]
            new_labels[i, ch_idx] = 1
    return new_labels


def clean_text(text):
    """
        text: a string

        return: modified initial string
    """
    text = text.lower()  # lowercase text
    text = REPLACE_BY_SPACE_RE.sub(' ',
                                   text)  # replace REPLACE_BY_SPACE_RE symbols by space in text. substitute the matched string in REPLACE_BY_SPACE_RE with space.
    text = BAD_SYMBOLS_RE.sub('',
                              text)  # remove symbols which are in BAD_SYMBOLS_RE from text. substitute the matched string in BAD_SYMBOLS_RE with nothing.
    text = ' '.join(word for word in text.split() if word not in STOPWORDS)  # remove stopwors from text
    text = text.replace("\\d+", "")
    return text


def clean_data():
    text = np.load(TEXT_FILENAME, allow_pickle=True)
    text = np.array(list(map(clean_text, text)))
    return text


def get_data_and_labels(data):
    data = clean_data()
    labels = np.load(LABELS_FILENAME, allow_pickle=True)
    return data, labels


def tokenize_words(data: np.ndarray) -> np.ndarray:
    """[summary]
    tokenize the words, and add additional features
    Arguments:
        data {[numpy array]} -- the data
    
    Returns:
        [numpy array] -- the tokenized data, with additional features
    """
    tokenizer = Tokenizer(num_words=MAX_NB_WORDS, filters='!"#$%&()*+,-./:;<=>?@[\]^_`{|}~', lower=True)
    lines = data[:, 6]
    tokenizer.fit_on_texts(lines)
    x = tokenizer.texts_to_sequences(lines)
    x = pad_sequences(x, maxlen=MAX_SEQUENCE_LENGTH)

    additional_2 = np.array([features.create_features(data[i])[0] for i in range(len(data))])
    x = np.hstack((x, additional_2))
    return x


def labels_to_numbers(labels: np.ndarray) -> np.ndarray:
    """[summary]
    convert the labels to number labels
    Arguments:
        labels {[numpy array]} -- the array of text labels
    
    Returns:
        [numpy array] -- the array of number labels
    """
    labels_dict = {}
    curr_idx = 0
    for label in labels:
        if label not in labels_dict.keys():
            labels_dict[label] = curr_idx
            curr_idx += 1
    numbers = np.array([labels_dict[label] for label in labels])
    return numbers


def build_model(input_length: int, number_of_classes: int) -> Model:
    """[summary]
    build lstm model
    Arguments:
        input_length {[int]} -- the input size
        number_of_classes {[int]} -- the number of classes
    
    Returns:
        [Model] -- the built model
    """
    input_tensor = Input(shape=(input_length,))
    tensor = Embedding(MAX_NB_WORDS, EMBEDDING_DIM)(input_tensor)
    tensor = SpatialDropout1D(0.2)(tensor)
    tensor = LSTM(100, dropout=0.2, recurrent_dropout=0.2)(tensor)
    second_input = Input(shape=(SPECIAL_FEATURES,))
    tensor = Concatenate()([tensor, second_input])
    tensor = Dense(100, activation='relu')(tensor)
    tensor = Dense(number_of_classes, activation='softmax')(tensor)
    model = Model(inputs=[input_tensor, second_input], outputs=tensor)
    model.compile(loss='mse', optimizer='adam')
    print(model.summary())
    return model


def train_model(model: Model, x_train: list, y_train: np.ndarray) -> History:
    """[summary]
    train the model on the given data
    Arguments:
        model {[Model]} -- the model to train
        x_train {[type]} -- the data to train on
        y_train {[type]} -- the labels to train on
    
    Returns:
        [History] -- the model train history
    """
    epochs = 10
    batch_size = 64

    history = model.fit(x_train, y_train, epochs=epochs, batch_size=batch_size, validation_split=0.1)
    return history


def calculate_accuracy(model: Model, x: np.ndarray, y: np.ndarray) -> float:
    """[summary]
    calculate the model accuracy on the x as data and y as labels
    Arguments:
        model {[Model]} -- the NN model
        x {[numpy array]} -- the data
        y {[numpy array]} -- the labels
    
    Returns:
        [float] -- the accuracy
    """
    n = y.shape[0]
    y_predicted = model.predict([x[:, :MAX_SEQUENCE_LENGTH], x[:, MAX_SEQUENCE_LENGTH:]])
    predicted_indexes = np.argmax(y_predicted, axis=1)
    in_y = y[np.arange(n), predicted_indexes]
    accuracy = float(np.sum(in_y)) / n
    return accuracy


if __name__ == "__main__":
    data = pd.read_csv('../../part2_data_cleaned_15_characters.csv', delimiter=',', header=None).to_numpy()
    text_data, labels = data[:, :-1], data[:, -1]

    x = tokenize_words(text_data)
    # labels = labels_to_numbers(labels)

    y = create_vector_labels(labels)
    # y = to_categorical(labels, NUMBER_OF_CLASSES)

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1)

    np.save("x_train", x_train)
    np.save("x_test", x_test)
    np.save("y_train", y_train)
    np.save("y_test", y_test)

    # x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1)
    model = build_model(MAX_SEQUENCE_LENGTH, NUMBER_OF_CLASSES)
    history = train_model(model, [x_train[:, :MAX_SEQUENCE_LENGTH], x_train[:, MAX_SEQUENCE_LENGTH:]], y_train)
    # accuracy = model.evaluate(x_test, y_test)
    # print("Accuracy:", accuracy)

    model.save_weights("weights.h5")

    plt.title('Loss')
    plt.plot(history.history['loss'], label='train')
    plt.plot(history.history['val_loss'], label='validation')
    plt.legend()
    plt.show()

    test_loss = model.evaluate(x_test, y_test)
    print("Test Loss:", test_loss)

    plt.title('Accuracy')
    plt.plot(history.history['accuracy'], label='train')
    plt.plot(history.history['val_accuracy'], label='validation')
    plt.legend()
    plt.show()

    x_train, x_test, y_train, y_test = np.load("x_train.npy"), np.load("x_test.npy"), \
                                       np.load("y_train.npy"), np.load("y_test.npy")
    model = build_model(MAX_SEQUENCE_LENGTH, NUMBER_OF_CLASSES)
    model.load_weights("weights.h5")
    train_accuracy = calculate_accuracy(model, x_train, y_train)
    test_accuracy = calculate_accuracy(model, x_test, y_test)
    print("Train Accuracy:", train_accuracy)
    print("Test Accuracy:", test_accuracy)

    data = pd.read_csv('../../part2_data_cleaned_15_characters.csv', delimiter=',', header=None).to_numpy()
    text_data, labels = data[:, :-1], data[:, -1]

    x = tokenize_words(text_data)
    # labels = labels_to_numbers(labels)

    y = create_vector_labels(labels)
    # y = to_categorical(labels, NUMBER_OF_CLASSES)

    n = x.shape[0]
    labels = np.random.randint(0, NUMBER_OF_CLASSES, n)
    in_y = y[np.arange(n), labels]
    accuracy = float(np.sum(in_y)) / n
    print(accuracy)
