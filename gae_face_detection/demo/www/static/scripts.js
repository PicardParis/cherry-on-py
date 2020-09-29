/*
Copyright 2020 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
const eSourceTestImage = document.getElementById("source-test-image");
const eSourceCustomImage = document.getElementById("source-custom-image");
const eSourceCamera = document.getElementById("source-camera");

const eTestImageInput = document.getElementById("test-image-input");
const eCustomImageInput = document.getElementById("custom-image-input");
const eDropZone = document.getElementById("drop-zone");
const eCameraInput = document.getElementById("camera-input");
const eStartCamera = document.getElementById("start-camera");

const eResultImageOptions = document.getElementById("result-image-options");
const eWebpLabel = document.getElementById("webp-label");
const eWebp = document.getElementById("webp");
const ePng = document.getElementById("png");
const eGif = document.getElementById("gif");
const eShowLogs = document.getElementById("show-logs");
const eLogs = document.getElementById("logs");
const eLogEntries = document.getElementById("log-entries");

const eStill = document.getElementById("still");
const eAnimated = document.getElementById("animated");
const eStillImageOptions = document.getElementById("still-image-options");
const eLandmarks = document.getElementById("landmarks");
const eAnonymize = document.getElementById("anonymize");
const eStache = document.getElementById("stache");
const eAnimatedImageOptions = document.getElementById("animated-image-options");
const eOscillating = document.getElementById("oscillating");
const eBouncing = document.getElementById("bouncing");

const eCropFaces = document.getElementById("crop-faces");
const eCropImage = document.getElementById("crop-image");

const eResult = document.getElementById("result");
const eResultLegend = document.getElementById("result-legend");
const eResultContainer = document.getElementById("result-container");
const eCopyToClipboard = document.getElementById("button-copy-to-clipboard");
const eDownloadImage = document.getElementById("button-download-image");
const eResultImage = document.getElementById("result-image");

const eOverlay = document.getElementById("overlay");
const eOverlayClose = document.getElementById("overlay-close");
const eButtonSelfie = document.getElementById("button-selfie");
const eVideo = document.getElementById("camera");
const clipboardSupported = (typeof ClipboardItem !== "undefined");

const DEFAULT_TEST_IMAGE = "American_Gothic.jpg";
const VIDEO_DIM = 600;

// The backend API can be called successively with different rendering options.
// Cache image analyses and blobs to only call the Vision API once per new picture.
const modeEnum = Object.freeze({ "none": null, "camera": 0, "customImage": 1, "testImage": 2, "count": 3 });
const gAnalysis = Array(modeEnum.count).fill(null);
const gImageObj = Array(modeEnum.count).fill(null);

init();

function init() {
    overrideConsole();

    // Default options
    eSourceTestImage.checked = true;
    document.querySelector(`input[value="${DEFAULT_TEST_IMAGE}"]`).checked = true;
    if (webpSupported()) {
        eWebpLabel.hidden = false;
        eWebp.checked = true;
    } else
        ePng.checked = true;
    eStill.checked = true;
    eShowLogs.checked = !eLogs.hidden;
    eStache.checked = true;
    eOscillating.checked = true;

    // Events
    for (input of document.getElementsByTagName("input"))
        input.onchange =
            (input.name === "test-image") ? onTestImageChanged
                : (input.id === "show-logs") ? onShowLogs
                    : onNewConfig;
    eDropZone.onclick = onImageSelect;
    eDropZone.ondragenter = eDropZone.ondragleave = onDragEnterLeave;
    eDropZone.ondragover = onDragOver;
    eDropZone.ondrop = onFileDrop;
    eStartCamera.onclick = startCamera;
    eButtonSelfie.onclick = takeSelfie;
    eOverlayClose.onclick = closeCameraOverlay;
    eResultImage.onclick = eDownloadImage.onclick = downloadResultImage;
    eCopyToClipboard.onclick = copyResultImageToClipboard;

    onNewConfig();
}

function onNewConfig() {
    eCameraInput.hidden = !eSourceCamera.checked;
    eCustomImageInput.hidden = !eSourceCustomImage.checked;
    eTestImageInput.hidden = !eSourceTestImage.checked;
    eStillImageOptions.hidden = eAnimated.checked;
    eAnimatedImageOptions.hidden = !eAnimated.checked;
    eResult.hidden = true;
    eResultImage.onload = _ => { eResult.hidden = false };

    processImage();
}

async function analyzeImage(formData) {
    const image = formData.get("image");
    if (image)
        console.log("→ /analyze-image…");

    let chrono = performance.now();
    const params = { method: "POST", body: formData };
    const response = await fetch("/analyze-image", params);
    if (!response.ok) {
        console.error(`# HTTP error: ${response.status}`);
        return null;
    }
    chrono = performance.now() - chrono;

    if (image)
        console.log(`← /analyze-image | ${Math.round(chrono)} ms | ${image.size} bytes`);
    return response.json();
}

async function processImage() {
    const formData = new FormData();
    const analysis = await fillFormOptions(formData);
    if (!analysis)
        return;
    eResultLegend.textContent = `Result (faces: ${analysis.faces_detected})`;
    console.log("→ /process-image…");

    let chrono = performance.now();
    const params = { method: "POST", body: formData };
    const response = await fetch("/process-image", params);
    if (!response.ok) {
        console.error(`# HTTP error: ${response.status}`);
        return;
    }
    chrono = performance.now() - chrono;

    // Define an image title with creation date + image type
    // The image title will be used as the filename on image download
    const resultBlob = await response.blob();
    const fileDate = new Date().toISOString().split(".")[0];
    const fileType = resultBlob.type.split("image/")[1];
    eResultImage.title = `FaceDetection_${fileDate}.${fileType}`;
    if (!!eResultImage.src)
        URL.revokeObjectURL(eResultImage.src);
    eResultImage.src = URL.createObjectURL(resultBlob);

    console.log(`← /process-image | ${Math.round(chrono)} ms | ${analysis.faces_detected} face(s) | ${resultBlob.size} bytes`);
}

async function fillFormOptions(formData) {
    const mode =
        eSourceCamera.checked ? modeEnum.camera
            : eSourceCustomImage.checked ? modeEnum.customImage
                : eSourceTestImage.checked ? modeEnum.testImage
                    : modeEnum.none;
    switch (mode) {
        case modeEnum.camera:
        case modeEnum.customImage:
            if (!gImageObj[mode])
                return null;
            formData.append("image", gImageObj[mode]);
            break;
        case modeEnum.testImage:
            const testImage = document.querySelector("input[name='test-image']:checked");
            if (!testImage)
                return null;
            formData.append("file_name", testImage.value);
            break;
        default:
            return null;
    }

    if (!gAnalysis[mode])
        gAnalysis[mode] = await analyzeImage(formData);
    const analysis = gAnalysis[mode];
    if (!analysis)
        return null;

    formData.append("annotations", analysis.annotations);
    function checkedToInt(e) { return e.checked ? 1 : 0; }
    formData.append("animated", checkedToInt(eAnimated));
    formData.append("crop-faces", checkedToInt(eCropFaces));
    formData.append("crop-image", checkedToInt(eCropImage));
    formData.append("image-format", document.querySelector("input[name='image-format']:checked").id);
    if (eAnimated.checked) {
        formData.append("oscillating", checkedToInt(eOscillating));
        formData.append("bouncing", checkedToInt(eBouncing));
    } else {
        formData.append("landmarks", checkedToInt(eLandmarks));
        formData.append("anonymize", checkedToInt(eAnonymize));
        formData.append("stache", checkedToInt(eStache));
    }

    return analysis;
}

// Source: test image

function onTestImageChanged() {
    gAnalysis[modeEnum.testImage] = null;
    onNewConfig();
}

// Source: custom image

function onImageSelect() {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = false;
    input.accept = "image/*";
    input.onchange = ev => { if (1 <= ev.target.files.length) onCustomImage(ev.target.files[0]); };
    input.click();
}

function onDragOver(ev) {
    ev.preventDefault();
}

function onDragEnterLeave(ev) {
    ev.preventDefault();
    const img = (ev.type === "dragenter") ? firstImage(ev.dataTransfer) : null;
    eDropZone.className = (img) ? "drop-zone-ok" : "drop-zone-idle";
}

function onFileDrop(ev) {
    ev.preventDefault();
    eDropZone.className = "drop-zone-idle";
    const img = firstImage(ev.dataTransfer);
    if (img)
        onCustomImage(img.getAsFile());
}

function firstImage(dataTransfer) {
    if (!dataTransfer || !dataTransfer.items) {
        console.log("DataTransfer is not supported");
        return null;
    }
    for (const item of dataTransfer.items)
        if (item.kind === "file" && item.type.startsWith("image/"))
            return item;
    return null;
}

function onCustomImage(file) {
    console.log(`New custom image | ${file.size} bytes`);
    // Copy file into memory blob (file is not persistent on Safari)
    const reader = new FileReader();
    reader.onload = _ => {
        gAnalysis[modeEnum.customImage] = null;
        gImageObj[modeEnum.customImage] = new Blob([reader.result], { type: file.type });
        onNewConfig();
    };
    reader.readAsArrayBuffer(file);
}

// Source: camera

document.addEventListener("keydown", event => { if (event.key === "Escape") closeCameraOverlay(); });

async function startCamera() {
    const stream = await openCamera(VIDEO_DIM, VIDEO_DIM);
    eVideo.srcObject = stream;
    await eVideo.play();
    eOverlay.hidden = false;
    console.log(`Camera resolution: ${eVideo.videoWidth}×${eVideo.videoHeight}`);
}

function stopCamera() {
    const stream = eVideo.srcObject;
    if (!stream)
        return;
    stream.getTracks().forEach(track => track.stop());
    eVideo.srcObject = null;
}

function closeCameraOverlay() {
    stopCamera();
    eOverlay.hidden = true;
}

function openCamera(width, height) {
    const constraints = {
        audio: false,
        video: { width, height },
        facingMode: "user"
    }
    return navigator.mediaDevices.getUserMedia(constraints);
}

function takeSelfie() {
    eVideo.pause();
    const canvas = document.createElement("canvas");
    canvas.width = eVideo.videoWidth;
    canvas.height = eVideo.videoHeight;
    canvas.getContext("2d").drawImage(eVideo, 0, 0);
    canvas.toBlob(onNewSelfieBlob);
}

function onNewSelfieBlob(blob) {
    console.log(`New selfie | ${blob.size} bytes`);
    gAnalysis[modeEnum.camera] = null;
    gImageObj[modeEnum.camera] = blob;
    stopCamera();
    eOverlay.hidden = true;
    onNewConfig();
}

// Result image copy/download

eResult.addEventListener("mouseenter", _ => {
    eDownloadImage.hidden = false;
    eCopyToClipboard.hidden = !(clipboardSupported && eStill.checked);
});

eResult.addEventListener("mouseleave", _ => {
    eDownloadImage.hidden = eCopyToClipboard.hidden = true;
});

function downloadResultImage() {
    const link = document.createElement("a");
    link.href = eResultImage.src;
    link.download = eResultImage.title;
    link.click();
    console.log(`Image download triggered | ${link.download}`);
}

function copyResultImageToClipboard() {
    // Clipboard copy does not support "image/webp" or "image/gif"
    // Convert the result image using the default mime type ("image/png")
    const canvas = document.createElement("canvas");
    canvas.width = eResultImage.naturalWidth;
    canvas.height = eResultImage.naturalHeight;
    canvas.getContext("2d").drawImage(eResultImage, 0, 0);
    canvas.toBlob(async (blob) => {
        const data = [new ClipboardItem({ [blob.type]: blob })];
        await navigator.clipboard.write(data);
        console.log("Image copied to clipboard");
    });
}

// Misc

function webpSupported() {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    return canvas.toDataURL("image/webp").startsWith("data:image/webp");
}

function overrideConsole() {
    ["log", "debug", "warn", "error", "info"].forEach(overrideLogFunction);
}

function overrideLogFunction(logFunctionName) {
    const overridenFunction = `overriden${logFunctionName}`;
    console[overridenFunction] = console[logFunctionName];
    console[logFunctionName] = function (...args) {
        eLogEntries.innerHTML += args.reduce((output, arg) => `${output}<span>${arg}</span><br>`, "");
        eLogEntries.scrollTop = eLogEntries.scrollHeight;
        console[overridenFunction].apply(undefined, args);
    };
}

function onShowLogs() {
    eLogs.hidden = !eShowLogs.checked;
    eLogEntries.scrollTop = eLogEntries.scrollHeight;
}
