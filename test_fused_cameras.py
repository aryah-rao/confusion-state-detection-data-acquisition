########################################################################
#
# Copyright (c) 2022, STEREOLABS.
#
# All rights reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################

"""
   This sample shows how to detect human bodies and draw their 
   modelized skeleton in an OpenGL window
"""
import os
import datetime
import cv2
import sys
import pyzed.sl as sl
import time
import ogl_viewer.viewer as gl
import numpy as np
import json
import argparse
from signal import signal, SIGINT

# Global variables to store camera objects and body tracking data
zcameras = []  # List to keep track of active cameras
body_json = []  # List to store serialized body tracking data

# Handler to deal with CTRL+C (SIGINT) signal properly
def handler(signal_received, frame):
    global zcameras, body_json
    print("got sigint, shutting cameras")
    for cam in zcameras:
        cam.disable_recording()  # Disable recording for each camera
        cam.close()  # Close each camera
    print("dumping json")
    with open('body_tracking.json', 'w') as outfile:
        json.dump(body_json, outfile)  # Save the collected body tracking data to a JSON file
    print("exiting")
    sys.exit(0)  # Exit the program

# Bind the handler to the SIGINT signal (usually triggered by CTRL+C)
signal(SIGINT, handler)

# Function to serialize body tracking data into a dictionary format
def serialize_body(body, timestamp):
    return {
        "id": body.unique_object_id,  # Unique ID of the detected body
        "ts": timestamp,  # Timestamp of the detection
        "keypoint": body.keypoint.tolist(),  # List of keypoints (skeleton joints)
        "confidence": body.confidence,  # Confidence level of the detection
        # "tracking_state": body.tracking_state,
        # "action_state": body.action_state
    }

# Function to create the folder for the current date if it doesn't exist
def create_experiment_folder():
    experiments_path = "./experiments/"
    current_date = time.strftime("%Y-%m-%d")
    folder_path = os.path.join(experiments_path, current_date)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

