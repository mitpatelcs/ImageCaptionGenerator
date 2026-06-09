const imageInput = document.getElementById("imageInput");
const uploadBtn = document.getElementById("uploadBtn");
const captionBtn = document.getElementById("captionBtn");
const preview = document.getElementById("preview");
const statusBox = document.getElementById("status");
const captionText = document.getElementById("captionText");
const audioPlayer = document.getElementById("audioPlayer");

let selectedFile = null;
let uploadId = null;

function setStatus(message) {
  statusBox.textContent = message;
}

function resetResult() {
  captionText.textContent = "-";
  audioPlayer.hidden = true;
  audioPlayer.removeAttribute("src");
}

imageInput.addEventListener("change", () => {
  selectedFile = imageInput.files[0];
  uploadId = null;
  captionBtn.disabled = true;
  resetResult();

  if (!selectedFile) {
    preview.innerHTML = "<span>No image selected</span>";
    setStatus("Waiting for an image.");
    return;
  }

  const imageUrl = URL.createObjectURL(selectedFile);
  preview.innerHTML = `<img src="${imageUrl}" alt="Selected image">`;
  setStatus(`Selected: ${selectedFile.name}`);
});

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus("Please select an image first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);

  uploadBtn.disabled = true;
  captionBtn.disabled = true;
  setStatus("Uploading image...");

  try {
    const response = await fetch("/upload-image", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed.");
    }

    const data = await response.json();
    uploadId = data.upload_id;
    captionBtn.disabled = false;
    setStatus("Image uploaded. Ready to generate caption.");
  } catch (error) {
    setStatus(error.message);
  } finally {
    uploadBtn.disabled = false;
  }
});

captionBtn.addEventListener("click", async () => {
  if (!uploadId) {
    setStatus("Please upload an image first.");
    return;
  }

  const formData = new FormData();
  formData.append("upload_id", uploadId);
  formData.append("generate_audio", "true");

  captionBtn.disabled = true;
  setStatus("Generating caption...");

  try {
    const response = await fetch("/generate-caption", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Caption generation failed.");
    }

    const data = await response.json();
    captionText.textContent = data.caption || "-";

    if (data.audio_url) {
      audioPlayer.src = data.audio_url;
      audioPlayer.hidden = false;
    } else {
      audioPlayer.hidden = true;
    }

    if (data.audio_error) {
      setStatus("Caption generated. Audio could not be generated.");
    } else {
      setStatus("Caption generated.");
    }
  } catch (error) {
    setStatus(error.message);
  } finally {
    captionBtn.disabled = false;
  }
});

