# TrustID Face Model Provenance

## SFace

| Field | Value |
|---|---|
| Model | OpenCV Zoo SFace `face_recognition_sface_2021dec.onnx` |
| Architecture | SFace face-recognition embedding model exposed through OpenCV `FaceRecognizerSF` |
| Source repository | [opencv/opencv_zoo](https://github.com/opencv/opencv_zoo) |
| Source URL | [SFace model path](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) |
| SHA-256 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| Embedding dimension | 128, observed during local inference |
| Runtime | `opencv-contrib-python-headless`, OpenCV `FaceRecognizerSF` |
| License/provenance status | Upstream repository and model terms require legal review for the intended deployment. No commercial clearance is claimed. |

## YuNet

| Field | Value |
|---|---|
| Model | OpenCV Zoo YuNet `face_detection_yunet_2023mar.onnx` |
| Architecture | YuNet face detector with five-point landmark output |
| Source repository | [opencv/opencv_zoo](https://github.com/opencv/opencv_zoo) |
| Source URL | [YuNet model path](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |
| SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| Runtime | OpenCV `FaceDetectorYN` |
| License/provenance status | Upstream repository and model terms require legal review for the intended deployment. No commercial clearance is claimed. |

## Provisioning

`apps/api/scripts/provision_face_models.sh` downloads the exact pinned files from the OpenCV Zoo source URLs and refuses to continue on a checksum mismatch. `apps/api/Dockerfile` invokes this script during image build. Model files are not committed to Git.

## Open review items

Software license, model license, training-data provenance, intended-use restrictions, and commercial-use interpretation are separate questions. This repository records the exact source and checksum but does not represent the models as legally cleared for commercial biometric deployment.

**LEGAL / MODEL PROVENANCE REVIEW = OPEN**
