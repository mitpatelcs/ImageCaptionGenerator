import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.utils import to_categorical

from src.config import RANDOM_STATE, TEST_SIZE


def get_image_ids(mapping):
    """Return image ids from the caption mapping."""
    return list(mapping.keys())


def split_image_ids(mapping, test_size=TEST_SIZE, random_state=RANDOM_STATE):
    """Create a stable train/test split by image id."""
    image_ids = get_image_ids(mapping)
    return train_test_split(image_ids, test_size=test_size, random_state=random_state)


def calculate_steps(data_keys, batch_size):
    """Number of image batches in one epoch."""
    return len(data_keys) // batch_size


def data_generator(data_keys, mapping, features, tokenizer, max_length, vocab_size, batch_size):
    """
    Yield batches for model training.

    One batch contains captions generated from `batch_size` images. Each image
    produces many training rows because every caption is split into multiple
    input-sequence / next-word pairs.
    """
    X1, X2, y = [], [], []
    image_count = 0

    while True:
        for key in data_keys:
            captions = mapping[key]

            for caption in captions:
                sequence = tokenizer.texts_to_sequences([caption])[0]

                for i in range(1, len(sequence)):
                    in_seq = sequence[:i]
                    out_seq = sequence[i]

                    in_seq = pad_sequences([in_seq], maxlen=max_length)[0]
                    out_seq = to_categorical([out_seq], num_classes=vocab_size)[0]

                    X1.append(features[key][0])
                    X2.append(in_seq)
                    y.append(out_seq)

            image_count += 1

            if image_count == batch_size:
                yield (
                    {
                        "image": np.array(X1),
                        "text": np.array(X2),
                    },
                    np.array(y),
                )

                X1, X2, y = [], [], []
                image_count = 0

