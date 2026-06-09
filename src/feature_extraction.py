import os

import numpy as np
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tqdm import tqdm

from src.config import FEATURE_SHAPE, FEATURES_PATH, IMAGE_SIZE, IMAGES_DIR
from src.preprocessing import save_pickle


def build_feature_model():
    """Create the VGG16 model that returns fc2 image features."""
    vgg_model = VGG16()
    feature_model = Model(
        inputs=vgg_model.inputs,
        outputs=vgg_model.get_layer("fc2").output,
    )
    return feature_model


def extract_image_feature(image_path, model, image_size=IMAGE_SIZE):
    """Extract one image feature vector with VGG16 preprocessing."""
    image = load_img(image_path, target_size=image_size)
    image = img_to_array(image)
    image = image.reshape((1, image_size[0], image_size[1], 3))
    image = preprocess_input(image)

    feature = model.predict(image, verbose=0)
    return feature.astype("float32")


def extract_features(images_dir=IMAGES_DIR, model=None):
    """Extract VGG16 features for every JPG image in a directory."""
    if model is None:
        model = build_feature_model()

    features = {}

    for image_name in tqdm(sorted(os.listdir(images_dir))):
        if not image_name.lower().endswith(".jpg"):
            continue

        image_path = os.path.join(images_dir, image_name)
        image_id = image_name.split(".")[0]
        features[image_id] = extract_image_feature(image_path, model)

    return features


def check_features(features):
    """Basic safety checks before saving or training with image features."""
    if not features:
        raise ValueError("No image features found.")

    sample = next(iter(features.values()))

    if sample.shape != FEATURE_SHAPE:
        raise ValueError(f"Expected feature shape {FEATURE_SHAPE}, got {sample.shape}.")

    if np.isnan(sample).any():
        raise ValueError("Feature vector contains NaN values.")

    if sample.min() < 0:
        raise ValueError("VGG16 fc2 features should be non-negative.")


def save_features(features, path=FEATURES_PATH):
    """Validate and save extracted image features."""
    check_features(features)
    save_pickle(features, path)


def run_feature_extraction(images_dir=IMAGES_DIR, features_path=FEATURES_PATH):
    """Extract all image features and save them to features.pkl."""
    model = build_feature_model()
    features = extract_features(images_dir, model)
    save_features(features, features_path)
    return features

