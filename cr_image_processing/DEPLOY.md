# 🎨 Image processing as a service 🐍 Deploying from scratch 🚀

With a Google Cloud account, you can set up the cloud architecture and deploy the app from scratch:

- directly from your browser ([Cloud Shell](https://console.cloud.google.com/?cloudshell=true)),
- using 1 command-line tool (`gcloud`),
- in less than 7 minutes.

## 🔧 Project setup

### Environment variables

```bash
MY_UNIQUE_ID="MY_UNIQUE_ID"  # e.g. you can use your GitHub username
PROJECT_NAME="Coloring Page Generator"
PROJECT_ID="cpg-$MY_UNIQUE_ID"

# Cloud Run region (see https://cloud.google.com/about/locations#region)
CLOUD_RUN_REGION="europe-west6"

# Source on GitHub
GIT_USER="PicardParis"
GIT_REPO="cherry-on-py"
GITHUB_SOURCE=https://github.com/$GIT_USER/$GIT_REPO.git
PROJECT_SOURCE=~/$GIT_REPO/cr_image_processing/demo
```

### Source code

```bash
# Get the source code
cd ~
git clone $GITHUB_SOURCE

# Make sure you point to the right location
ls $PROJECT_SOURCE

# You should get the following:
# main.py  Procfile  requirements.txt  static/
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
# Link the project with a billing account
BILLING_ACCOUNT=$(gcloud beta billing accounts list \
    --filter "displayName='My Billing Account'" \
    --format 'value(name)')

gcloud beta billing projects link $PROJECT_ID \
  --billing-account $BILLING_ACCOUNT
```

### Cloud APIs

```bash
# Enable the APIs
# - Artifact Registry will store your build artifacts.
# - Cloud Build will build your app.
# - Cloud Run will deploy and serve your app.
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com
```

### Cloud Run 

```bash
# Set the default platform to "managed"
# (Cloud Run can also be deployed to Kubernetes clusters)
gcloud config set run/platform managed

# This demo uses a single region: define the default region
# (To manage services in multiple regions, use the `--region` flag in `gcloud run` commands)
gcloud config set run/region $CLOUD_RUN_REGION
```

## 🚀 Deployment

Deploy your app from the source code with a single command:

```bash
SERVICE="coloring-page-generator"
CLOUD_RUN_MEMORY="2Gi"

gcloud run deploy $SERVICE \
  --source $PROJECT_SOURCE \
  --memory $CLOUD_RUN_MEMORY \
  --allow-unauthenticated \
  --quiet
```

> Notes:
> - For more details, see the `gcloud run deploy` [options](https://cloud.google.com/sdk/gcloud/reference/run/deploy)
> - Deploying from source requires an Artifact Registry repository to store the build artifacts. By using the `--quiet` flag, you skip prompt confirmations and a default repository named `cloud-run-source-deploy` will automatically be created.
> - The default memory allocated to a Cloud Run instance is 512 MiB. To handle higher resolution images, the service is configured with 2 GiB here. You can currently allocate up to 16 GiB of memory.

This gives the following output:

```text
…
Building using Buildpacks and deploying container to Cloud Run service [SERVICE] in project [PROJECT_ID] region [REGION]
OK Building and deploying new service... Done.
  OK Creating Container Repository...
  OK Uploading sources...
  OK Building Container... Logs are available at […].
  OK Creating Revision...
  OK Routing traffic...   
  OK Setting IAM Policy...
Done.
Service [SERVICE] revision [SERVICE-REVISION] has been deployed and is serving 100 percent of traffic.
Service URL: https://SERVICE-PROJECTHASH-REGIONID.a.run.app
```

Check the details of your service:

```bash
gcloud run services describe $SERVICE
```

> For more details, see the `gcloud run services` [options](https://cloud.google.com/sdk/gcloud/reference/run/services).

This lists the specific and default settings:

```text
✔ Service SERVICE in region REGION

URL:     https://SERVICE-PROJECTHASH-REGIONID.a.run.app
Ingress: all
Traffic:
  100% LATEST (currently SERVICE-REVISION)

Last updated…:
  Revision SERVICE-REVISION
  Image:           REGION-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/…
  Port:            8080
  Memory:          2Gi
  CPU:             1000m
  Service account: SERVICE_ACCOUNT@developer.gserviceaccount.com
  Concurrency:     80
  Max Instances:   100
  Timeout:         300s
```

> To get all available info, request it in JSON: `gcloud run services describe $SERVICE --format json`

You can also manage your Cloud Run services from the [GUI (Cloud Console)](https://console.cloud.google.com/run).

List of services:

![screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/a_cloud_run_services.png)

Service details:

![screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/c_cloud_run_details.png)

## 🎉 Production test

The web app is ready. Retrieve your app URL:

```bash
SERVICE_URL=$(gcloud run services describe $SERVICE --format "value(status.url)")
echo $SERVICE_URL
```

The service URL has the following format:

```text
https://SERVICE-PROJECTHASH-REGIONID.a.run.app
```

Send a GET request to your app:

```bash
curl $SERVICE_URL
```

This returns the static index page:

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <title>Coloring Page Generator</title>
    ...
</head>
<body>
    ...
</body>

</html>
```

Open the URL in your browser. Your image processing app is live!

![Demo animation](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/demo.gif)

## 🧹 Project deletion

```bash
# To clean up everything, you can delete the project
gcloud projects delete $PROJECT_ID
```

## ➕ One more thing

How big is the code?

```bash
first_line_after_licence=16

# Number of Python lines
find $PROJECT_SOURCE -name "*.py" -exec tail -n +$first_line_after_licence {} \; | grep -c "\S"
# 50

# Number of JavaScript lines
find $PROJECT_SOURCE -name "*.js" -exec tail -n +$first_line_after_licence {} \; | grep -c "\S"
# 130
```

- This image processing app counts less than 200 lines of code: less lines, less bugs!
- Deploying from scratch takes less than 7 minutes.
- 🔥🐍 **Mission accomplished!** 🐍🔥
