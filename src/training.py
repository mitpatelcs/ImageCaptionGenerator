from src.config import BATCH_SIZE, DEFAULT_EPOCHS, HISTORY_PATH, MODEL_PATH
from src.data_generator import calculate_steps, data_generator, split_image_ids
from src.model_builder import build_caption_model
from src.preprocessing import get_max_length, get_vocab_size, save_pickle


def train_model(
    features,
    mapping,
    tokenizer,
    all_captions,
    epochs=DEFAULT_EPOCHS,
    batch_size=BATCH_SIZE,
):
    """Train the caption model and return the model, history, and split ids."""
    vocab_size = get_vocab_size(tokenizer)
    max_length = get_max_length(all_captions)

    train_ids, test_ids = split_image_ids(mapping)
    steps_per_epoch = calculate_steps(train_ids, batch_size)

    model = build_caption_model(vocab_size, max_length)
    generator = data_generator(
        train_ids,
        mapping,
        features,
        tokenizer,
        max_length,
        vocab_size,
        batch_size,
    )

    history = model.fit(
        generator,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        verbose=1,
    )

    return model, history, train_ids, test_ids


def save_training_outputs(model, history, model_path=MODEL_PATH, history_path=HISTORY_PATH):
    """Save the trained model and training history."""
    model.save(model_path)
    save_pickle(history.history, history_path)

