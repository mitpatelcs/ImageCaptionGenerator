import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

from src.config import MODEL_PATH


def load_caption_model(model_path=MODEL_PATH):
    """Load the trained caption model for inference."""
    return load_model(model_path, compile=False)


def create_index_to_word(tokenizer):
    """Create index -> word lookup from the tokenizer."""
    return {index: word for word, index in tokenizer.word_index.items()}


def clean_generated_caption(caption):
    """Remove start/end tokens from a generated caption."""
    return caption.replace("startseq", "").replace("endseq", "").strip()


def predict_caption(model, image_feature, tokenizer, max_length):
    """Generate one caption using greedy search."""
    index_to_word = create_index_to_word(tokenizer)
    text = "startseq"

    for _ in range(max_length):
        sequence = tokenizer.texts_to_sequences([text])[0]
        sequence = pad_sequences([sequence], maxlen=max_length)

        y_pred = model.predict([image_feature, sequence], verbose=0)
        predicted_index = int(np.argmax(y_pred))
        word = index_to_word.get(predicted_index)

        if word is None:
            break

        text += " " + word

        if word == "endseq":
            break

    return text


def predict_caption_from_image_id(model, image_id, features, tokenizer, max_length):
    """Generate a clean caption for one image id from pre-extracted features."""
    caption = predict_caption(model, features[image_id], tokenizer, max_length)
    return clean_generated_caption(caption)
