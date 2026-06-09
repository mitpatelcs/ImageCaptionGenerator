from tensorflow.keras.layers import LSTM, Dense, Dropout, Embedding, Input, add
from tensorflow.keras.models import Model


def build_caption_model(vocab_size, max_length):
    """Build the image captioning model used in the notebooks."""
    image_input = Input(shape=(4096,), name="image")
    image_dropout = Dropout(0.3)(image_input)
    image_dense = Dense(256, activation="relu")(image_dropout)

    text_input = Input(shape=(max_length,), name="text")
    text_embedding = Embedding(vocab_size, 256)(text_input)
    text_dropout = Dropout(0.3)(text_embedding)
    text_lstm = LSTM(256)(text_dropout)

    decoder = add([image_dense, text_lstm])
    decoder = Dense(256, activation="relu")(decoder)
    output = Dense(vocab_size, activation="softmax")(decoder)

    model = Model(inputs=[image_input, text_input], outputs=output)
    model.compile(loss="categorical_crossentropy", optimizer="adam")

    return model