# Main function
def main():
    global zcameras, body_json
    
    # Create experiment folder
    experiment_folder = create_experiment_folder()

    # Check if the necessary argument (localization file) is provided
    if len(sys.argv) < 2:
        print("This sample displays the fused body tracking of multiple cameras.")
        print("It needs a Localization file in input. Generate it with ZED 360.")
        print("The cameras can either be plugged to your devices, or already running on the local network.")
        exit(1)

    # Read the fusion configuration file
    filepath = sys.argv[1]
    fusion_configurations = sl.read_fusion_configuration_file(filepath, sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP, sl.UNIT.METER)
    if len(fusion_configurations) <= 0:
        print("Invalid file.")
        exit(1)

    senders = {}  # Dictionary to store local camera objects
    network_senders = {}  # Dictionary to store network camera identifiers

    # Common parameters for camera initialization
    init_params = sl.InitParameters()
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP  # Set the coordinate system
    init_params.coordinate_units = sl.UNIT.METER  # Set the unit of measurement
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE  # Set the depth mode for performance
    init_params.camera_resolution = sl.RESOLUTION.HD720  # Set the camera resolution
    init_params.camera_fps = 30  # Set the camera frame rate

    # Parameters for communication, positional tracking, and body tracking
    communication_parameters = sl.CommunicationParameters()
    communication_parameters.set_for_shared_memory()  # Use shared memory for communication

    positional_tracking_parameters = sl.PositionalTrackingParameters()
    positional_tracking_parameters.set_as_static = True  # Set positional tracking as static

    body_tracking_parameters = sl.BodyTrackingParameters()
    body_tracking_parameters.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST  # Set body tracking model
    body_tracking_parameters.body_format = sl.BODY_FORMAT.BODY_34  # Set body format to BODY_34 (34 keypoints)
    body_tracking_parameters.enable_body_fitting = True  # Enable body fitting
    body_tracking_parameters.enable_tracking = True  # Enable tracking

    # Initialize cameras based on the configuration
    for conf in fusion_configurations:
        print("Try to open ZED", conf.serial_number)
        init_params.input = sl.InputType()  # Initialize input type

        # For network cameras
        if conf.communication_parameters.comm_type == sl.COMM_TYPE.LOCAL_NETWORK:
            network_senders[conf.serial_number] = conf.serial_number  # Store network camera identifier
        else:
            # For local cameras
            init_params.input = conf.input_type  # Set input type for local camera
            senders[conf.serial_number] = sl.Camera()  # Create a new camera object
            init_params.set_from_serial_number(conf.serial_number)  # Set parameters from serial number
            status = senders[conf.serial_number].open(init_params)  # Open the camera
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error opening the camera", conf.serial_number, status)
                del senders[conf.serial_number]  # Remove the camera from the list if it fails to open
                continue

            # Enable positional tracking
            status = senders[conf.serial_number].enable_positional_tracking(positional_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the positional tracking of camera", conf.serial_number)
                del senders[conf.serial_number]  # Remove the camera if positional tracking fails
                continue

            # Enable body tracking
            status = senders[conf.serial_number].enable_body_tracking(body_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the body tracking of camera", conf.serial_number)
                del senders[conf.serial_number]  # Remove the camera if body tracking fails
                continue

            # Start publishing data
            senders[conf.serial_number].start_publishing(communication_parameters)  # Start data publishing

        print("Camera", conf.serial_number, "is open")
    
    # Check if there are enough cameras
    if len(senders) + len(network_senders) < 1:
        print("No enough cameras")
        exit(1)

    print("Senders started, running the fusion...")
    
    # Initialize fusion parameters
    init_fusion_parameters = sl.InitFusionParameters()
    init_fusion_parameters.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP  # Set coordinate system
    init_fusion_parameters.coordinate_units = sl.UNIT.METER  # Set unit of measurement
    init_fusion_parameters.output_performance_metrics = False  # Disable performance metrics output
    init_fusion_parameters.verbose = True  # Enable verbose mode
    communication_parameters = sl.CommunicationParameters()
    fusion = sl.Fusion()  # Create a Fusion object
    camera_identifiers = []  # List to store camera identifiers

    # Initialize the fusion object
    fusion.init(init_fusion_parameters)
    
    print("Cameras in this configuration : ", len(fusion_configurations))

    # Warmup recording
    bodies = sl.Bodies()  # Create a Bodies object to store body tracking data

    # Enable recording for each local camera
    context = input("Please enter the context for the recording files: ")

    for serial in senders:
        zcameras.append(senders[serial])  # Add camera to the global list for shutdown handling
        recording_filename = f"{time.strftime('%Y-%m-%d_%H-%M-%S')}_{serial}_{context}.svo"
        recording_path = os.path.join(experiment_folder, recording_filename)
        recording_param = sl.RecordingParameters(recording_path, sl.SVO_COMPRESSION_MODE.H265)  # Set recording parameters
        zed = senders[serial]  # Get the camera object
        err = zed.enable_recording(recording_param)  # Enable recording
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Error enabling recording on {serial}: {err}")
            sys.exit(1)  # Exit if recording fails
        print('both cameras recording')
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_bodies(bodies)  # Retrieve body tracking data

    # Subscribe to each camera in the fusion configuration
    for i in range(0, len(fusion_configurations)):
        conf = fusion_configurations[i]
        uuid = sl.CameraIdentifier()  # Create a CameraIdentifier object
        uuid.serial_number = conf.serial_number  # Set the serial number
        print("Subscribing to", conf.serial_number, conf.communication_parameters.comm_type)

        status = fusion.subscribe(uuid, conf.communication_parameters, conf.pose)  # Subscribe to the camera
        if status != sl.FUSION_ERROR_CODE.SUCCESS:
            print("Unable to subscribe to", uuid.serial_number, status)
        else:
            camera_identifiers.append(uuid)  # Add the camera identifier to the list
            print("Subscribed.")

    # Check if there are any subscribed cameras
    if len(camera_identifiers) <= 0:
        print("No camera connected.")
        sys.exit(1)  # Exit if no cameras are connected

    # Set fusion body tracking parameters
    body_tracking_fusion_params = sl.BodyTrackingFusionParameters()
    body_tracking_fusion_params.enable_tracking = True  # Enable body tracking
    body_tracking_fusion_params.enable_body_fitting = False  # Disable body fitting
    
    fusion.enable_body_tracking(body_tracking_fusion_params)  # Enable body tracking in fusion

    # Runtime parameters for body tracking
    rt = sl.BodyTrackingFusionRuntimeParameters()
    rt.skeleton_minimum_allowed_keypoints = 7  # Minimum allowed keypoints for a valid skeleton

    # viewer = gl.GLViewer()
    # viewer.init()

    # Create ZED objects filled in the main loop
    bodies = sl.Bodies()  # Create a Bodies object to store body tracking data
    single_bodies = [sl.Bodies]  # List to store bodies from individual cameras

    # Main loop to grab and process body tracking data
    while True:
        for serial in senders:
            zed = senders[serial]  # Get the camera object
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_bodies(bodies)  # Retrieve body tracking data

        if fusion.process() == sl.FUSION_ERROR_CODE.SUCCESS:
            fusion.retrieve_bodies(bodies, rt)  # Retrieve fused body tracking data
            body_json.append([serialize_body(b, bodies.timestamp.get_milliseconds()) for b in bodies.body_list])  # Serialize and store body tracking data

            # for debug, you can retrieve the data send by each camera, as well as communication and process stat just to make sure everything is okay
            # for cam in camera_identifiers:
            #     fusion.retrieveBodies(single_bodies, rt, cam);
            # viewer.update_bodies(bodies)
            
    for sender in senders:
        senders[sender].close()  # Close each camera

    # viewer.exit()

if __name__ == '__main__':
    main()  # Run the main function
