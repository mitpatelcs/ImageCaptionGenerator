import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from src.config import ARTIFACTS_DIR, MODEL_PATH, PROJECT_ROOT
from src.feature_extraction import build_feature_model, extract_image_feature
from src.inference import clean_generated_caption, load_caption_model, predict_caption
from src.preprocessing import get_max_length, load_pickle, load_text_artifacts
from src.text_to_speech import text_to_speech


UPLOAD_DIR = ARTIFACTS_DIR / "uploads"
AUDIO_DIR = ARTIFACTS_DIR / "audio"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

app = FastAPI(title="Image Caption Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

caption_model = None
feature_model = None
tokenizer = None
all_captions = None
max_length = None


def load_resources():
    """Load model and artifacts once, then reuse them for requests."""
    global caption_model, feature_model, tokenizer, all_captions, max_length

    if caption_model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError("Trained model not found at artifacts/model.h5")
        caption_model = load_caption_model(MODEL_PATH)

    if feature_model is None:
        feature_model = build_feature_model()

    if tokenizer is None or all_captions is None:
        tokenizer, _, all_captions = load_text_artifacts()
        max_length = get_max_length(all_captions)


def validate_image_file(file: UploadFile):
    """Check that the uploaded file looks like a supported image."""
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, and PNG images are supported.",
        )

    return extension


def verify_saved_image(path):
    """Make sure the uploaded file is a real image."""
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from error


def get_upload_path(upload_id):
    """Find an uploaded image by id."""
    matches = list(UPLOAD_DIR.glob(f"{upload_id}.*"))

    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded image not found.")

    return matches[0]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload-image")
def upload_image(file: UploadFile = File(...)):
    """Save an uploaded image and return its upload id."""
    extension = validate_image_file(file)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload_id = uuid4().hex
    saved_path = UPLOAD_DIR / f"{upload_id}{extension}"

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    verify_saved_image(saved_path)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "image_url": f"/uploads/{saved_path.name}",
    }


@app.post("/generate-caption")
def generate_caption(upload_id: str = Form(...), generate_audio: bool = Form(True)):
    """Generate a caption for a previously uploaded image."""
    try:
        load_resources()
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    image_path = get_upload_path(upload_id)
    image_feature = extract_image_feature(image_path, feature_model)
    raw_caption = predict_caption(caption_model, image_feature, tokenizer, max_length)
    caption = clean_generated_caption(raw_caption)

    audio_url = None
    audio_error = None

    if generate_audio:
        try:
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            audio_path = AUDIO_DIR / f"{upload_id}.mp3"
            text_to_speech(caption, audio_path=audio_path)
            audio_url = f"/audio/{audio_path.name}"
        except Exception as error:
            audio_error = str(error)

    return {
        "upload_id": upload_id,
        "caption": caption,
        "raw_caption": raw_caption,
        "audio_url": audio_url,
        "audio_error": audio_error,
    }


@app.get("/uploads/{filename}")
def get_uploaded_image(filename: str):
    path = UPLOAD_DIR / filename

    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")

    return FileResponse(path)


@app.get("/audio/{filename}")
def get_audio(filename: str):
    path = AUDIO_DIR / filename

    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")

    return FileResponse(path, media_type="audio/mpeg")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
