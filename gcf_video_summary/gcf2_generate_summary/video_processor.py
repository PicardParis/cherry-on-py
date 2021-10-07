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
import logging
from io import BytesIO
from typing import Iterator, NamedTuple

import cv2 as cv
from PIL import Image

from storage_helper import StorageHelper

PilImage = Image.Image
ImageSize = NamedTuple("ImageSize", [("w", int), ("h", int)])
ImageFormat = NamedTuple("ImageFormat", [("type", str), ("save_parameters", dict)])

SUMMARY_MAX_SIZE = ImageSize(1920, 1080)
RGB_BACKGROUND = (0x80, 0x80, 0x80)
ANIMATION_FRAME_DURATION_MS = 333
ANIMATION_FRAMES = 6
assert 2 <= ANIMATION_FRAMES

IMAGE_JPEG = ImageFormat("jpeg", dict(optimize=True, progressive=True))
IMAGE_GIF = ImageFormat("gif", dict(optimize=True))
IMAGE_PNG = ImageFormat("png", dict(optimize=True))
IMAGE_WEBP = ImageFormat("webp", dict(lossless=False, quality=80, method=1))
SUMMARY_STILL_FORMATS = (IMAGE_JPEG, IMAGE_PNG, IMAGE_WEBP)
SUMMARY_ANIMATED_FORMATS = (IMAGE_GIF, IMAGE_PNG, IMAGE_WEBP)


class VideoProcessor:
    storage: StorageHelper
    video: cv.VideoCapture
    cell_size: ImageSize
    grid_size: ImageSize

    @staticmethod
    def generate_summary(annot_uri: str, output_bucket: str, animated=False):
        """Generate a video summary from video shot annotations"""
        try:
            with StorageHelper(annot_uri, output_bucket) as storage:
                with VideoProcessor(storage) as video_proc:
                    print("Generating summary...")
                    if animated:
                        video_proc.generate_summary_animations()
                    else:
                        video_proc.generate_summary_stills()
        except Exception:
            logging.exception("Could not generate summary from <%s>", annot_uri)

    def __init__(self, storage: StorageHelper):
        self.storage = storage

    def __enter__(self):
        video_path = self.storage.video_local_path
        self.video = cv.VideoCapture(str(video_path))
        if not self.video.isOpened():
            raise RuntimeError(f"Could not open video <{video_path}>")
        self.compute_grid_dimensions()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.video.release()

    def compute_grid_dimensions(self):
        shot_count = len(self.storage.video_shots)
        if shot_count < 1:
            raise RuntimeError(f"Expected 1+ video shots (got {shot_count})")
        # Try to preserve the video aspect ratio
        # Consider cells as pixels and try to fit them in a square
        cols = rows = int(shot_count ** 0.5 + 0.5)
        if cols * rows < shot_count:
            cols += 1
        cell_w = int(self.video.get(cv.CAP_PROP_FRAME_WIDTH))
        cell_h = int(self.video.get(cv.CAP_PROP_FRAME_HEIGHT))
        if SUMMARY_MAX_SIZE.w < cell_w * cols:
            scale = SUMMARY_MAX_SIZE.w / (cell_w * cols)
            cell_w = int(scale * cell_w)
            cell_h = int(scale * cell_h)
        self.cell_size = ImageSize(cell_w, cell_h)
        self.grid_size = ImageSize(cell_w * cols, cell_h * rows)

    def generate_summary_stills(self):
        image = self.render_summary()
        for image_format in SUMMARY_STILL_FORMATS:
            self.upload_summary([image], image_format)

    def generate_summary_animations(self):
        frame_count = ANIMATION_FRAMES
        images = []
        for frame_index in range(frame_count):
            shot_ratio = (frame_index + 1) / (frame_count + 1)
            print(f"shot_ratio: {shot_ratio:.0%}")
            image = self.render_summary(shot_ratio)
            images.append(image)
        for image_format in SUMMARY_ANIMATED_FORMATS:
            self.upload_summary(images, image_format)

    def render_summary(self, shot_ratio: float = 0.5) -> PilImage:
        grid_img = Image.new("RGB", self.grid_size, RGB_BACKGROUND)

        img_and_pos_iter = zip(self.gen_cell_img(shot_ratio), self.gen_cell_pos())
        for cell_img, cell_pos in img_and_pos_iter:
            cell_img.thumbnail(self.cell_size)  # Makes it smaller if needed
            grid_img.paste(cell_img, cell_pos)

        return grid_img

    def gen_cell_img(self, shot_ratio: float) -> Iterator[PilImage]:
        assert 0.0 <= shot_ratio <= 1.0
        MS_IN_NS = 10 ** 6
        for video_shot in self.storage.video_shots:
            pos1_ns, pos2_ns = video_shot
            pos_ms = (pos1_ns + shot_ratio * (pos2_ns - pos1_ns)) / MS_IN_NS
            yield self.frame_at_position(pos_ms)

    def gen_cell_pos(self) -> Iterator[tuple[int, int]]:
        cell_x, cell_y = 0, 0
        while True:
            yield cell_x, cell_y
            cell_x += self.cell_size.w
            if self.grid_size.w <= cell_x:  # Move to next row?
                cell_x, cell_y = 0, cell_y + self.cell_size.h

    def frame_at_position(self, pos_ms: float) -> PilImage:
        self.video.set(cv.CAP_PROP_POS_MSEC, pos_ms)
        _, cv_frame = self.video.read()
        return Image.fromarray(cv.cvtColor(cv_frame, cv.COLOR_BGR2RGB))

    def upload_summary(self, images: list[PilImage], image_format: ImageFormat):
        if not images:
            raise RuntimeError("Empty image list")
        mem_file = BytesIO()
        image_type = image_format.type
        save_parameters = image_format.save_parameters.copy()
        if animated := 1 < len(images):
            save_parameters |= dict(
                save_all=True,
                append_images=images[1:],
                duration=ANIMATION_FRAME_DURATION_MS,
                loop=0,  # Infinite loop
            )
        images[0].save(mem_file, format=image_type, **save_parameters)

        image_bytes = mem_file.getvalue()
        self.storage.upload_summary(image_bytes, image_type, animated)
