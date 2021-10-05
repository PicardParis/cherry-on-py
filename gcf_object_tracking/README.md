# 🎞️ Video object tracking as a service 🐍

> _This is not an official Google product. This is an article aiming at giving you ideas..._

## 👋 Hello!

In this article, following up on the previous one ("Video summary as a service"), you'll see the following:
- how to track objects present in a video,
- with an automated processing pipeline,
- in less than 300 lines of Python code.

Here is an example of an auto-generated object summary for the video [<animals.mp4>](https://storage.googleapis.com/cloud-samples-data/video/animals.mp4):

![Tracked object summary for animals.mp4](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/animals.mp4.summary_pct70_fr10.jpeg)

## 🛠️ Tools

A few tools will do:

- Storage space for videos and results
- A serverless solution to run the code
- A machine learning model to analyze videos
- A library to extract frames from videos
- A library to render the objects

## 🧱 Architecture

Here is a possible architecture using 3 Google Cloud services ([Cloud Storage](https://cloud.google.com/storage/docs), [Cloud Functions](https://cloud.google.com/functions/docs), and the [Video Intelligence API](https://cloud.google.com/video-intelligence/docs)):

![Architecture](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/architecture_1.png)

The processing pipeline follows these steps:

1. You upload a video
2. The upload event automatically triggers the tracking function
3. The function sends a request to the Video Intelligence API
4. The Video Intelligence API analyzes the video and uploads the results (annotations)
5. The upload event triggers the rendering function
6. The function downloads both annotation and video files
7. The function renders and uploads the objects
8. You know which objects are present in your video!

## 🐍 Python libraries

### Video Intelligence API
- To analyze videos
- <https://pypi.org/project/google-cloud-videointelligence>

### Cloud Storage
- To manage downloads and uploads
- <https://pypi.org/project/google-cloud-storage>

### OpenCV
- To extract video frames
- `OpenCV` offers a headless version (without GUI features, ideal for a service)
- <https://pypi.org/project/opencv-python-headless>

### Pillow
- To render and annotate object images
- `Pillow` is a very popular imaging library, both extensive and easy to use
- <https://pypi.org/project/Pillow>

## 🧠 Video analysis

### Video Intelligence API

The Video Intelligence API is a pre-trained machine learning model that can analyze videos. One of its multiple features is detecting and tracking objects. For the 1st Cloud Function, here is a possible core function calling `annotate_video()` with the `OBJECT_TRACKING` feature:

```python
from google.cloud import storage, videointelligence

def launch_object_tracking(video_uri: str, annot_bucket: str):
    """ Detect and track video objects (asynchronously)

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
```

### Cloud Function entry point

```python
import os

ANNOTATION_BUCKET = os.getenv("ANNOTATION_BUCKET", "")
assert ANNOTATION_BUCKET, "Undefined ANNOTATION_BUCKET environment variable"

def gcf_track_objects(data, context):
    """Cloud Function triggered by a new Cloud Storage object"""
    video_bucket = data["bucket"]
    path_to_video = data["name"]
    video_uri = f"gs://{video_bucket}/{path_to_video}"
    launch_object_tracking(video_uri, ANNOTATION_BUCKET)
```

> Notes:
> - This function will be called when a video is uploaded to the bucket defined as a trigger.
> - Using an environment variable makes the code more portable and lets you deploy the exact same code with different trigger and output buckets.


## 🎨 Object rendering

### Code structure

It's interesting to split the code into 2 main classes:

- `StorageHelper` for managing local files and cloud storage objects
- `VideoProcessor` for all graphical processings

Here is a possible core function for the 2nd Cloud Function:

```python
class VideoProcessor:
    @staticmethod
    def render_objects(annot_uri: str, output_bucket: str):
        """Render objects from video annotations"""
        with StorageHelper(annot_uri, output_bucket) as storage:
            with VideoProcessor(storage) as video_proc:
                print(f"Objects to render: {video_proc.object_count}")
                video_proc.render_object_summary()
```

### Cloud Function entry point

```python
def gcf_render_objects(data, context):
    """Cloud Function triggered by a new Cloud Storage object"""
    annotation_bucket = data["bucket"]
    path_to_annotation = data["name"]
    annot_uri = f"gs://{annotation_bucket}/{path_to_annotation}"
    VideoProcessor.render_objects(annot_uri, OBJECT_BUCKET)
```

> Note: This function will be called when an annotation file is uploaded to the bucket defined as a trigger.

### Frame rendering

`OpenCV` and `Pillow` easily let you extract video frames and compose over them:

```python
class VideoProcessor:
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
            ...

        def add_bounding_box(image: PilImage) -> PilImage:
            ...
            draw.rectangle(r, outline=BBOX_COLOR, width=BBOX_WIDTH_PX)
            return image

        return add_bounding_box(add_caption(get_video_frame()))
```

> Note: It would probably be possible to only use `OpenCV` but I found it more productive developing with `Pillow` (code is more readable and intuitive).

## 🔎 Results

Here are the main objects found in the video [<JaneGoodall.mp4>](https://storage.googleapis.com/cloud-samples-data/video/JaneGoodall.mp4):

![Tracked object summary for JaneGoodall.mp4](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.summary_pct70_fr10.jpeg)

> Notes:
> - The machine learning model has correctly identified different wildlife species: those are "true positives". It has also incorrectly identified our planet as "packaged goods": this is a "false positive". Machine learning models keep learning by being trained with new samples so, with time, their precision keeps increasing (resulting in less false positives).
> - The current code filters out objects detected with a confidence below 70% or with less than 10 frames. Lower the thresholds to get more results.

## 🍒 Cherry on Py 🐍

Now, the icing on the cake (or the "cherry on the pie" as we say in French), you can enrich the architecture to add new possibilities:
- Trigger the processing for videos from any bucket (including external public buckets)
- Generate individual object animations (in parallel to object summaries)

### Architecture (v2)

![Architecture (v2)](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/architecture_2.png)

- A - Video object tracking can also be triggered manually with an HTTP GET request
- B - The same rendering code is deployed in 2 sibling functions, differentiated with an environment variable
- C - Object summaries and animations are generated in parallel

### Cloud Function HTTP entry point

```python
def gcf_track_objects_http(request):
    """Cloud Function triggered by an HTTP GET request"""
    if request.method != "GET":
        return ("Please use a GET request", 403)
    if not request.args or "video_uri" not in request.args:
        return ('Please specify a "video_uri" parameter', 400)
    video_uri = request.args["video_uri"]
    launch_object_tracking(video_uri, ANNOTATION_BUCKET)
    return f"Launched object tracking for <{video_uri}>"
```

> Note: This is the same code as `gcf_track_objects()` with the video URI parameter specified by the caller through a GET request.

## 🎉 Results

Here are some auto-generated trackings for the video [<animals.mp4>](https://storage.googleapis.com/cloud-samples-data/video/animals.mp4):

- The left elephant (a big object ;) is detected:
  ![Elephant on the left](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/animals.mp4.022_elephant_pct91_fr17.gif)
- The right elephant is perfectly isolated too:
  ![Elephant on the right](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/animals.mp4.021_elephant_pct93_fr17.gif)
- The veterinarian is correctly identified:
  ![Person on the left](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/animals.mp4.033_person_pct96_fr11.gif)
- The animal he's feeding too:
  ![Animal on the right](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/animals.mp4.034_animal_pct79_fr11.gif)

Moving objects or static objects in moving shots are tracked too, as in [<beyond-the-map-rio.mp4>](https://storage.googleapis.com/ga-demo-videos/beyond-the-map-rio.mp4):

- A building in a moving shot:
  ![Shot with buildings 1](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/beyond-the-map-rio.mp4.000_building_pct77_fr10.gif)
- Neighbor buildings are tracked too:
  ![Shot with buildings 2](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/beyond-the-map-rio.mp4.001_building_pct83_fr11.gif)
- Persons in a moving shot:
  ![Moving persons](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/beyond-the-map-rio.mp4.004_person_pct100_fr11.gif)
- A surfer crossing the shot:
  ![Surfer](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/beyond-the-map-rio.mp4.010_person_pct97_fr14.gif)

Here are some others for the video [<JaneGoodall.mp4>](https://storage.googleapis.com/cloud-samples-data/video/JaneGoodall.mp4):

- A butterfly (easy?):
  ![Butterfly](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.005_butterfly_pct91_fr21.gif)
- An insect, in larval stage, climbing a moving twig:
  ![Caterpillar on moving twig](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.004_insect_pct71_fr23.gif)
- An ape in a tree far away (hard?):
  ![Ape catching bugs in tree far away](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.002_animal_pct81_fr24.gif)
- A monkey jumping from the top of a tree (harder?):
  ![Monkey jumping from tree top](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.008_animal_pct75_fr12.gif)
- Now, a trap! If we can be fooled, current machine learning state of the art can too:
  ![A flower or maybe not a flower](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/JaneGoodall.mp4.007_flower_pct85_fr16.gif)

## 🚀 Source code and deployment

- The Python source code is less than 300 lines.
- You can deploy this architecture in less than 8 minutes.
- See ["Deploying from scratch"](./DEPLOY.md).

## 🖖 See you

Do you want more, do you have questions? I'd love to read [your feedback](https://bit.ly/feedback-video-object-tracking). You can also [follow me on Twitter](https://twitter.com/PicardParis).
