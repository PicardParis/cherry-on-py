# 🎞️ Video object tracking as a service 🐍 Deploying from scratch 🚀

With a Google Cloud account, you can set up the whole architecture from scratch:
- directly from your browser ([Cloud Shell](https://console.cloud.google.com/?cloudshell=true)),
- using 2 command-line tools (`gcloud` and `gsutil`),
- in less than 8 minutes.

## 🔧 Project setup

### Environment variables

```bash
# Project
PROJECT_NAME="Object tracking"
PROJECT_ID="object-tracking-REPLACE_WITH_UNIQUE_SUFFIX"

# Cloud Storage region
# See https://cloud.google.com/storage/docs/locations
GCS_REGION="europe-west1"

# Cloud Functions region
# See https://cloud.google.com/functions/docs/locations
GCF_REGION="europe-west1"

# Cloud Storage buckets
VIDEO_BUCKET="b1-videos_${PROJECT_ID}"
ANNOTATION_BUCKET="b2-annotations_${PROJECT_ID}"
OBJECT_BUCKET="b3-objects_${PROJECT_ID}"

# Source
GIT_REPO="cherry-on-py"
PROJECT_SRC=~/$PROJECT_ID/$GIT_REPO/gcf_object_tracking
```

> Note: You can use your GitHub username as a unique suffix.

### Project

```bash
# Create new project
gcloud projects create $PROJECT_ID \
  --name "$PROJECT_NAME" \
  --set-as-default
```

### Billing account

```bash
# Link project with billing account
BILLING_ACCOUNT=$(gcloud beta billing accounts list \
    --filter "displayName='My Billing Account'" \
    --format 'value(name)')

gcloud beta billing projects link $PROJECT_ID \
  --billing-account $BILLING_ACCOUNT
```

### Cloud Storage buckets

```bash
# Create buckets with uniform bucket-level access
gsutil mb -b on -c regional -l $GCS_REGION gs://$VIDEO_BUCKET
gsutil mb -b on -c regional -l $GCS_REGION gs://$ANNOTATION_BUCKET
gsutil mb -b on -c regional -l $GCS_REGION gs://$OBJECT_BUCKET
```

Here is what you get in the [Cloud Console](https://console.cloud.google.com/storage/browser):

![Cloud Storage buckets](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/buckets.png)

### Cloud APIs

```bash
# Enable the Video Intelligence and Cloud Functions APIs
gcloud services enable \
  videointelligence.googleapis.com \
  cloudfunctions.googleapis.com
```

### Source code

```bash
# Retrieve the source code
mkdir ~/$PROJECT_ID
cd ~/$PROJECT_ID
git clone https://github.com/PicardParis/$GIT_REPO.git
```

## 🧠 Video analysis

Deploy the 1st function:

```bash
GCF_NAME="gcf1_track_objects"
GCF_SOURCE="$PROJECT_SRC/gcf1_track_objects"
GCF_ENTRY_POINT="gcf_track_objects"
GCF_TRIGGER_BUCKET="$VIDEO_BUCKET"
GCF_ENV_VARS="ANNOTATION_BUCKET=$ANNOTATION_BUCKET"
GCF_MEMORY="128MB"

gcloud functions deploy $GCF_NAME \
  --runtime python37 \
  --source $GCF_SOURCE \
  --entry-point $GCF_ENTRY_POINT \
  --update-env-vars $GCF_ENV_VARS \
  --trigger-bucket $GCF_TRIGGER_BUCKET \
  --region $GCF_REGION \
  --memory $GCF_MEMORY \
  --quiet
```

Deploy its HTTP counterpart:

```bash
GCF_NAME="gcf1_track_objects_http"
GCF_SOURCE="$PROJECT_SRC/gcf1_track_objects"
GCF_ENTRY_POINT="gcf_track_objects_http"
GCF_TRIGGER_BUCKET="$VIDEO_BUCKET"
GCF_ENV_VARS="ANNOTATION_BUCKET=$ANNOTATION_BUCKET"
GCF_MEMORY="128MB"

gcloud functions deploy $GCF_NAME \
  --runtime python37 \
  --source $GCF_SOURCE \
  --entry-point $GCF_ENTRY_POINT \
  --update-env-vars $GCF_ENV_VARS \
  --trigger-http \
  --region $GCF_REGION \
  --memory $GCF_MEMORY \
  --quiet
```

## 🎨 Object rendering

Deploy the 2nd function:

```bash
GCF_NAME="gcf2_render_objects"
GCF_SOURCE="$PROJECT_SRC/gcf2_render_objects"
GCF_ENTRY_POINT="gcf_render_objects"
GCF_TRIGGER_BUCKET="$ANNOTATION_BUCKET"
GCF_ENV_VARS1="OBJECT_BUCKET=$OBJECT_BUCKET"
GCF_ENV_VARS2="ANIMATED=0"
GCF_TIMEOUT="540s"
GCF_MEMORY="512MB"

gcloud functions deploy $GCF_NAME \
  --runtime python37 \
  --source $GCF_SOURCE \
  --entry-point $GCF_ENTRY_POINT \
  --update-env-vars $GCF_ENV_VARS1 \
  --update-env-vars $GCF_ENV_VARS2 \
  --trigger-bucket $GCF_TRIGGER_BUCKET \
  --region $GCF_REGION \
  --timeout $GCF_TIMEOUT \
  --memory $GCF_MEMORY \
  --quiet
```

Deploy its animated counterpart:

```bash
GCF_NAME="gcf2_render_objects_animated"
GCF_SOURCE="$PROJECT_SRC/gcf2_render_objects"
GCF_ENTRY_POINT="gcf_render_objects"
GCF_TRIGGER_BUCKET="$ANNOTATION_BUCKET"
GCF_ENV_VARS1="OBJECT_BUCKET=$OBJECT_BUCKET"
GCF_ENV_VARS2="ANIMATED=1"
GCF_TIMEOUT="540s"
GCF_MEMORY="1024MB"

gcloud functions deploy $GCF_NAME \
  --runtime python37 \
  --source $GCF_SOURCE \
  --entry-point $GCF_ENTRY_POINT \
  --update-env-vars $GCF_ENV_VARS1 \
  --update-env-vars $GCF_ENV_VARS2 \
  --trigger-bucket $GCF_TRIGGER_BUCKET \
  --region $GCF_REGION \
  --timeout $GCF_TIMEOUT \
  --memory $GCF_MEMORY \
  --quiet
```

Here is what you get in the [Cloud Console](https://console.cloud.google.com/functions/list):

![Cloud Functions](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/functions.png)

> Notes:
> - The object rendering functions use the maximum possible timeout of 540 seconds and thus must complete in 9 minutes.
> - For a video with hundreds of objects, generating so many animations may need more than 9 minutes. You can adapt the code to filter out more results, reduce the number of animation frames, reduce the resolution, or increase the allocated memory (memory size and CPU speed go together). You can also use [Cloud Run](https://cloud.google.com/run) (serverless containers) which supports longer timeouts.

## 🎉 Production test

To trigger the pipeline, upload videos to the 1st bucket or send a GET request to the HTTP endpoint:

```bash
GCF_NAME="gcf1_track_objects_http"
VIDEO_URI="gs://cloud-samples-data/video/JaneGoodall.mp4"
GCF_URL="https://$GCF_REGION-$PROJECT_ID.cloudfunctions.net/$GCF_NAME?video_uri=$VIDEO_URI"

curl $GCF_URL -H "Authorization: bearer $(gcloud auth print-identity-token)"
```

You'll see the HTTP response:

```text
Launching object tracking for <gs://cloud-samples-data/video/JaneGoodall.mp4>...
```

Check the logs:

```bash
gcloud functions logs read --region $GCF_REGION --limit 50
```

You'll see the 2 rendering functions working in parallel:

```text
LEVEL  NAME                          LOG
D      gcf1_track_objects_http       Function execution started
I      gcf1_track_objects_http       Launching object tracking for for <gs://.../JaneGoodall.mp4>...
D      gcf1_track_objects_http       Function execution took 819 ms, finished with status code: 200
D      gcf2_render_objects           Function execution started
I      gcf2_render_objects           Downloading -> /tmp/b3-objects.../JaneGoodall.mp4
D      gcf2_render_objects_animated  Function execution started
I      gcf2_render_objects           Objects to render: 9
I      gcf2_render_objects_animated  Downloading -> /tmp/b3-objects.../JaneGoodall.mp4
I      gcf2_render_objects_animated  Objects to render: 9
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.000_packaged goods_pct75_fr14.gif
I      gcf2_render_objects           Uploading -> .../JaneGoodall.mp4.summary_pct70_fr10.jpeg
D      gcf2_render_objects           Function execution took 21209 ms, finished with status: 'ok'
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.001_butterfly_pct86_fr12.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.002_animal_pct81_fr24.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.003_insect_pct86_fr25.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.004_insect_pct71_fr23.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.005_butterfly_pct91_fr21.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.006_animal_pct73_fr29.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.007_flower_pct85_fr16.gif
I      gcf2_render_objects_animated  Uploading -> .../JaneGoodall.mp4.008_animal_pct75_fr12.gif
D      gcf2_render_objects_animated  Function execution took 81792 ms, finished with status: 'ok'
```

And you can preview the results directly from the [Storage Browser](https://console.cloud.google.com/storage/browser/):

![Production test](https://github.com/PicardParis/cherry-on-py-pics/raw/main/gcf_object_tracking/pics/production-test.png)

## 🧹 Project deletion

```text
gcloud projects delete $PROJECT_ID
```

## ➕ One more thing

```bash
first_line_after_licence=16
find $PROJECT_SRC -name '*.py' -exec tail -n +$first_line_after_licence {} \; | grep -v "^$" | wc -l
299
```

- You did everything in less than 300 lines of Python.
- Less lines, less bugs!
- 🔥🐍 **Mission accomplished!** 🐍🔥
