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
from io import BytesIO
from typing import Iterator, NamedTuple, Optional, Union

import cv2 as cv
from google.cloud import videointelligence as vi
from PIL import Image, ImageDraw, ImageFont

from storage_helper import StorageHelper

PilImage = Image.Image
PilFrames = Union[PilImage, Iterator[PilImage]]
ImageSize = NamedTuple("ImageSize", [("w", int), ("h", int)])

MIN_CONFIDENCE = 0.7  # Ignore objects with lower confidence
MIN_FRAMES = 10  # Ignore objects with lower number of detected frames
BACKGROUND_COLOR = "#808080"
BBOX_COLOR = "#00FF00"  # Color of bounding box and caption
BBOX_WIDTH_PX = 4  # Width of bounding box

# FreeSansBold is preinstalled in Cloud Functions runtimes (fonts-freefont-ttf)
# See https://cloud.google.com/functions/docs/reference/system-packages
FONT = "arial.ttf" if os.name == "nt" else "FreeSansBold.ttf"
FONT_SIZE_RATIO = 0.08  # Ratio // mininum dimension (width, height)
FONT_BG_COLOR = "#00000040"
IMAGE_MAX_SIZE = ImageSize(1920, 1080)
ANIM_FIXED_DURATION_MS = 250
ANIM_MAX_FRAMES = 12  # Max number of generated frames for animations
SUMMARY_SUFFIX = f"summary_pct{int(MIN_CONFIDENCE*100):02}_fr{MIN_FRAMES:02}"
ANIM_SUFFIX_FMT = "{index:03}_{entity}_pct{confidence}_fr{frames}"


