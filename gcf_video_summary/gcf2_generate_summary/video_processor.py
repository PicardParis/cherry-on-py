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
import logging
from io import BytesIO
from typing import Dict, Iterator, List, NamedTuple, Tuple, Type

import cv2 as cv
from PIL import Image

from storage_helper import StorageHelper


class VideoProcessor:
    class ImageSize(NamedTuple):
        w: int
        h: int

    storage: StorageHelper
    video: cv.VideoCapture
    cell_size: ImageSize
    grid_size: ImageSize

    SUMMARY_MAX_SIZE = ImageSize(1920, 1080)
    RGB_BACKGROUND = (0x80, 0x80, 0x80)
    ANIMATION_FRAME_DURATION_MS = 333
    ANIMATION_FRAMES = 6
    assert 2 <= ANIMATION_FRAMES

    class ImageFormat:
        # See https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
        image_format: str
        save_parameters: Dict  # Make a copy if updated

    class ImageJpeg(ImageFormat):
        image_format = 'jpeg'
        save_parameters = dict(optimize=True, progressive=True)

    class ImageGif(ImageFormat):
        image_format = 'gif'
        save_parameters = dict(optimize=True)

    class ImagePng(ImageFormat):
        image_format = 'png'
        save_parameters = dict(optimize=True)

    class ImageWebP(ImageFormat):
        image_format = 'webp'
        save_parameters = dict(lossless=False, quality=80, method=1)

    SUMMARY_STILL_FORMATS = (ImageJpeg, ImagePng, ImageWebP)
    SUMMARY_ANIMATED_FORMATS = (ImageGif, ImagePng, ImageWebP)

    @staticmethod
    def generate_summary(annot_uri: str, output_bucket: str, animated=False):
        """ Generate a video summary from video shot annotations """
        try:
            with StorageHelper(annot_uri, output_bucket) as storage:
                with VideoProcessor(storage) as video_proc:
                    print('Generating summary...')
                    if animated:
                        video_proc.generate_summary_animations()
                    else:
                        video_proc.generate_summary_stills()
        except:
            logging.exception(
                'Could not generate summary from shot annotations <%s>',
                annot_uri)

    def __init__(self, storage: StorageHelper):
        self.storage = storage

    def __enter__(self):
        video_path = self.storage.video_local_path
        self.video = cv.VideoCapture(str(video_path))
        if not self.video.isOpened():
            raise RuntimeError(f'Could not open video <{video_path}>')
        self.compute_grid_dimensions()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.video.release()

    def compute_grid_dimensions(self):
        shot_count = self.storage.shot_count()
        if shot_count < 1:
            raise RuntimeError(f'Expected 1+ video shots (got {shot_count})')
        # Try to preserve the video aspect ratio
        # Consider cells as pixels and try to fit them in a square
        cols = rows = int(shot_count ** 0.5 + 0.5)
        if cols * rows < shot_count:
            cols += 1
        cell_w = int(self.video.get(cv.CAP_PROP_FRAME_WIDTH))
        cell_h = int(self.video.get(cv.CAP_PROP_FRAME_HEIGHT))
        if self.SUMMARY_MAX_SIZE.w < cell_w*cols:
            scale = self.SUMMARY_MAX_SIZE.w / (cell_w*cols)
            cell_w = int(scale * cell_w)
            cell_h = int(scale * cell_h)
        self.cell_size = self.ImageSize(cell_w, cell_h)
        self.grid_size = self.ImageSize(cell_w*cols, cell_h*rows)

    def generate_summary_stills(self):
        image = self.render_summary()
        for image_format in self.SUMMARY_STILL_FORMATS:
            self.upload_summary([image], image_format)

    def generate_summary_animations(self):
        frame_count = self.ANIMATION_FRAMES
        images = []
        for frame_index in range(frame_count):
            shot_ratio = (frame_index+1) / (frame_count+1)
            print(f'shot_ratio: {shot_ratio:.0%}')
            image = self.render_summary(shot_ratio)
            images.append(image)
        for image_format in self.SUMMARY_ANIMATED_FORMATS:
            self.upload_summary(images, image_format)

    def render_summary(self, shot_ratio: float = 0.5) -> Image:
        grid_img = Image.new('RGB', self.grid_size, self.RGB_BACKGROUND)

        img_and_pos_iter = zip(self.gen_cell_img(shot_ratio),
                               self.gen_cell_pos())
        for cell_img, cell_pos in img_and_pos_iter:
            cell_img.thumbnail(self.cell_size)  # Make it smaller if needed
            grid_img.paste(cell_img, cell_pos)

        return grid_img

    def gen_cell_img(self, shot_ratio: float) -> Iterator['Image']:
        assert 0.0 <= shot_ratio <= 1.0
        MS_IN_NS = 10**6
        for video_shot in self.storage.gen_video_shots():
            pos1_ns, pos2_ns = video_shot
            pos_ms = (pos1_ns + shot_ratio*(pos2_ns-pos1_ns)) / MS_IN_NS
            yield self.image_at_pos(pos_ms)

    def gen_cell_pos(self) -> Iterator[Tuple[int, int]]:
        cell_x, cell_y = 0, 0
        while True:
            yield cell_x, cell_y
            cell_x += self.cell_size.w
            if self.grid_size.w <= cell_x:  # Move to next row?
                cell_x, cell_y = 0, cell_y+self.cell_size.h

    def image_at_pos(self, pos_ms: float) -> Image:
        self.video.set(cv.CAP_PROP_POS_MSEC, pos_ms)
        ok, cv_frame = self.video.read()
        if not ok:
            raise RuntimeError(f'Failed to get video frame @pos_ms[{pos_ms}]')
        return Image.fromarray(cv.cvtColor(cv_frame, cv.COLOR_BGR2RGB))

    def upload_summary(self,
                       images: List['Image'],
                       image_format: Type[ImageFormat]):
        if not images:
            raise RuntimeError('Empty image list')
        mem_file = BytesIO()
        image_type = image_format.image_format
        save_parameters = dict(image_format.save_parameters)  # Copy
        animated = 1 < len(images)
        if animated:
            save_parameters.update(dict(
                save_all=True,
                append_images=images[1:],
                duration=self.ANIMATION_FRAME_DURATION_MS,
                loop=0,  # Infinite loop
            ))
        images[0].save(mem_file, format=image_type, **save_parameters)

        image_bytes = mem_file.getvalue()
        self.storage.upload_summary(image_bytes, image_type, animated)
