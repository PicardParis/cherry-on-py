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
from io import BytesIO
from math import atan2, ceil, cos, fabs, sin, sqrt
from typing import NamedTuple

from google.cloud import vision_v1 as vision
from PIL import Image, ImageDraw, ImageOps

PilImage = Image.Image
Point = NamedTuple("Point", [("x", int), ("y", int)])
Annotations = vision.AnnotateImageResponse
LandmarkType = vision.FaceAnnotation.Landmark.Type

# Reference moustache by Mushon Zer-Aviv, Yanka (see CREDITS.md)
REF_STACHE = "www/res/stache.png"
REF_STACHE_NOSE_BOTTOM = Point(125, 8)
REF_EYE_DISTANCE = 121  # Distance between eyes for which the moustache is 1:1

# Reference landmarks to position the moustache
MAX_DETECTED_FACES = 50
NOSE_B = LandmarkType.NOSE_BOTTOM_CENTER
MOUTH_L = LandmarkType.MOUTH_LEFT
MOUTH_R = LandmarkType.MOUTH_RIGHT
EYE_L = LandmarkType.LEFT_EYE
EYE_R = LandmarkType.RIGHT_EYE

# Rendering
ANNOTATION_COLOR = "#00FF00"
ANNOTATION_LANDMARK_DIM_PERMIL = 8
ANNOTATION_LANDMARK_DIM_MIN = 4
ANONYMIZATION_PIXELS = 13
ANIM_ANGLES = (0.0, -0.2, +0.2, -0.1, +0.1, -0.05, +0.05)
ANIM_SCALES = (1.0, 1.2, 0.8, 1.1, 0.9, 1.05, 0.95)
assert len(ANIM_SCALES) == len(ANIM_ANGLES)
ANIM_FRAME_NB = len(ANIM_ANGLES)
ANIM_FRAME0_DUR_MS = 1200
ANIM_FRAME1_DUR_MS = 50
CROP_MARGIN_PERCENT = 10


def detect_faces(image_bytes: bytes) -> Annotations:
    client = vision.ImageAnnotatorClient()
    api_image = vision.Image(content=image_bytes)
    return client.face_detection(api_image, max_results=MAX_DETECTED_FACES)


class ResultOptions(NamedTuple):
    animated: bool = False
    crop_faces: bool = False
    crop_image: bool = False
    # "webp", "png", or "gif" (still or animated)
    image_format: str = "png"
    # Still image options
    landmarks: bool = False
    anonymize: bool = False
    stache: bool = True
    # Animated image options
    oscillating: bool = True
    bouncing: bool = False


