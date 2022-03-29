# 🎨 Image processing as a service 🐍

![Coloring page generated from Hokusai's painting "The Great Wave off Kanagawa"](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/preview.gif)

> _This is not an official Google product. This is an article aiming at giving you ideas…_

## 👋 Hello

Have you ever written a script to transform an image? Did you share the script with others or did you run it on multiple computers? How many times did you need to update the script or the setup instructions? Did you end up making it a service or an online app? If your script is useful, you’ll likely want to make it available to others. Deploying processing services is a recurring need – one that comes with its own set of challenges. Serverless technologies let you solve these challenges easily and efficiently.

In this post, you’ll see how to…

- Create an image processing service that generates coloring pages
- Make it available online using minimal resources

…and do it all in less than 200 lines of Python and JavaScript!

## 🛠️ Tools

To build and deploy a coloring page generator, you’ll need a few tools:

- A library to process images
- A web application framework
- A web server
- A serverless solution to make the demo available 24/7

## 🧱 Architecture

Here is one possible architecture for a coloring page generator using Cloud Run:

![Architecture serving a web app with Cloud Run](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/1_architecture.png)

And here is the workflow:

- 1 - The user opens the web app: the browser requests the main page.
- 2 - Cloud Run serves the app HTML code.
- 3 - The browser requests the additional needed resources.
- 4 - Cloud Run serves the CSS, JavaScript, and other resources.
- A - The user selects an image and the frontend sends the image to the `/api/coloring-page` endpoint.
- B - The backend processes the input image and returns an output image, which the user can then visualize, download, or print via the browser.


## 🐍 Software stack

Of course, there are many different software stacks that you could use to implement such an architecture.

Here is a good one based on Python:

![schema](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/2_software_stack.png)

It includes:

- [Gunicorn](https://pypi.org/project/gunicorn): A production-grade WSGI HTTP server
- [Flask](https://pypi.org/project/Flask): A popular web app framework
- [scikit-image](https://pypi.org/project/scikit-image): An extensive image processing library

Define these app dependencies in a file named `requirements.txt`:

```txt
# https://pypi.org/project/gunicorn
gunicorn==20.1.0

# https://pypi.org/project/flask
Flask==2.1.1

# https://pypi.org/project/scikit-image
# scikit-image dependencies include NumPy and Pillow
scikit-image==0.19.2
```

## 🎨 Image processing

How do you remove colors from an image? One way is by detecting the object edges and removing everything but the edges in the result image. This can be done with a [Sobel](https://wikipedia.org/wiki/Sobel_operator) filter, a convolution filter that detects the regions in which the image intensity changes the most.

Create a Python file named `main.py`, define an image processing function, and within it use the Sobel filter and other functions from scikit-image:

```py
import numpy as np
import skimage
from PIL import Image
from PIL.Image import Image as PilImage


def generate_coloring_page(input: PilImage) -> PilImage:
    # Convert to grayscale if needed
    if input.mode != "L":
        input = input.convert("L")
    np_image = np.asarray(input)

    # Detect the edges
    np_image = skimage.filters.sobel(np_image)
    # Convert to 8 bpp
    np_image = skimage.util.img_as_ubyte(np_image)
    # Invert to get dark edges on a light background
    np_image = 255 - np_image
    # Improve the contrast
    np_image = skimage.exposure.rescale_intensity(np_image)

    return Image.fromarray(np_image)
```

> Note: The NumPy and Pillow libraries are automatically installed as dependencies of scikit-image.

As an example, here is how the Cloud Run logo is processed at each step:

![Colored input transformed into edge-detected grayscale output](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/3_edge_detection.png)

## ✨ Web app

### Backend

To expose both endpoints (`GET /` and `POST /api/coloring-page`), add Flask routes in `main.py`:

```py
import io

import flask
from PIL import Image

app = flask.Flask(__name__, static_url_path="")


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/coloring-page")
def coloring_page():
    file = flask.request.files.get("input-image")
    if file is None:
        return "Missing input-image parameter", 400

    input_image = Image.open(file.stream)
    output_image = generate_coloring_page(input_image)

    image_io = io.BytesIO()
    output_format = "png"
    output_image.save(image_io, format=output_format)
    image_io.seek(0)

    return flask.send_file(image_io, mimetype=f"image/{output_format}")
```

### Frontend

On the browser side, write a JavaScript function that calls the `/api/coloring-page` endpoint and receives the processed image:

```js
async function fetchColoringPage(inputFile) {
    const formData = new FormData()
    formData.append('input-image', inputFile)

    const url = '/api/coloring-page'
    const init = { method: 'POST', body: formData }
    try {
        const response = await fetch(url, init)
        return response.ok ? response.blob() : null
    } catch (error) {
        console.error(error)
        return null
    }
}
```

The base of your app is there. Now you just need to add a mix of HTML + CSS + JS to complete the desired user experience.

### Local development

To develop and test the app on your computer, once your environment is set up, make sure you have the needed dependencies:

```sh
pip install --upgrade -r requirements.txt
```

Add the following block to `main.py`. It will only execute when you run your app manually:

```py
import os

# ...

if __name__ == "__main__":
    os.environ["FLASK_ENV"] = "development"
    app.run(host="localhost", port=8080, debug=True)
```

Run your app:

```sh
python main.py
```

Flask starts a local web server:

```txt
 * Serving Flask app 'main' (lazy loading)
 * Environment: development
 * Debug mode: on
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 718-408-327
 * Running on http://localhost:8080/ (Press CTRL+C to quit)
```

> Note: In this mode, you’re using a development web server (one that is not suited for production). You’ll next set up the deployment to serve your app with Gunicorn, a production-grade server.

You're all set. Open `localhost:8080` in your browser, test, refine, and iterate.

## 🚀 Deployment

Once your app is ready for prime time, you can define how it will be served with this single line in a file named `Procfile`:

```sh
web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
```

At this stage, here are the files found in a typical project:

```txt
.
├── main.py
├── Procfile
├── requirements.txt
└── static
    ├── favicon.ico
    ├── index.html
    ├── scripts.js
    └── styles.css
```

That's it, you can now deploy your app from the source folder:

```sh
SERVICE="coloring-page-generator"
SOURCE="."

gcloud run deploy $SERVICE --source $SOURCE --allow-unauthenticated
```

## ⚙️ Under the hood

The command line output details all the different steps:

```txt
This command is equivalent to running `gcloud builds submit --pack image=[IMAGE] SOURCE` and `gcloud run deploy SERVICE --image [IMAGE]`

Building using Buildpacks and deploying container to Cloud Run service [SERVICE] in project [PROJECT_ID] region [REGION]
OK Building and deploying... Done.
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

Cloud Build is indirectly called to containerize your app. One of its core components is Google Cloud [Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), which automatically builds a production-ready container image from your source code. Here are the main steps:

- Cloud Build fetches the source code.
- Buildpacks autodetects the app language (Python, in this case) and uses the corresponding secure base image.
- Buildpacks installs the app dependencies (defined in `requirements.txt` for Python).
- Buildpacks configures the service entrypoint (defined in `Procfile` for Python).
- Cloud Build pushes the container image to [Artifact Registry](https://cloud.google.com/artifact-registry).
- Cloud Run creates a new revision of the service based on this container image.
- Cloud Run routes production traffic to it.

Notes:

- Buildpacks currently supports the following runtimes: Go, Java, .NET, Node.js, and Python.
- The base image is actively maintained by Google, scanned for security vulnerabilities, and patched against known issues. This means that, when you deploy an update, your service is based on an image that is as secure as possible.
- If you need to build your own container image, for example with a custom runtime, you can add your own `Dockerfile` and Buildpacks will use it instead.

## 💫 Updates

More testing from real-life users shows some issues.

First, the app does not handle pictures taken with digital cameras in non-native orientations. You can fix this using the EXIF orientation data:

```diff
-from PIL import Image
+from PIL import Image, ImageOps
...
def generate_coloring_page(input: PilImage) -> PilImage:
    # Convert to grayscale if needed
    if input.mode != "L":
        input = input.convert("L")
+   # Transpose if taken in non-native orientation (rotated digital camera)
+   NATIVE_ORIENTATION = 1
+   if input.getexif().get(0x0112, NATIVE_ORIENTATION) != NATIVE_ORIENTATION:
+       input = ImageOps.exif_transpose(input)
    np_image = np.asarray(input)
...
```

In addition, the app is too sensitive to details in the input image. Textures in paintings, or noise in pictures, can generate many edges in the processed image. You can improve the processing algorithm by adding a denoising step upfront:

```diff
...
def generate_coloring_page(input: PilImage) -> PilImage:
...
    np_image = np.asarray(input)

+   # Remove some noise to keep the most visible edges
+   np_image = skimage.restoration.denoise_tv_chambolle(np_image, weight=0.05)
    # Detect the edges
    np_image = skimage.filters.sobel(np_image)
...
```

This additional step makes the coloring page cleaner and reduces the quantity of ink used if you print it:

![La nascita di Venere by Botticelli, with and without denoising](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/4_denoising_botticelli.png)

Redeploy, and the app is automatically updated:

```sh
gcloud run deploy $SERVICE --source $SOURCE
```

## 🎉 It's alive

The app is visible as a service in Cloud Run:

![screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/a_cloud_run_services.png)

The service dashboard gives you an overview of app usage:

![screenshot](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/b_cloud_run_dashboard.png)

That's it; your image processing app is in production!

![Animated Demo](https://github.com/PicardParis/cherry-on-py-pics/raw/main/cr_image_processing/pics/demo.gif)

## 🤯 It's serverless

There are many benefits to using Cloud Run in this architecture:

- Your app is available 24/7.
- The environment is fully managed: you can focus on your code and not worry about the infrastructure.
- Your app is automatically available through HTTPS.
- You can map your app to a custom domain.
- Cloud Run scales the number of instances automatically and the billing includes only the resources used when your code runs.
- If your app is not used, Cloud Run scales down to zero.
- If your app gets more traffic (imagine it makes the news), Cloud Run scales up to the number of instances needed.
- You can control performance and cost by fine-tuning many settings: CPU, memory, concurrency, minimum instances, maximum instances, and more.
- Every month, the [free tier](https://cloud.google.com/run/pricing) offers the first 50 vCPU-hours, 100 GiB-hours, and 2 million requests for no cost.

## 💾 Source code

The project includes just seven files and less than 200 lines of Python + JavaScript code.

You can reuse this demo as a base to build your own image processing app:

- Check out the source code on [GitHub](https://github.com/PicardParis/cherry-on-py/tree/main/cr_image_processing).
- For step-by-step instructions on deploying the app yourself in a few minutes, see [“Deploying from scratch”](https://github.com/PicardParis/cherry-on-py/blob/main/cr_image_processing/DEPLOY.md).

## 🖖 More

- [Try the demo](https://coloring-page.lolo.dev) and generate your own coloring pages.
- [Learn more](https://cloud.google.com/run/docs) about Cloud Run.
- For more cloud content, follow me on Twitter ([@PicardParis](https://twitter.com/PicardParis)) or LinkedIn ([in/PicardParis](https://linkedin.com/in/PicardParis)), and feel free to get in touch with any feedback or questions.
