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
   modelled skeleton in an OpenGL window
"""
import cv2
import sys
import pyzed.sl as sl
import ogl_viewer.viewer as gl
import cv_viewer.tracking_viewer as cv_viewer
import numpy as np
import argparse
import os
import json

body_json = []

def serialize_body(body, timestamp):
    return {
        "id": body.unique_object_id,  # Unique ID of the detected body
        "ts": timestamp,  # Timestamp of the detection
        "keypoint": body.keypoint.tolist(),  # List of keypoints (skeleton joints)
        "keypoint_confidence": body.keypoint_confidence.tolist(),
        "confidence": body.confidence,  # Confidence level of the detection
        # "tracking_state": body.tracking_state,
        # "action_state": body.action_state
    }

def parse_args(init):
    """
    Parse command line arguments and set initial parameters for the ZED camera

    Args:
        init (sl.InitParameters): The initialization parameters for the ZED camera
    """
    # Check if a folder path was specified
    if len(opt.folder_path) > 0:
        # Get a list of all files in the folder that end with .svo2 or .svo
        svo_files = [f for f in os.listdir(opt.folder_path) if f.endswith(".svo2") or f.endswith(".svo")]
        
        # If there is at least one SVO file in the folder
        if svo_files:
            # Get the first SVO file in the folder
            svo_file_path = os.path.join(opt.folder_path, svo_files[0])
            
            # Set the initialization parameters to use the SVO file as input
            init.set_from_svo_file(svo_file_path)
            print("[Sample] Using SVO File input: {0}".format(svo_file_path))
        else:
            print("No SVO files found in the specified folder. Using live stream")
    # Check if an IP address was specified
    elif len(opt.ip_address) > 0:
        # Get the IP address specified by the user
        ip_str = opt.ip_address
        
        # Check if the IP address is in the format of "xxx.xxx.xxx.xxx:xxxx" where x is a digit and the second part is a number between 0 and 65535
        if ip_str.replace(':','').replace('.','').isdigit() and len(ip_str.split('.')) == 4 and len(ip_str.split(':')) == 2:
            # Split the IP address and port and set the initialization parameters to use the stream as input
            init.set_from_stream(ip_str.split(':')[0], int(ip_str.split(':')[1]))
            print("[Sample] Using Stream input, IP : ", ip_str)
        # Check if the IP address is in the format of "xxx.xxx.xxx.xxx" where x is a digit
        elif ip_str.replace(':','').replace('.','').isdigit() and len(ip_str.split('.')) == 4:
            # Set the initialization parameters to use the stream as input
            init.set_from_stream(ip_str)
            print("[Sample] Using Stream input, IP : ", ip_str)
        else:
            print("Invalid IP format. Using live stream")
    # Check if a specific resolution was specified
    if "HD2K" in opt.resolution:
        # Set the camera resolution to HD2K
        init.camera_resolution = sl.RESOLUTION.HD2K
        print("[Sample] Using Camera in resolution HD2K")
    elif "HD1200" in opt.resolution:
        # Set the camera resolution to HD1200
        init.camera_resolution = sl.RESOLUTION.HD1200
        print("[Sample] Using Camera in resolution HD1200")
    elif "HD1080" in opt.resolution:
        # Set the camera resolution to HD1080
        init.camera_resolution = sl.RESOLUTION.HD1080
        print("[Sample] Using Camera in resolution HD1080")
    elif "HD720" in opt.resolution:
        # Set the camera resolution to HD720
        init.camera_resolution = sl.RESOLUTION.HD720
        print("[Sample] Using Camera in resolution HD720")
    elif "SVGA" in opt.resolution:
        # Set the camera resolution to SVGA
        init.camera_resolution = sl.RESOLUTION.SVGA
        print("[Sample] Using Camera in resolution SVGA")
    elif "VGA" in opt.resolution:
        # Set the camera resolution to VGA
        init.camera_resolution = sl.RESOLUTION.VGA
        print("[Sample] Using Camera in resolution VGA")
    elif len(opt.resolution) > 0: 
        print("[Sample] No valid resolution entered. Using default")
    else: 
        print("[Sample] Using default resolution")


def main():
    # Print a message to indicate that the Body Tracking sample is running
    print("Running Body Tracking sample ... Press 'q' to quit, or 'm' to pause or restart")

    # Create a Camera object
    zed = sl.Camera()

    # Create a InitParameters object and set configuration parameters
    init_params = sl.InitParameters()
    # Set the camera video mode to HD1080
    init_params.camera_resolution = sl.RESOLUTION.HD1080
    # Set the coordinate units to meters
    init_params.coordinate_units = sl.UNIT.METER
    # Set the depth mode to ULTRA
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    # Set the coordinate system to right-handed Y-up
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    
    # Parse command line arguments and set initialization parameters
    parse_args(init_params)

    # Open the camera
    err = zed.open(init_params)
    # If the camera cannot be opened, exit the program
    if err != sl.ERROR_CODE.SUCCESS:
        exit(1)

    # Enable Positional tracking (mandatory for object detection)
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    # If the camera is static, uncomment the following line to have better performances
    # positional_tracking_parameters.set_as_static = True
    # Enable Positional tracking
    zed.enable_positional_tracking(positional_tracking_parameters)
    
    # Create BodyTrackingParameters object and set configuration parameters
    body_param = sl.BodyTrackingParameters()
    # Enable tracking of people across images flow
    body_param.enable_tracking = True
    # Disable smooth skeleton movement
    body_param.enable_body_fitting = False
    # Set the body detection model to HUMAN_BODY_FAST
    body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST 
    # Choose the BODY_FORMAT to use
    body_param.body_format = sl.BODY_FORMAT.BODY_18 

    # Enable Object Detection module
    zed.enable_body_tracking(body_param)

    # Create BodyTrackingRuntimeParameters object and set configuration parameters
    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    # Set the detection confidence threshold
    body_runtime_param.detection_confidence_threshold = 40

    # Get ZED camera information
    camera_info = zed.get_camera_information()
    # Calculate the display resolution based on the camera resolution and a maximum of 1280x720
    display_resolution = sl.Resolution(min(camera_info.camera_configuration.resolution.width, 1280), min(camera_info.camera_configuration.resolution.height, 720))
    # Calculate the image scale based on the display resolution and the camera resolution
    image_scale = [display_resolution.width / camera_info.camera_configuration.resolution.width
                 , display_resolution.height / camera_info.camera_configuration.resolution.height]

    # Create OpenGL viewer
    viewer = gl.GLViewer()
    # Initialize the OpenGL viewer with the camera calibration parameters, body tracking enabled, and the chosen BODY_FORMAT
    viewer.init(camera_info.camera_configuration.calibration_parameters.left_cam, body_param.enable_tracking, body_param.body_format)
    # Create ZED objects filled in the main loop
    bodies = sl.Bodies()
    image = sl.Mat()
    key_wait = 10 
    while viewer.is_available():
        # Grab an image
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            # Retrieve left image
            zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
            # Retrieve bodies
            zed.retrieve_bodies(bodies, body_runtime_param)
            body_json.append([serialize_body(b, bodies.timestamp.get_milliseconds()) for b in bodies.body_list]) 
            # Update GL view
            viewer.update_view(image, bodies) 
            # Update OCV view
            image_left_ocv = image.get_data()
            cv_viewer.render_2D(image_left_ocv, image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format)
            cv2.imshow("ZED | 2D View", image_left_ocv)
            key = cv2.waitKey(key_wait)
            # If 'q' key is pressed, exit the program
            if key == 113: 
                print("Exiting...")
                break
            # If 'm' key is pressed, pause or restart the program
            if key == 109: 
                if key_wait > 0:
                    print("Pause")
                    key_wait = 0 
                else: 
                    print("Restart")
                    key_wait = 10 
        else:
            break
    with open(os.path.join(opt.folder_path,"body_tracking.json"), "w+") as outfile:
        json.dump(body_json, outfile)
    # Clean up resources
    viewer.exit()
    image.free(sl.MEM.CPU)
    # Disable body tracking and positional tracking
    zed.disable_body_tracking()
    zed.disable_positional_tracking()
    # Close the camera
    zed.close()
    # Close the OpenCV window
    cv2.destroyAllWindows()
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder_path', type=str, help='Path to a folder containing .svo or .svo2 files', default='')
    parser.add_argument('--ip_address', type=str, help='IP Address, in format a.b.c.d:port or a.b.c.d, if you have a streaming setup', default = '')
    parser.add_argument('--resolution', type=str, help='Resolution, can be either HD2K, HD1200, HD1080, HD720, SVGA or VGA', default = '')
    opt = parser.parse_args()
    if len(opt.folder_path) > 0 and len(opt.ip_address) > 0:
        print("Specify only folder_path or ip_address, or none to use wired camera, not both. Exit program")
        exit()
    main() 
