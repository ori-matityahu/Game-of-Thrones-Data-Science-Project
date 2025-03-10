import numpy as np
import re
import matplotlib.pyplot as plt
from keras.layers import Embedding, SpatialDropout1D, LSTM, Dense, Input, Concatenate
from keras.models import Model
from keras_preprocessing.sequence import pad_sequences
from keras_preprocessing.text import Tokenizer
from keras.callbacks.callbacks import History
from keras.utils import to_categorical
from nltk.corpus import stopwords
from split_data_and_labels import TEXT_FILENAME, LABELS_FILENAME

REPLACE_BY_SPACE_RE = re.compile('[/(){}\[\]\|@,;]')
BAD_SYMBOLS_RE = re.compile('[^0-9a-z #+_]')
STOPWORDS = set(stopwords.words('english'))

MAX_NB_WORDS = 50000
MAX_SEQUENCE_LENGTH = 250
EMBEDDING_DIM = 100

NUMBER_OF_CLASSES = 30

SPECIAL_FEATURES = 9


def remove_classes(text: np.ndarray, labels: np.ndarray) -> tuple:
    """[summary]
    remove the classes in not top 30
    Arguments:
        text {[numpy array]} -- the text array
        labels {[numpy array]} -- the lables array
    
    Returns:
        [tuple] -- the new text and labels
    """
    rows_ind = []
    bins = range(np.max(labels))
    histogram, bins = np.histogram(labels, bins=bins)
    arg = np.array(list(reversed(np.argsort(histogram))))
    indexes = arg[:NUMBER_OF_CLASSES]
    for i in range(len(labels)):
        if labels[i] in indexes:
            rows_ind.append(i)
    rows_ind = np.array(rows_ind)
    text = text[rows_ind]
    labels = labels[rows_ind]
    labels = np.array([np.where(indexes == labels[i])[0] for i in range(len(labels))]).reshape((-1,))
    return text, labels


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


def get_data_and_labels():
    data = clean_data()
    labels = np.load(LABELS_FILENAME, allow_pickle=True)
    return data, labels


def tokenize_words(data: np.ndarray) -> np.ndarray:
    """[summary]
    tokenize the given data
    Arguments:
        data {[numpy array]} -- the text data
    
    Returns:
        [numpy array] -- the tokenized data
    """
    tokenizer = Tokenizer(num_words=MAX_NB_WORDS, filters='!"#$%&()*+,-./:;<=>?@[\]^_`{|}~', lower=True)
    tokenizer.fit_on_texts(data)
    x = tokenizer.texts_to_sequences(data)
    x = pad_sequences(x, maxlen=MAX_SEQUENCE_LENGTH)
    additional = np.array([additional_features(data[i]) for i in range(len(data))])
    x = np.hstack((x, additional))
    return x


def labels_to_numbers(labels: np.ndarray) -> np.ndarray:
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
    build the model
    Arguments:
        input_length {[int]} -- the input size
        number_of_classes {[int]} -- the number of classes
    
    Returns:
        [Model] -- the built model
    """
    input_tensor = Input(shape=(input_length,))
    tensor = Embedding(MAX_NB_WORDS, EMBEDDING_DIM)(input_tensor)
    tensor = SpatialDropout1D(0.2)(tensor)
    tensor = LSTM(100, dropout=0.5, recurrent_dropout=0.2)(tensor)
    second_input = Input(shape=(SPECIAL_FEATURES,))
    tensor = Concatenate()([tensor, second_input])
    tensor = Dense(100, activation='relu')(tensor)
    tensor = Dense(number_of_classes, activation='softmax')(tensor)
    model = Model(inputs=[input_tensor, second_input], outputs=tensor)
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    print(model.summary())
    return model


def train_model(model: Model, x_train: list, y_train: np.ndarray) -> History:
    epochs = 10
    batch_size = 64

    history = model.fit(x_train, y_train, epochs=epochs, batch_size=batch_size, validation_split=0.1)
    return history


def additional_features(text):
    """adds the following additional features:
    Average Word Length
    Average Sentence Length By Word
    Average Sentence Length By Character
    Special Character Count

    Arguments:
        text {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    # symbols:
    f = [text.count("?"), text.count("!"), text.count(","), text.count("-"), text.count(".")]

    # avg sentence length
    text_splitted_to_sentences = re.findall(r"[\w',\- ]+", text)
    sub_sentences_count = len(text_splitted_to_sentences)
    if sub_sentences_count == 0:
        sub_sentences_count = 1
    words = re.findall(r"[\w']+", text)
    if len(words) == 0:
        words = []
        # smoothing
        words_count = 1
    else:
        words_count = len(words)
    avg_sentence_length = words_count / sub_sentences_count

    # avg word len
    letters_counter = 0
    for _ in words:
        letters_counter = letters_counter + words_count
    avg_word_len = letters_counter / words_count
    return np.asarray(f + [avg_sentence_length, avg_word_len, words_count, letters_counter])


if __name__ == "__main__":
    text_data, labels = get_data_and_labels()
    x = tokenize_words(text_data)
    labels = labels_to_numbers(labels)

    x, labels = remove_classes(x, labels)
    y = to_categorical(labels, NUMBER_OF_CLASSES)

    # x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.1)
    model = build_model(MAX_SEQUENCE_LENGTH, NUMBER_OF_CLASSES)
    history = train_model(model, [x[:, :MAX_SEQUENCE_LENGTH], x[:, MAX_SEQUENCE_LENGTH:]], y)
    # accuracy = model.evaluate(x_test, y_test)
    # print("Accuracy:", accuracy)

    plt.title('Loss')
    plt.plot(history.history['loss'], label='train')
    plt.plot(history.history['val_loss'], label='validation')
    plt.legend()
    plt.show()

    plt.title('Accuracy')
    plt.plot(history.history['accuracy'], label='train')
    plt.plot(history.history['val_accuracy'], label='validation')
    plt.legend()
    plt.show()
