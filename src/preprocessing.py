import pickle
import re
from pathlib import Path

import pandas as pd
from tensorflow.keras.preprocessing.text import Tokenizer

from src.config import (
    ALL_CAPTIONS_PATH,
    ARTIFACTS_DIR,
    CAPTIONS_FILE,
    MAPPING_PATH,
    TOKENIZER_PATH,
)


def load_captions(captions_file=CAPTIONS_FILE):
    """Load the Flickr8k captions CSV."""
    return pd.read_csv(captions_file)


def clean_caption(caption):
    """Clean one caption and add start/end tokens."""
    caption = caption.lower()
    caption = re.sub(r"[^a-zA-Z\s]", "", caption)
    caption = " ".join(caption.split())
    return "startseq " + caption + " endseq"


def create_mapping(captions_df):
    """Create image_id -> cleaned captions mapping."""
    mapping = {}

    for _, row in captions_df.iterrows():
        image_id = row["image"].split(".")[0]
        caption = clean_caption(row["caption"])

        if image_id not in mapping:
            mapping[image_id] = []

        mapping[image_id].append(caption)

    return mapping


def get_all_captions(mapping):
    """Flatten the mapping into one list of captions."""
    all_captions = []

    for captions in mapping.values():
        all_captions.extend(captions)

    return all_captions


def create_tokenizer(all_captions):
    """Fit a Keras tokenizer on the cleaned captions."""
    tokenizer = Tokenizer()
    tokenizer.fit_on_texts(all_captions)
    return tokenizer


def get_vocab_size(tokenizer):
    """Keras word indexes start at 1, so we add 1 for padding token 0."""
    return len(tokenizer.word_index) + 1


def get_max_length(all_captions):
    """Find the longest cleaned caption length."""
    return max(len(caption.split()) for caption in all_captions)


def save_pickle(data, path):
    """Save any Python object as a pickle file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as file:
        pickle.dump(data, file)


def load_pickle(path):
    """Load a pickle file."""
    with open(path, "rb") as file:
        return pickle.load(file)


def save_text_artifacts(
    tokenizer,
    mapping,
    all_captions,
    tokenizer_path=TOKENIZER_PATH,
    mapping_path=MAPPING_PATH,
    all_captions_path=ALL_CAPTIONS_PATH,
):
    """Save tokenizer, mapping, and all captions."""
    save_pickle(tokenizer, tokenizer_path)
    save_pickle(mapping, mapping_path)
    save_pickle(all_captions, all_captions_path)


def load_text_artifacts(
    tokenizer_path=TOKENIZER_PATH,
    mapping_path=MAPPING_PATH,
    all_captions_path=ALL_CAPTIONS_PATH,
):
    """Load tokenizer, mapping, and all captions."""
    tokenizer = load_pickle(tokenizer_path)
    mapping = load_pickle(mapping_path)
    all_captions = load_pickle(all_captions_path)
    return tokenizer, mapping, all_captions


def run_text_preprocessing(captions_file=CAPTIONS_FILE, artifacts_dir=ARTIFACTS_DIR):
    """Run the full text preprocessing step and save its artifacts."""
    captions_df = load_captions(captions_file)
    mapping = create_mapping(captions_df)
    all_captions = get_all_captions(mapping)
    tokenizer = create_tokenizer(all_captions)

    save_text_artifacts(
        tokenizer,
        mapping,
        all_captions,
        Path(artifacts_dir) / "tokenizer.pkl",
        Path(artifacts_dir) / "mapping.pkl",
        Path(artifacts_dir) / "all_captions.pkl",
    )

    return tokenizer, mapping, all_captions

