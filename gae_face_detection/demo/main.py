"""
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
"""
import base64
from pathlib import Path
from typing import Optional
import datetime

import flask
from google.protobuf import json_format
from PIL import Image

import faces

PilImage = Image.Image
Annotations = faces.Annotations
Options = faces.ResultOptions

DIR_STATIC = "www/static"
DIR_TESTS = f"{DIR_STATIC}/tests"

app = flask.Flask(__name__, static_folder=DIR_STATIC, template_folder="www/templates")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = datetime.timedelta(minutes=10)


@app.route("/")
def index():
    return flask.render_template("home.html", images=local_images())


@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    if (image_file := flask.request.files.get("image")) is not None:
        annotations = faces.detect_faces(image_file.read())
    elif (file_name := flask.request.form.get("file_name")) is not None:
        annotations = get_local_image_annotations(file_name)
    else:
        return "Could not open input image in /analyze-image", 400

    return flask.jsonify(
        faces_detected=len(annotations.face_annotations),
        annotations=encode_annotations(annotations),
    )


@app.route("/process-image", methods=["POST"])
def process_image():
    if (base64_annotations := flask.request.form.get("annotations")) is None:
        return "Missing annotations: call /analyze-image first", 400
    annotations = decode_annotations(base64_annotations)
    if annotations is None:
        return "Could not decode annotations", 400

    if (image_file := flask.request.files.get("image")) is not None:
        image = Image.open(image_file)
    elif (file_name := flask.request.form.get("file_name")) is not None:
        image = Image.open(f"{DIR_TESTS}/{file_name}")
    else:
        return "Could not open input image in /process-image", 400

    options = options_from_request_form()
    image_io = faces.render_result(image, annotations, options)
    return flask.send_file(image_io, mimetype=f"image/{options.image_format}")


def local_images():
    suffixes = (".jpg", ".jpeg", ".webp", ".png")
    return (p.name for p in Path(DIR_TESTS).glob("*") if p.suffix.lower() in suffixes)


def get_local_image_annotations(file_name: str) -> Optional[Annotations]:
    annotations_path = f"{DIR_TESTS}/{file_name}.json"
    if (annotations := read_annotations(annotations_path)) is not None:
        return annotations

    with open(f"{DIR_TESTS}/{file_name}", "rb") as image_file:
        image_bytes = image_file.read()
    annotations = faces.detect_faces(image_bytes)
    save_annotations(annotations, annotations_path)

    return annotations


def encode_annotations(annotations: Annotations) -> str:
    binary_data = annotations.SerializeToString()
    base64_data = base64.urlsafe_b64encode(binary_data)
    base64_annotations = base64_data.decode("ascii")
    return base64_annotations


def decode_annotations(base64_annotations: str) -> Annotations:
    base64_data = base64_annotations.encode("ascii")
    binary_data = base64.urlsafe_b64decode(base64_data)
    return Annotations.FromString(binary_data)


def read_annotations(annotations_path: str) -> Optional[Annotations]:
    if not Path(annotations_path).is_file():
        return None
    with open(annotations_path, "r") as f:
        data = f.read()
    return json_format.Parse(data, Annotations())


def save_annotations(annotations: Annotations, annotations_path: str):
    with open(annotations_path, "w") as f:
        f.write(json_format.MessageToJson(annotations))


def options_from_request_form() -> Options:
    def to_bool(option: str) -> bool:
        return flask.request.form.get(option, default=0, type=int) == 1

    return Options(
        animated=to_bool("animated"),
        crop_faces=to_bool("crop-faces"),
        crop_image=to_bool("crop-image"),
        image_format=flask.request.form.get("image-format", default="png", type=str),
        landmarks=to_bool("landmarks"),
        anonymize=to_bool("anonymize"),
        stache=to_bool("stache"),
        oscillating=to_bool("oscillating"),
        bouncing=to_bool("bouncing"),
    )


if __name__ == "__main__":
    # For local tests only, run "python main.py" (3.8+) and open http://localhost:8080
    app.run(host="localhost", port=8080, debug=True)
