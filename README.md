# Denison Research Summer 24

## Overview

This repository contains the source code and resources for a research project utilizing Stereolabs AI camera ZED. The project aims to develop a system capable of predicting when a person may require assistance from a robot, focusing on analyzing facial and body movements using computer vision algorithms.

## Prerequisites

To run the provided script, ensure you have the following dependencies installed:

- Python 3.x
- PyZED SDK: Make sure you have installed the latest version of PyZED by following the installation guide provided by Stereolabs.
- zed-tools: This includes `zed360` for camera calibration.
- Other dependencies specified in `requirements.txt`.

### Installing PyZED SDK

Please follow the installation guide provided by Stereolabs to install the latest version of PyZED SDK:
[PyZED SDK Installation Guide](https://www.stereolabs.com/docs/app-development/python/install)

## Usage

### 1. Clone this repository to your local machine:

```bash
git clone https://github.com/aryah-rao/denison-research-summer-24
```

### 2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Follow the steps from here on for every experiment:

### 3. Run the Script

Run the `body_tracking_fused_cameras.py` script and enter `CONTEXT` to create a unique folder and identiy the experiment.

```bash
python body_tracking_fused_cameras.py
```

You will be prompted to enter the context:
```bash
Please enter the context for the experiment: my_experiment
```

### 4. Calibrate Cameras

The script will automatically start the `ZED360` executable for calibration. Ensure the `ZED360` executable is located in the `./zed-tools/` directory. If not, adjust the path accordingly in the script.

Follow the guide [here](https://www.stereolabs.com/docs/fusion/zed360) to complete calibration.

Save the calibration file in the directory structure `./experiments/DATE/DATE_CONTEXT/`, where `DATE` is the current date and `CONTEXT` is the context you entered for your experiment.

Example structure:
```bash
./experiments/2024-05-21/2024-05-21_my_experiment/calibration.json
```

### 6. Recording and Output

Once calibration is complete, press any key to start recording. The script will begin capturing body tracking data from the connected ZED cameras.

### 7. Stopping the script:

To stop the script and save the recorded data, press CTRL+C. The script will handle the shutdown process, save the body tracking data to a JSON file, and close all cameras. The script will output:
- One or more .svo files for each camera.
- A body_tracking.json file with the recorded body tracking data.

All these files will be saved in the same directory as the calibration file.

Example output:

```bash
./experiments/YY-MM-DD/YY-MM-DD_my_experiment/
    calibration.json
    body_tracking.json
    YY-MM-DD_12345_my_experiment.svo
    YY-MM-DD_67890_my_experiment.svo
```

### Notes

- Ensure your ZED cameras are properly connected and recognized by the system.
- The script requires the pyzed and cv2 libraries, among others. Make sure you have all dependencies installed.
- The experiments directory will be created if it does not exist.

### Troubleshooting

- If the script cannot find the calibration file, ensure it is saved in the correct directory structure.
- If any errors occur during camera initialization or recording, check the ZED SDK documentation and ensure your cameras are properly set up and connected.

## Contributors

- Dr. Matthew Law
- Shaina Khan
- Aryah Rao

## License

This repository is licensed under the [MIT License](LICENSE).
