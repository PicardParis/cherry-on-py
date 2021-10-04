"""
Copyright 2020-2021 Google LLC

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
import datetime
from pathlib import Path

import flask
from PIL import Image

import faces

Annotations = faces.Annotations
Options = faces.ResultOptions

DIR_STATIC = "www/static"

app = flask.Flask(__name__, static_folder=DIR_STATIC, template_folder="www/templates")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = datetime.timedelta(minutes=10)
demo_samples = Path(DIR_STATIC, "samples")


@app.get("/")
def index():
    return flask.render_template("home.html", images=local_images())


@app.post("/analyze-image")
def analyze_image():
    if (image_file := flask.request.files.get("image")) is not None:
        annotations = faces.detect_faces(image_file.read())
    elif (file_name := flask.request.form.get("file_name")) is not None:
        sample_path = demo_samples.joinpath(file_name)
        annotations = get_local_image_annotations(sample_path)
    else:
        return "Could not open input image in /analyze-image", 400

    return flask.jsonify(
        faces_detected=len(annotations.face_annotations),
        annotations=encode_annotations(annotations),
    )


@app.post("/process-image")
def process_image():
    if (base64_annotations := flask.request.form.get("annotations")) is None:
        return "Missing annotations: call /analyze-image first", 400
    annotations = decode_annotations(base64_annotations)
    if annotations is None:
        return "Could not decode annotations", 400

    if (image_file := flask.request.files.get("image")) is not None:
        image = Image.open(image_file)
    elif (file_name := flask.request.form.get("file_name")) is not None:
        image = Image.open(demo_samples.joinpath(file_name))
    else:
        return "Could not open input image in /process-image", 400

    options = options_from_request_form()
    image_io = faces.render_result(image, annotations, options)
    return flask.send_file(image_io, mimetype=f"image/{options.image_format}")


def local_images():
    suffixes = (".jpg", ".jpeg", ".webp", ".png")
    return (p.name for p in demo_samples.glob("*") if p.suffix.lower() in suffixes)


def get_local_image_annotations(sample_path: Path) -> Annotations:
    json_path = sample_path.with_suffix(f"{sample_path.suffix}.json")
    if json_path.is_file():
        json = json_path.read_text(encoding="utf-8")  # Use cached json file
        return Annotations(Annotations.from_json(json))

    with sample_path.open("rb") as sample_file:
        annotations = faces.detect_faces(sample_file.read())

    json = Annotations.to_json(
        annotations,
        # Arbitrary options for more readable json (closer to Python)
        including_default_value_fields=False,
        use_integers_for_enums=False,
        preserving_proto_field_name=True,
    )
    json_path.write_text(json, encoding="utf-8")  # Cache json file

    return annotations


def encode_annotations(annotations: Annotations) -> str:
    binary_data = Annotations.serialize(annotations)
    base64_data = base64.urlsafe_b64encode(binary_data)
    base64_annotations = base64_data.decode("ascii")
    return base64_annotations


def decode_annotations(base64_annotations: str) -> Annotations:
    base64_data = base64_annotations.encode("ascii")
    binary_data = base64.urlsafe_b64decode(base64_data)
    return Annotations(Annotations.deserialize(binary_data))


def options_from_request_form() -> Options:
    def to_bool(option: str) -> bool:
        return flask.request.form.get(option, default=0, type=int) == 1

    return Options(
        animated=to_bool("animated"),
        crop_faces=to_bool("crop-faces"),
        crop_image=to_bool("crop-image"),
        image_format=flask.request.form.get("image-format", default="png"),
        landmarks=to_bool("landmarks"),
        anonymize=to_bool("anonymize"),
        stache=to_bool("stache"),
        oscillating=to_bool("oscillating"),
        bouncing=to_bool("bouncing"),
    )


if __name__ == "__main__":
    # Local tests only (service account needed if calls are made to the API)
    # Run "python main.py" (3.9+) and open http://localhost:8080
    app.run(host="localhost", port=8080, debug=True)