class VideoProcessor:
    storage: StorageHelper
    animated: bool
    annotations: vi.AnnotateVideoResponse
    object_count: int
    video: Optional[cv.VideoCapture] = None
    cell_size: ImageSize
    grid_size: ImageSize
    font: ImageFont.FreeTypeFont
    font_height: int

    @staticmethod
    def render_objects(annot_uri: str, output_bucket: str, animated: bool):
        """Render objects from video annotations"""
        with StorageHelper(annot_uri, output_bucket) as storage:
            with VideoProcessor(storage, animated) as video_proc:
                print(f"Objects to render: {video_proc.object_count}")
                if animated:
                    video_proc.render_object_animations()
                else:
                    video_proc.render_object_summary()

    def __init__(self, storage: StorageHelper, animated: bool):
        self.storage = storage
        self.animated = animated

    def __enter__(self):
        self.annotations = self.storage.annotations
        self.object_count = len(list(self.gen_video_objects_filtered()))
        if self.object_count == 0:
            return self
        video_path = self.storage.video_local_path
        self.video = cv.VideoCapture(str(video_path))
        if not self.video.isOpened():
            raise RuntimeError(f"Could not open video <{video_path}>")
        self.compute_dimensions()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.video is not None:
            self.video.release()

    def gen_video_objects_filtered(self) -> Iterator[vi.ObjectTrackingAnnotation]:
        for obj in self.annotations.annotation_results[0].object_annotations:
            if all([MIN_CONFIDENCE <= obj.confidence, MIN_FRAMES <= len(obj.frames)]):
                yield obj

    def compute_dimensions(self):
        cell_w = int(self.video.get(cv.CAP_PROP_FRAME_WIDTH))
        cell_h = int(self.video.get(cv.CAP_PROP_FRAME_HEIGHT))
        if self.animated:
            cols = rows = 1
        else:
            # Grid trying to preserve the video aspect ratio
            cols = rows = int(self.object_count ** 0.5 + 0.5)
            if cols * rows < self.object_count:
                cols += 1
        if IMAGE_MAX_SIZE.w < cell_w * cols:
            scale = IMAGE_MAX_SIZE.w / (cell_w * cols)
            cell_w = int(scale * cell_w)
            cell_h = int(scale * cell_h)
        self.cell_size = ImageSize(cell_w, cell_h)
        self.grid_size = ImageSize(cell_w * cols, cell_h * rows)

        font_size = int(FONT_SIZE_RATIO * min(cell_w, cell_h) + 0.5)
        self.font = ImageFont.truetype(FONT, size=font_size)
        ascend, descend = self.font.getmetrics()
        self.font_height = ascend + descend

    def render_object_summary(self):
        if self.object_count == 0:
            return
        grid_img = Image.new("RGB", self.grid_size, BACKGROUND_COLOR)

        img_and_pos_iter = zip(self.gen_cell_img(), self.gen_cell_pos())
        for cell_img, cell_pos in img_and_pos_iter:
            grid_img.paste(cell_img, cell_pos)

        self.upload_image(grid_img, SUMMARY_SUFFIX)

    def gen_cell_img(self) -> Iterator[PilImage]:
        for obj in self.gen_video_objects_filtered():
            first_frame = obj.frames[0]
            yield self.get_frame_with_overlay(obj, first_frame)

    def gen_cell_pos(self) -> Iterator[tuple[int, int]]:
        cell_x, cell_y = 0, 0
        while True:
            yield cell_x, cell_y
            cell_x += self.cell_size.w
            if self.grid_size.w <= cell_x:  # Move to next row?
                cell_x, cell_y = 0, cell_y + self.cell_size.h

    def render_object_animations(self):
        for obj_idx, obj in enumerate(self.gen_video_objects_filtered()):
            image_gen = (
                self.get_frame_with_overlay(obj, frame)
                for frame_idx, frame in enumerate(obj.frames)
                if frame_idx < ANIM_MAX_FRAMES
            )
            filename_suffix = ANIM_SUFFIX_FMT.format(
                index=obj_idx,
                entity=obj.entity.description,
                confidence=int(obj.confidence * 100 + 0.5),
                frames=len(obj.frames),
            )
            self.upload_image(image_gen, filename_suffix)

    def get_frame_with_overlay(
        self, obj: vi.ObjectTrackingAnnotation, frame: vi.ObjectTrackingFrame
    ) -> PilImage:
        def get_video_frame() -> PilImage:
            pos_ms = frame.time_offset.total_seconds() * 1000
            self.video.set(cv.CAP_PROP_POS_MSEC, pos_ms)
            _, cv_frame = self.video.read()
            image = Image.fromarray(cv.cvtColor(cv_frame, cv.COLOR_BGR2RGB))
            image.thumbnail(self.cell_size)  # Makes it smaller if needed
            return image

        def add_caption(image: PilImage) -> PilImage:
            description = obj.entity.description
            confidence = obj.confidence
            frames = len(obj.frames)
            sep = "·"
            text = f"{description} {sep} {confidence:.0%} {sep} {frames} fr."
            padding_w, _ = self.font.getsize(sep)
            text_w, _ = self.font.getsize(text)
            w = text_w + 2 * padding_w
            h = self.font_height
            overlay = Image.new("RGBA", image.size, "#FFF0")
            draw = ImageDraw.Draw(overlay)
            draw.rectangle((0, 0, w, h), FONT_BG_COLOR)
            draw.text((padding_w, 0), text, BBOX_COLOR, self.font)
            return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

        def add_bounding_box(image: PilImage) -> PilImage:
            image_w, image_h = image.size
            bb = frame.normalized_bounding_box
            r = (
                int(image_w * bb.left + 0.5),
                int(image_h * bb.top + 0.5),
                int(image_w * bb.right + 1.5),
                int(image_h * bb.bottom + 1.5),
            )
            draw = ImageDraw.Draw(image)
            draw.rectangle(r, outline=BBOX_COLOR, width=BBOX_WIDTH_PX)
            return image

        return add_bounding_box(add_caption(get_video_frame()))

    def upload_image(self, frames: PilFrames, filename_suffix: str):
        mem_file = BytesIO()

        if isinstance(frames, PilImage):
            image_type = "jpeg"  # webp soon ;)
            first_frame = frames
            save_parameters = dict()
        else:
            image_type = "gif"  # webp if you can (faster and x15 smaller)
            first_frame = next(frames)
            save_parameters = dict(
                save_all=True,
                append_images=frames,
                duration=ANIM_FIXED_DURATION_MS,
                loop=0,  # Infinite loop
            )
        first_frame.save(mem_file, format=image_type, **save_parameters)

        image_bytes = mem_file.getvalue()
        self.storage.upload_image(image_bytes, image_type, filename_suffix)
