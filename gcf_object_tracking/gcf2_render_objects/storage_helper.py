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
import json
import tempfile
from pathlib import Path

from google.cloud import storage
from google.cloud import videointelligence as vi

ANNOT_EXT = ".json"


class StorageHelper:
    """Local+Cloud storage helper

    - Uses a temp dir for local processing (e.g. video frame extraction)
    - Paths are relative to this temp dir (named after the output bucket)

    Naming convention:
    - video_uri:               gs://video_bucket/path/to/video.ext
    - annot_uri:  gs://annot_bucket/video_bucket/path/to/video.ext.json
    - video_path:                   video_bucket/path/to/video.ext
    - image_path:                   video_bucket/path/to/video.ext.SUFFIX
    - image_uri: gs://output_bucket/video_bucket/path/to/video.ext.SUFFIX
    """

    client = storage.Client()
    annotations: vi.AnnotateVideoResponse
    video_path: Path
    video_local_path: Path
    upload_bucket: storage.Bucket

    def __init__(self, annot_uri: str, output_bucket: str):
        if not annot_uri.endswith(ANNOT_EXT):
            raise RuntimeError(f"annot_uri must end with <{ANNOT_EXT}>")
        self.annotations = self.get_annotations(annot_uri)
        self.video_path = self.video_path_from_uri(annot_uri)
        temp_root = Path(tempfile.gettempdir(), output_bucket)
        temp_root.mkdir(parents=True, exist_ok=True)
        self.video_local_path = temp_root.joinpath(self.video_path)
        self.upload_bucket = self.client.bucket(output_bucket)

    def get_annotations(self, annot_uri: str) -> vi.AnnotateVideoResponse:
        json_blob = storage.Blob.from_string(annot_uri, self.client)
        json_bytes = json_blob.download_as_bytes()
        mapping = json.loads(json_bytes)
        return vi.AnnotateVideoResponse(mapping)

    def __enter__(self):
        self.download_video()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.video_local_path.unlink()

    def video_path_from_uri(self, annot_uri: str) -> Path:
        annot_blob = storage.Blob.from_string(annot_uri)
        return Path(annot_blob.name[: -len(ANNOT_EXT)])

    def download_video(self):
        video_uri = f"gs://{self.video_path.as_posix()}"
        blob = storage.Blob.from_string(video_uri, self.client)
        print(f"Downloading -> {self.video_local_path}")
        self.video_local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(self.video_local_path)

    def upload_image(self, image_bytes: bytes, image_type: str, filename_suffix: str):
        path = self.image_path(image_type, filename_suffix)
        blob = self.upload_bucket.blob(path.as_posix())
        content_type = f"image/{image_type}"
        print(f"Uploading -> {blob.name}")
        blob.upload_from_string(image_bytes, content_type)

    def image_path(self, image_type: str, filename_suffix) -> Path:
        video_name = self.video_path.name
        image_name = f"{video_name}.{filename_suffix}.{image_type}"
        return Path(self.video_path.parent, image_name)
