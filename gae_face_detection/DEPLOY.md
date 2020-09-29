# 🕵️ Detecting faces as a service 🐍 Deploying from scratch 🚀

With a Google Cloud account, set up the cloud architecture and deploy the app from scratch:

- directly from your browser ([Cloud Shell](https://console.cloud.google.com/?cloudshell=true)),
- using 1 command-line tool (`gcloud`),
- in less than 4 minutes.

## 🔧 Project setup

### Environment variables

```bash
# Project: Face DetectioN (FDN)
# Note: You can use your GitHub username as a unique suffix
PROJECT_NAME="Face detection"
PROJECT_ID="fdn-REPLACE_WITH_UNIQUE_SUFFIX"

# App Engine (GAE) region
# See https://cloud.google.com/about/locations#region
GAE_REGION="europe-west2"

# Source on GitHub
GIT_REPO="cherry-on-py"
GITHUB_SOURCE=https://github.com/PicardParis/$GIT_REPO.git
PROJECT_SRC=~/$GIT_REPO/gae_face_detection/demo
```

### Source code

```bash
# Retrieve the source code
cd ~
git clone $GITHUB_SOURCE
```

### Project

```bash
# Create a new project
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

### Cloud APIs

```bash
# Enable the Vision API
gcloud services enable vision.googleapis.com
```

### App Engine

```bash
# Create an App Engine app within the current cloud project
gcloud app create --region $GAE_REGION
```

## 🚀 Deployment

Deploy your first and successive versions with a single command:

```bash
gcloud app deploy $PROJECT_SRC/app.yaml --quiet
```

This gives the following output:

```text
…
Beginning deployment of service [default]...
╔════════════════════════════════════════════════════════════╗
╠═ Uploading 18 files to Google Cloud Storage               ═╣
╚════════════════════════════════════════════════════════════╝
File upload done.
Updating service [default]...done.
Setting traffic split for service [default]...done.
Deployed service [default] to [https://PROJECT_ID.REGION_ID.r.appspot.com]
```

You can also handle cloud resources in the GUI ([Cloud Console](https://console.cloud.google.com/appengine/versions)):

![App Engine screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/live/gae_face_detection/pics/app_engine.png)

## 🎉 Production test

The web app is ready. Open the `appspot.com` URL:

![Demo screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/live/gae_face_detection/pics/face_detection_demo.png)

Check the latest logs:

```bash
gcloud app logs read --limit 20
```

The first request is handled, which starts the web app instance, and the successive web requests are served immediately:

```text
DATE TIME default[VERSION]  "GET / HTTP/1.1" 200
DATE TIME default[VERSION]  … Starting gunicorn 20.0.4
DATE TIME default[VERSION]  … Listening at: http://0.0.0.0:8081 (10)
DATE TIME default[VERSION]  … Using worker: threads
DATE TIME default[VERSION]  … Booting worker with pid: 21
DATE TIME default[VERSION]  … Booting worker with pid: 23
DATE TIME default[VERSION]  … Booting worker with pid: 25
DATE TIME default[VERSION]  … Booting worker with pid: 26
DATE TIME default[VERSION]  … Booting worker with pid: 27
DATE TIME default[VERSION]  … Booting worker with pid: 28
DATE TIME default[VERSION]  … Booting worker with pid: 29
DATE TIME default[VERSION]  … Booting worker with pid: 30
DATE TIME default[VERSION]  "GET /static/styles.css HTTP/1.1" 200
DATE TIME default[VERSION]  "GET /static/scripts.js HTTP/1.1" 200
DATE TIME default[VERSION]  "GET /static/favicon.ico HTTP/1.1" 200
DATE TIME default[VERSION]  "POST /analyze-image HTTP/1.1" 200
DATE TIME default[VERSION]  "POST /process-image HTTP/1.1" 200
```

> You can also browse the logs in the GUI ([Cloud Console](https://console.cloud.google.com/logs/viewer?resource=gae_app)).

## 🧹 Project deletion

```bash
gcloud projects delete $PROJECT_ID
```

## ➕ One more thing

Several options have been progressively added to the backend. Has our code base grown significantly?

```bash
first_line_after_licence=16
find $PROJECT_SRC -name "*.py" -exec tail -n +$first_line_after_licence {} \; | grep -v "^$" | wc -l

279
```

- Image analysis and processing, with different options, run in less than 300 lines of readable Python.
- Less lines, less bugs!
- 🔥🐍 **Mission accomplished!** 🐍🔥
