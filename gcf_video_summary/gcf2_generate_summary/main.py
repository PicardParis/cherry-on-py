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
import os

from video_processor import VideoProcessor

SUMMARY_BUCKET = os.getenv('SUMMARY_BUCKET', '')
assert SUMMARY_BUCKET, 'Undefined SUMMARY_BUCKET environment variable'
ANIMATED = os.getenv('ANIMATED', '0') == '1'


def gcf_generate_summary(data, context):
    """ Cloud Function triggered by a new Cloud Storage object """
    annotation_bucket = data['bucket']
    path_to_annotation = data['name']
    annot_uri = f'gs://{annotation_bucket}/{path_to_annotation}'
    VideoProcessor.generate_summary(annot_uri, SUMMARY_BUCKET, ANIMATED)


if __name__ == '__main__':
    """ Only for local tests """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('annot_uri',
                        type=str,
                        help='gs://annotation_bucket/path/to/video.ext.json')
    args = parser.parse_args()
    VideoProcessor.generate_summary(args.annot_uri, SUMMARY_BUCKET, ANIMATED)
