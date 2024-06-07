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
   This sample shows how to detect a human bodies and draw their 
   modelised skeleton in an OpenGL window
"""
import argparse
import sys
import pyzed.sl as sl  # type: ignore
import time
import ogl_viewer.viewer as gl
import numpy as np
import json
import os

body_json = {}  # Dictionary to store serialized body tracking data

def serialize_body(body, timestamp):
    """
    Serialize the body tracking data into a dictionary format.

    Args:
        body (sl.Body): The body object containing the tracking data.
        timestamp (float): The timestamp of the detection.

    Returns:
        dict: A dictionary containing the serialized body tracking data.
    """
    # Create a dictionary to store the serialized body tracking data
    serialized_body = {
        "id": body.unique_object_id,  # Unique ID of the detected body
        "ts": timestamp,  # Timestamp of the detection
        "keypoint": body.keypoint.tolist(),  # List of keypoints (skeleton joints)
        "keypoint_confidence": body.keypoint_confidence.tolist(),  # Confidence levels of the keypoints
        "confidence": body.confidence  # Confidence level of the detection
    }

    # Return the serialized body tracking data
    return serialized_body

def main():
    """
    This function reads the localization file, initializes the cameras based on the configuration, and performs body tracking on the cameras.
    It then saves the body tracking data to a JSON file.
    """
    # Read the localization file
    filepath = os.path.join(opt.folder_path, 'calibration.json')
    fusion_configurations = sl.read_fusion_configuration_file(filepath, sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP, sl.UNIT.METER)
    if len(fusion_configurations) <= 0:
        print("Invalid file.")
        exit(1)

    # Initialize the camera senders dictionary
    senders = {}
    network_senders = {}

    # Initialize the common parameters
    init_params = sl.InitParameters()
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_params.coordinate_units = sl.UNIT.METER
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.camera_resolution = sl.RESOLUTION.HD1080

    # Set the communication parameters
    communication_parameters = sl.CommunicationParameters()
    communication_parameters.set_for_shared_memory()

    # Set the positional tracking parameters
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    positional_tracking_parameters.set_as_static = True

    # Set the body tracking parameters
    body_tracking_parameters = sl.BodyTrackingParameters()
    body_tracking_parameters.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_ACCURATE
    body_tracking_parameters.body_format = sl.BODY_FORMAT.BODY_34
    body_tracking_parameters.enable_body_fitting = True
    body_tracking_parameters.enable_tracking = True

    # Open each camera based on the localization configuration
    for conf in fusion_configurations:
        print("Trying to open ZED", conf.serial_number)
        init_params.input = sl.InputType()

        # If the camera is already running on the local network
        if conf.communication_parameters.comm_type == sl.COMM_TYPE.LOCAL_NETWORK:
            network_senders[conf.serial_number] = conf.serial_number

        # If the camera is connected to the device
        else:
            init_params.input = conf.input_type
            
            # Create a ZED camera object
            senders[conf.serial_number] = sl.Camera()

            # Open the camera
            status = senders[conf.serial_number].open(init_params)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error opening the camera", conf.serial_number, status)
                del senders[conf.serial_number]
                continue

            # Enable the positional tracking
            status = senders[conf.serial_number].enable_positional_tracking(positional_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the positional tracking of camera", conf.serial_number)
                del senders[conf.serial_number]
                continue

            # Enable the body tracking
            status = senders[conf.serial_number].enable_body_tracking(body_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the body tracking of camera", conf.serial_number)
                del senders[conf.serial_number]
                continue

            # Start publishing the camera data
            senders[conf.serial_number].start_publishing(communication_parameters)

        print("Camera", conf.serial_number, "is open")
    
    # Check if enough cameras are connected
    if len(senders) + len(network_senders) < 1:
        print("No enough cameras")
        exit(1)

    print("Senders started, running the fusion...")
        
    # Initialize the fusion parameters
    init_fusion_parameters = sl.InitFusionParameters()
    init_fusion_parameters.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_fusion_parameters.coordinate_units = sl.UNIT.METER
    init_fusion_parameters.output_performance_metrics = False
    init_fusion_parameters.verbose = True

    # Set the communication parameters for fusion
    communication_parameters = sl.CommunicationParameters()
    
    # Create a fusion object
    fusion = sl.Fusion()
    
    # Initialize the fusion
    fusion.init(init_fusion_parameters)
        
    print("Cameras in this configuration : ", len(fusion_configurations))

    # Warm-up the camera data
    bodies = sl.Bodies()        
    for serial in senders:
        zed = senders[serial]
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_bodies(bodies)

    # Subscribe each camera to the fusion
    camera_identifiers = []
    for i in range(0, len(fusion_configurations)):
        conf = fusion_configurations[i]
        uuid = sl.CameraIdentifier()
        uuid.serial_number = conf.serial_number
        print("Subscribing to", conf.serial_number, conf.communication_parameters.comm_type)

        # Subscribe the camera to the fusion
        status = fusion.subscribe(uuid, conf.communication_parameters, conf.pose)
        if status != sl.FUSION_ERROR_CODE.SUCCESS:
            print("Unable to subscribe to", uuid.serial_number, status)
        else:
            camera_identifiers.append(uuid)
            print("Subscribed.")

    # Check if any camera is connected
    if len(camera_identifiers) <= 0:
        print("No camera connected.")
        exit(1)

    # Enable the body tracking in the fusion
    body_tracking_fusion_params = sl.BodyTrackingFusionParameters()
    body_tracking_fusion_params.enable_tracking = True
    body_tracking_fusion_params.enable_body_fitting = True
    
    fusion.enable_body_tracking(body_tracking_fusion_params)

    # Set the runtime parameters for the body tracking fusion
    rt = sl.BodyTrackingFusionRuntimeParameters()
    rt.skeleton_minimum_allowed_keypoints = 7
    
    # Create the OpenGL viewer
    viewer = gl.GLViewer()
    viewer.init()

    # Create the objects to store the bodies
    bodies = sl.Bodies()

    frame_number = 0

    # Main loop to retrieve and display the bodies
#    while True:
    while (viewer.is_available()):
        for serial in senders:
            zed = senders[serial]
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_bodies(bodies)
            elif zed.grab() == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
                break

        # Process the fusion
        if fusion.process() == sl.FUSION_ERROR_CODE.SUCCESS:
            
            # Retrieve the detected bodies
            fusion.retrieve_bodies(bodies, rt)
            
            # Update the viewer with the bodies
            viewer.update_bodies(bodies)

            # Serialize body tracking data
            body_json[frame_number] = [serialize_body(b, bodies.timestamp.get_milliseconds()) for b in bodies.body_list]  # Serialize and store body tracking data

            # Increment the frame number
            frame_number += 1

        elif zed.grab() == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            break
        
    # Save the body tracking data to a JSON file
    output_filepath = os.path.join(opt.folder_path, "body_tracking.json")
    with open(output_filepath, "w") as outfile:
        json.dump(body_json, outfile, indent=4)

    # Close the camera objects
    for sender in senders:
        senders[sender].close()
        
    # Exit the viewer
    viewer.exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser() # Create an argument parser
    parser.add_argument('--folder_path', type=str, help='Path to the localization file', required=True)
    opt = parser.parse_args()

    # Validate the folder path
    if not os.path.isdir(opt.folder_path):
        print("--folder_path parameter should be an existing directory but is not: ", opt.folder_path)
        exit()

    main()
