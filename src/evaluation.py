from nltk.translate.bleu_score import corpus_bleu

from src.inference import clean_generated_caption, predict_caption


def prepare_references(captions):
    """Convert cleaned reference captions into token lists for BLEU."""
    return [clean_generated_caption(caption).split() for caption in captions]


def evaluate_model(model, test_ids, mapping, features, tokenizer, max_length, limit=200):
    """Generate captions for test images and calculate BLEU-1 and BLEU-2."""
    actual, predicted = [], []

    for image_id in test_ids[:limit]:
        caption = predict_caption(model, features[image_id], tokenizer, max_length)

        actual.append(prepare_references(mapping[image_id]))
        predicted.append(clean_generated_caption(caption).split())

    bleu_1 = corpus_bleu(actual, predicted, weights=(1.0, 0, 0, 0))
    bleu_2 = corpus_bleu(actual, predicted, weights=(0.5, 0.5, 0, 0))

    return bleu_1, bleu_2