def draw_face_landmarks(image: PilImage, annotations: Annotations):
    r_half = min(image.size) * ANNOTATION_LANDMARK_DIM_PERMIL // 1000
    r_half = max(r_half, ANNOTATION_LANDMARK_DIM_MIN) // 2
    border = max(r_half // 2, 1)

    draw = ImageDraw.Draw(image)
    for face in annotations.face_annotations:
        v = face.bounding_poly.vertices
        r = (v[0].x, v[0].y, v[2].x + 1, v[2].y + 1)
        draw.rectangle(r, outline=ANNOTATION_COLOR, width=border)

        for landmark in face.landmarks:
            x = int(landmark.position.x + 0.5)
            y = int(landmark.position.y + 0.5)
            r = (x - r_half, y - r_half, x + r_half + 1, y + r_half + 1)
            draw.rectangle(r, outline=ANNOTATION_COLOR, width=border)


def anonymize_faces(image: PilImage, annotations: Annotations):
    for face in annotations.face_annotations:
        v = face.bounding_poly.vertices
        face = image.crop((v[0].x, v[0].y, v[2].x + 1, v[2].y + 1))

        face1_w, face1_h = face.size
        pixel_dim = max(face1_w, face1_h) // ANONYMIZATION_PIXELS
        face2_w, face2_h = face1_w // pixel_dim, face1_h // pixel_dim
        face = face.resize((face2_w, face2_h), Image.NEAREST)
        face = face.resize((face1_w, face1_h), Image.NEAREST)

        image.paste(face, (v[0].x, v[0].y))


def draw_stache_on_face(
    image: PilImage, stache: PilImage, landmarks, angle=0.0, scale=1.0
):
    eye_distance, mouth_angle, nose_point = get_face_geometry(landmarks)
    stache_angle = mouth_angle + angle
    zoom = scale * eye_distance / REF_EYE_DISTANCE
    point_to_center = REF_STACHE_NOSE_BOTTOM
    stache = transform_image(stache, stache_angle, zoom, point_to_center)
    x = int(nose_point.x - stache.width / 2 + 0.5)
    y = int(nose_point.y - stache.height / 2 + 0.5)
    image.paste(stache, (x, y), stache)


def get_face_geometry(landmarks) -> tuple[float, float, Point]:
    """Returns the following 3 values:
    - The distance between the eyes (pix)
    - The mouth angle of elevation (rad)
    - The position of the bottom of the nose (x, y)
    """
    landmark_types = [EYE_L, EYE_R, MOUTH_L, MOUTH_R, NOSE_B]
    points = {}
    for landmark in landmarks:
        landmark_type = landmark.type_
        if landmark_type in landmark_types:
            position = landmark.position
            points[landmark_type] = Point(position.x, position.y)

    (x1, y1), (x2, y2) = points[EYE_L], points[EYE_R]
    eye_distance = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    (x1, y1), (x2, y2) = points[MOUTH_L], points[MOUTH_R]
    mouth_angle = atan2(y2 - y1, x2 - x1)

    return eye_distance, mouth_angle, points[NOSE_B]


def transform_image(
    image: PilImage, angle: float, zoom: float, center: Point
) -> PilImage:
    """Returns a copy of image rotated/scaled around center."""
    cos_a, sin_a = cos(angle), sin(angle)
    source_w, source_h = image.size
    scaled_w, scaled_h = source_w * zoom, source_h * zoom
    target_w = ceil(fabs(cos_a * scaled_w) + fabs(sin_a * scaled_h))
    target_h = ceil(fabs(sin_a * scaled_w) + fabs(cos_a * scaled_h))

    a, b = +cos_a / zoom, +sin_a / zoom
    d, e = -b, +a
    cx, cy = center
    tx, ty = target_w / 2, target_h / 2
    c = cx - tx * a - ty * b
    f = cy - tx * d - ty * e
    coeffs = (a, b, c, d, e, f)

    return image.transform((target_w, target_h), Image.AFFINE, coeffs, Image.BILINEAR)


def crop_faces(image: PilImage, annotations: Annotations, gif255: bool) -> PilImage:
    mask = Image.new("L", image.size, 0x00)
    draw = ImageDraw.Draw(mask)
    for face in annotations.face_annotations:
        draw.ellipse(face_crop_box(face), fill=0xFF)
    if gif255:
        image = image.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        image.paste(0xFF, mask=ImageOps.invert(mask))
    else:
        image.putalpha(mask)
    return image


def crop_image(image: PilImage, annotations: Annotations) -> PilImage:
    min_x, min_y, max_x, max_y = image.width, image.height, 0, 0
    for face in annotations.face_annotations:
        x1, y1, x2, y2 = face_crop_box(face)
        min_x, min_y = min(min_x, x1), min(min_y, y1)
        max_x, max_y = max(max_x, x2), max(max_y, y2)
    min_x, min_y = max(min_x, 0), max(min_y, 0)
    max_x, max_y = min(max_x, image.width), min(max_y, image.height)
    return image.crop((min_x, min_y, max_x, max_y))


def face_crop_box(face_annotation) -> tuple[int, int, int, int]:
    v = face_annotation.bounding_poly.vertices
    x1, y1, x2, y2 = v[0].x, v[0].y, v[2].x + 1, v[2].y + 1
    w, h = x2 - x1, y2 - y1
    hx, hy = x1 + w / 2, y1 + h / 2
    m = max(w, h) * (100 + CROP_MARGIN_PERCENT) / 100 / 2
    return int(hx - m + 0.5), int(hy - m + 0.5), int(hx + m + 1.5), int(hy + m + 1.5)


def render_result(
    input: PilImage, annotations: Annotations, options: ResultOptions
) -> BytesIO:
    """Renders the still|animated image, returns its bytes and format."""

    def draw_frame(image: PilImage, angle=0.0, scale=1.0) -> PilImage:
        if not annotations.face_annotations:
            return image
        if options.animated or options.stache:
            for face in annotations.face_annotations:
                draw_stache_on_face(image, stache, face.landmarks, angle, scale)
        if not options.animated:
            if options.anonymize:
                anonymize_faces(image, annotations)
            if options.landmarks:
                draw_face_landmarks(image, annotations)
        if options.crop_faces:
            image = crop_faces(image, annotations, transparent_gif)
        if options.crop_image:
            image = crop_image(image, annotations)
        return image

    has_faces = 1 <= len(annotations.face_annotations)
    transparent_gif = options.image_format == "gif" and options.crop_faces and has_faces
    stache = Image.open(REF_STACHE)
    if options.animated and has_faces:
        angles = ANIM_ANGLES if options.oscillating else [0.0] * ANIM_FRAME_NB
        scales = ANIM_SCALES if options.bouncing else [1.0] * ANIM_FRAME_NB
        # Frame generator: images will be generated when needed
        frames = (draw_frame(input.copy(), *a_s) for a_s in zip(angles, scales))
        durations = [ANIM_FRAME0_DUR_MS] + [ANIM_FRAME1_DUR_MS] * (ANIM_FRAME_NB - 1)
        result_image = next(frames)
        params = dict(save_all=True, append_images=frames, duration=durations, loop=0)
    else:
        result_image = draw_frame(input)
        params = dict()
    if options.image_format == "webp" and options.landmarks and not options.animated:
        params.update(dict(lossless=True))
    elif transparent_gif:
        params.update(dict(transparency=0xFF))

    result_bytes = BytesIO()
    result_image.save(result_bytes, format=options.image_format, **params)
    result_bytes.seek(0)

    return result_bytes
