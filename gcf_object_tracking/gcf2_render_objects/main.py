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
import os

from video_processor import VideoProcessor

OBJECT_BUCKET = os.getenv("OBJECT_BUCKET", "")
assert OBJECT_BUCKET, "Undefined OBJECT_BUCKET environment variable"
ANIMATED = os.getenv("ANIMATED", "0") == "1"


def gcf_render_objects(data, context):
    """Cloud Function triggered by a new Cloud Storage object"""
    annotation_bucket = data["bucket"]
    path_to_annotation = data["name"]
    annot_uri = f"gs://{annotation_bucket}/{path_to_annotation}"
    VideoProcessor.render_objects(annot_uri, OBJECT_BUCKET, ANIMATED)


if __name__ == "__main__":
    # Local tests only (service account needed)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "annot_uri", type=str, help="gs://annotation_bucket/path/to/video.ext.json"
    )
    args = parser.parse_args()
    VideoProcessor.render_objects(args.annot_uri, OBJECT_BUCKET, ANIMATED)
