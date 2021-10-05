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

from google.cloud import storage, videointelligence

ANNOTATION_BUCKET = os.getenv("ANNOTATION_BUCKET", "")
assert ANNOTATION_BUCKET, "Undefined ANNOTATION_BUCKET environment variable"


def launch_object_tracking(video_uri: str, annot_bucket: str):
    """Detect and track video objects (asynchronously)

    Results will be stored in <annot_uri> with this naming convention:
    - video_uri: gs://video_bucket/path/to/video.ext
    - annot_uri: gs://annot_bucket/video_bucket/path/to/video.ext.json
    """
    print(f"Launching object tracking for <{video_uri}>...")
    features = [videointelligence.Feature.OBJECT_TRACKING]
    video_blob = storage.Blob.from_string(video_uri)
    video_bucket = video_blob.bucket.name
    path_to_video = video_blob.name
    annot_uri = f"gs://{annot_bucket}/{video_bucket}/{path_to_video}.json"
    request = dict(features=features, input_uri=video_uri, output_uri=annot_uri)

    video_client = videointelligence.VideoIntelligenceServiceClient()
    video_client.annotate_video(request)


def gcf_track_objects(data, context):
    """Cloud Function triggered by a new Cloud Storage object"""
    video_bucket = data["bucket"]
    path_to_video = data["name"]
    video_uri = f"gs://{video_bucket}/{path_to_video}"
    launch_object_tracking(video_uri, ANNOTATION_BUCKET)


def gcf_track_objects_http(request):
    """Cloud Function triggered by an HTTP GET request"""
    if request.method != "GET":
        return ("Please use a GET request", 403)
    if not request.args or "video_uri" not in request.args:
        return ('Please specify a "video_uri" parameter', 400)
    video_uri = request.args["video_uri"]
    launch_object_tracking(video_uri, ANNOTATION_BUCKET)
    return f"Launched object tracking for <{video_uri}>"


if __name__ == "__main__":
    # Local tests only (service account needed)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "video_uri", type=str, help="gs://video_bucket/path/to/video.ext"
    )
    args = parser.parse_args()
    launch_object_tracking(args.video_uri, ANNOTATION_BUCKET)
