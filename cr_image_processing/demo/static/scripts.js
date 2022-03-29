/*
Copyright 2022 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
const eInputBlock = document.getElementById('input-block')
const eSpinnerBlock = document.getElementById('spinner-block')
const eSpinner = document.getElementById('spinner')
const eOutputBlock = document.getElementById('output-block')
const eCommandBlock = document.getElementById('command-block')
const eImageComparer = document.getElementById('image-comparer')
const eBeforeImage = document.getElementById('before-image')
const eAfterImage = document.getElementById('after-image')
const eDownloadButton = document.getElementById('download-button')
const ePrintButton = document.getElementById('print-button')
var dropEffect = 'none'

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

async function onNewFile(event) {
    await processFile(this.files[0])
}

async function processFile(inputFile) {
    onProcessStart(inputFile)
    const outputFile = await fetchColoringPage(inputFile)
    onProcessEnd(outputFile)
}

async function onProcessStart(inputFile) {
    eInputBlock.hidden = true
    eOutputBlock.hidden = true
    eCommandBlock.hidden = true
    eSpinner.className = 'spinner-waiting'
    eSpinnerBlock.hidden = false

    revokeElementSource(eAfterImage)
    revokeElementSource(eBeforeImage)
    eBeforeImage.download = inputFile.name
    eBeforeImage.src = URL.createObjectURL(inputFile)
}

function revokeElementSource(element) {
    if (!element.src)
        return

    URL.revokeObjectURL(element.src)
    element.src = ''
}

async function onProcessEnd(coloringPage) {
    if (!coloringPage) {
        eSpinner.className = 'spinner-error'
        eSpinnerBlock.hidden = true
        eInputBlock.hidden = false
        return
    }
    eSpinner.className = 'spinner-finishing'

    const fileStem = eBeforeImage.download.split('.')[0]
    const fileDate = new Date().toISOString().split('.')[0]
    const fileType = coloringPage.type.split('image/')[1]
    eAfterImage.download = `coloring-page_${fileStem}_${fileDate}.${fileType}`
    eAfterImage.src = URL.createObjectURL(coloringPage)
    await eBeforeImage.decode()
    await eAfterImage.decode()

    eImageComparer.position = 50
    eDownloadButton.download = eAfterImage.download
    eDownloadButton.href = eAfterImage.src

    eSpinnerBlock.hidden = true
    eOutputBlock.hidden = false
    eCommandBlock.hidden = false
}

function onPrint(event) {
    const body = `
    <html><head><title>Coloring Page</title></head><body style="margin: 0">
        <img src="${eAfterImage.src}"
            style="width: 100vw; height: 100vh; object-fit: contain; overflow: hidden"
            onload="window.print(); window.close()">
    </body></html>`
    window.open('').document.write(body)
}

function onDragEnterLeave(event) {
    event.preventDefault()
    switch (event.type) {
        case 'dragenter':
            if (draggedImageItem(event)) {
                document.body.className = 'drop-zone-active'
                dropEffect = 'copy'
            }
            return
        case 'dragleave':
            if (!event.relatedTarget) {
                document.body.className = ''
                dropEffect = 'none'
            }
            return
    }
}

function onDragOver(event) {
    event.preventDefault()
    event.dataTransfer.dropEffect = dropEffect
}

function onFileDrop(event) {
    event.preventDefault()
    document.body.className = ''
    const item = draggedImageItem(event)
    if (item)
        processFile(item.getAsFile())
}

function draggedImageItem(event) {
    const dataTransfer = event.dataTransfer
    if (!dataTransfer || !dataTransfer.items) {
        console.log('DataTransfer is not supported')
        return null
    }
    if (dataTransfer.items.length != 1) {
        console.log('Only one input image is supported')
        return null
    }
    const item = dataTransfer.items[0]
    return (item.kind == 'file' && item.type.startsWith('image/')) ? item : null
}

function init() {
    const eInputElement = document.getElementById('input')
    eInputElement.addEventListener('change', onNewFile, false)

    document.ondragenter = document.ondragleave = onDragEnterLeave
    document.ondragover = onDragOver
    document.ondrop = onFileDrop
    ePrintButton.onclick = onPrint
}

init()
