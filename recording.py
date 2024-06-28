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
   This sample shows how to calibrate and record videos from multiple ZED 
   cameras and save a calibration file, and video files for each camera.
"""
import os
import time
import sys
import pyzed.sl as sl # type: ignore
import json
import argparse
from signal import signal, SIGINT
import subprocess  # To run the executable

# Global variables to store camera objects and body tracking data
zcameras = []  # List to keep track of active cameras
# body_json = []  # List to store serialized body tracking data
experiment_folder = ""  # Global variable to store the experiment folder path
audio_process = None  # Global variable to store the audio recording process

# Handler to deal with CTRL+C (SIGINT) signal properly
def handler(signal_received, frame):
    """
    This function is called when the program receives a SIGINT signal (usually triggered by CTRL+C).
    It performs the following steps:
    1. Disable recording for each active camera.
    2. Close each active camera.
    3. Stop audio recording.
    4. Update the calibration.json file with the new data.
    5. Exit the program.
    """
    global zcameras, experiment_folder, audio_process

    # Print a message to inform that the program is receiving the signal
    print("got sigint, shutting cameras")

    # Iterate over each active camera
    for cam in zcameras:
        # Disable recording for each camera
        cam.disable_recording()
        # Close each camera
        cam.close()

    # Stop audio recording
    stop_audio_recording()

    # print("dumping json")
    # body_tracking_file = os.path.join(experiment_folder, 'body_tracking.json')
    # with open(body_tracking_file, 'w') as outfile:
    #     json.dump(body_json, outfile)  # Save the collected body tracking data to a JSON file

    # Update the calibration.json file
    # This function updates the calibration.json file with the new data
    update_calibration(experiment_folder)

    # Print a message to inform that the program is exiting
    print("exiting")

    # Exit the program
    sys.exit(0)

# Bind the handler to the SIGINT signal (usually triggered by CTRL+C)
signal(SIGINT, handler)

# # Function to serialize body tracking data into a dictionary format
# def serialize_body(body, timestamp):
#     return {
#         "id": body.unique_object_id,  # Unique ID of the detected body
#         "ts": timestamp,  # Timestamp of the detection
#         "keypoint": body.keypoint.tolist(),  # List of keypoints (skeleton joints)
#         "confidence": body.confidence,  # Confidence level of the detection
#         # "tracking_state": body.tracking_state,
#         # "action_state": body.action_state
#     }

# Function to create the folder for the current date if it doesn't exist
def create_context_folder(context):
    """
    Creates a folder for the current date with the given context.

    Args:
        context (str): The context of the experiment.

    Returns:
        str: The path to the created folder.
    """
    # Define the path to the experiments directory
    experiments_path = "./experiments/"

    # Get the current date in the format "YYYY-MM-DD"
    current_date = time.strftime("%Y-%m-%d")

    # Construct the folder path by joining the experiments path,
    # the current date, and the context with an underscore.
    folder_path = os.path.join(experiments_path, current_date, current_date + "_" + context)

    # Check if the folder already exists
    if not os.path.exists(folder_path):
        # If the folder does not exist, create it
        os.makedirs(folder_path)

    # Return the path to the created folder
    return folder_path

# Function to run the calibration using ZED360 executable
def run_calibration(experiment_folder):
    """
    Run the ZED360 executable for calibration and read the calibration file.

    Args:
        experiment_folder (str): The path to the experiment folder.

    Returns:
        list: The fusion configurations read from the calibration file.
    """
    # Define the path to the ZED360 executable
    zed360_executable = os.path.join("./zed-tools/", "ZED360")
    
    # Check if the ZED360 executable exists
    if not os.path.exists(zed360_executable):
        # If the executable is not found, print an error message and exit
        print(f"ZED360 executable not found at {zed360_executable}")
        exit(1)
    
    # Print a message to indicate that ZED360 is starting for calibration
    print("Starting ZED360 for calibration...")
    
    # Run the ZED360 executable and wait for it to close
    subprocess.run([zed360_executable])
    
    # Construct the path to the calibration file
    calibration_file_path = os.path.join(experiment_folder, 'calibration.json')
    
    # Check if the calibration file exists
    if not os.path.exists(calibration_file_path):
        # If the calibration file is not found, print an error message and exit
        print("Calibration file not found at", calibration_file_path)
        exit(1)
    
    # Read the fusion configuration file
    fusion_configurations = sl.read_fusion_configuration_file(
        calibration_file_path,  # Path to the calibration file
        sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP,  # The coordinate system used
        sl.UNIT.METER  # The unit of measurement
    )
    
    # Check if the fusion configuration file is valid
    if len(fusion_configurations) <= 0:
        # If the file is invalid, print an error message and exit
        print("Invalid file.")
        exit(1)
    
    # Print a message to indicate successful calibration
    print("Calibration successful.")
    
    # Wait for user input before starting recording
    input("Press any key to start recording...")
    
    # Return the fusion configurations
    return fusion_configurations

# Function to update calibration.json at the end to run body_tracking later
def update_calibration(experiment_folder):
    """
    Update the calibration.json file by modifying the configuration paths for each camera
    in the JSON structure. The new configuration paths are generated based on the experiment
    folder path and the serial number of each camera.

    Args:
        experiment_folder (str): The path to the experiment folder.
    """
    # Construct the path to the calibration.json file
    json_file_path = os.path.join(experiment_folder, "calibration.json")

    # Load the JSON data from the file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Iterate over each camera entry in the JSON structure
    for serial_number, camera_data in data.items():
        # Update the type for the zed configuration
        camera_data['input']['zed']['type'] = "SVO_FILE"

        # Create the new configuration path based on the folderpath and serial number
        # Extract the base name and timestamp from the experiment folder path
        folder_name = os.path.basename(experiment_folder)
        parts = folder_name.split('_')
        timestamp = parts[0]
        base_name = '_'.join(parts[1:])
        # Construct the new configuration path using the base name, serial number, and timestamp
        new_configuration_path = os.path.join(
            experiment_folder,
            f"{timestamp}_{serial_number}_{base_name}.svo2"
        )

        # Update the configuration path in the camera data
        camera_data['input']['zed']['configuration'] = new_configuration_path

    # Write the updated JSON data back to the file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

    # Print a message to indicate that the calibration.json file has been updated successfully
    print("Calibration JSON file updated successfully.")

def start_audio_recording(output_file):
    """
    Start recording audio using arecord.

    Args:
        output_file (str): The path to the output audio file.
    """
    global audio_process
    command = ["arecord", "-f", "cd", "-t", "wav", output_file]
    audio_process = subprocess.Popen(command)
    print("Audio recording started...")

def stop_audio_recording():
    """
    Stop the audio recording.
    """
    global audio_process
    if audio_process:
        audio_process.terminate()
        audio_process.wait()
        print("Audio recording stopped.")

# Main function
def main():
    """
    This function is the main entry point of the program. It performs the following steps:
    1. Prompts the user to enter the context for the experiment.
    2. Creates an experiment folder based on the entered context.
    3. Runs the calibration process and generates fusion configurations.
    4. Initializes cameras based on the generated configurations.
    5. Performs additional initialization steps for each camera.
    6. Enables positional tracking for each camera.
    7. Sets up the necessary parameters for communication and positional tracking.
    8. Initializes the fusion object.
    9. Subscribes to each camera in the fusion configuration.
    10. Enables recording for each local camera.
    11. Starts the audio recording.
    12. Starts the main loop to grab and process body tracking data.
    13. Closes each camera and stops the audio recording when the loop is exited.
    """
    # Initialize global variables
    global zcameras, experiment_folder
    
    # Prompt the user to enter the context for the experiment
    context = input("Please enter the context for the experiment: ")
    
    # Create an experiment folder based on the entered context
    experiment_folder = create_context_folder(context)
    
    # Run the calibration process and generate fusion configurations
    fusion_configurations = run_calibration(experiment_folder)

    # Initialize dictionaries to store local camera objects and network camera identifiers
    senders = {}
    network_senders = {}

    # Set common parameters for camera initialization
    init_params = sl.InitParameters()
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP  # Set the coordinate system
    init_params.coordinate_units = sl.UNIT.METER  # Set the unit of measurement
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE  # Set the depth mode for performance
    init_params.camera_resolution = sl.RESOLUTION.HD720  # Set the camera resolution
    init_params.camera_fps = 30  # Set the camera frame rate

    # Set parameters for communication and positional tracking
    communication_parameters = sl.CommunicationParameters()
    communication_parameters.set_for_shared_memory()  # Use shared memory for communication

    positional_tracking_parameters = sl.PositionalTrackingParameters()
    positional_tracking_parameters.set_as_static = True  # Set positional tracking as static

    # body_tracking_parameters = sl.BodyTrackingParameters()
    # body_tracking_parameters.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST  # Set body tracking model
    # body_tracking_parameters.body_format = sl.BODY_FORMAT.BODY_34  # Set body format to BODY_34 (34 keypoints)
    # body_tracking_parameters.enable_body_fitting = True  # Enable body fitting
    # body_tracking_parameters.enable_tracking = True  # Enable tracking

    # Initialize cameras based on the configuration
    for conf in fusion_configurations:
        # Print the camera serial number
        print("Try to open ZED", conf.serial_number)
        init_params.input = sl.InputType()  # Initialize input type

        # For network cameras
        if conf.communication_parameters.comm_type == sl.COMM_TYPE.LOCAL_NETWORK:
            # Store network camera identifier
            network_senders[conf.serial_number] = conf.serial_number
        else:
            # For local cameras
            init_params.input = conf.input_type  # Set input type for local camera
            # Create a new camera object
            senders[conf.serial_number] = sl.Camera()
            init_params.set_from_serial_number(conf.serial_number)  # Set parameters from serial number
            # Open the camera
            status = senders[conf.serial_number].open(init_params)
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

            # # Enable body tracking
            # status = senders[conf.serial_number].enable_body_tracking(body_tracking_parameters)
            # if status != sl.ERROR_CODE.SUCCESS:
            #     print("Error enabling the body tracking of camera", conf.serial_number)
            #     del senders[conf.serial_number]  # Remove the camera if body tracking fails
            #     continue
    
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
    # bodies = sl.Bodies()  # Create a Bodies object to store body tracking data
    
    # Enable recording for each local camera
    for serial in senders:
        # Add camera to the global list for shutdown handling
        zcameras.append(senders[serial])
        # Create the recording filename
        recording_filename = f"{time.strftime('%Y-%m-%d')}_{serial}_{context}.svo"
        # Create the recording path
        recording_path = os.path.join(experiment_folder, recording_filename)
        # Set the recording parameters
        recording_param = sl.RecordingParameters(recording_path, sl.SVO_COMPRESSION_MODE.H265)
        # Get the camera object
        zed = senders[serial]
        # Enable recording
        err = zed.enable_recording(recording_param)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Error enabling recording on {serial}: {err}")
            sys.exit(1)  # Exit if recording fails
        print('both cameras recording')
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            pass

    # Start audio recording
    audio_filename = os.path.join(experiment_folder, "audio_recording.wav")
    start_audio_recording(audio_filename)

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
    # body_tracking_fusion_params = sl.BodyTrackingFusionParameters()
    # body_tracking_fusion_params.enable_tracking = True  # Enable body tracking
    # body_tracking_fusion_params.enable_body_fitting = False  # Disable body fitting
    
    # fusion.enable_body_tracking(body_tracking_fusion_params)  # Enable body tracking in fusion

    # Runtime parameters for body tracking
    # rt = sl.BodyTrackingFusionRuntimeParameters()
    # rt.skeleton_minimum_allowed_keypoints = 7  # Minimum allowed keypoints for a valid skeleton

    # viewer = gl.GLViewer()
    # viewer.init()

    # Create ZED objects filled in the main loop
    # bodies = sl.Bodies()  # Create a Bodies object to store body tracking data
    # single_bodies = [sl.Bodies]  # List to store bodies from individual cameras

    # Main loop to grab and process body tracking data
    while True:
        for serial in senders:
            zed = senders[serial]  # Get the camera object
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                # zed.retrieve_bodies(bodies)  # Retrieve body tracking data
                pass

        if fusion.process() == sl.FUSION_ERROR_CODE.SUCCESS:
            # fusion.retrieve_bodies(bodies, rt)  # Retrieve fused body tracking data
            # body_json.append([serialize_body(b, bodies.timestamp.get_milliseconds()) for b in bodies.body_list])  # Serialize and store body tracking data

            # for debug, you can retrieve the data send by each camera, as well as communication and process stat just to make sure everything is okay
            # for cam in camera_identifiers:
            #     fusion.retrieveBodies(single_bodies, rt, cam);
            # viewer.update_bodies(bodies)
            pass
            
    for sender in senders:
        senders[sender].close()  # Close each camera

    # viewer.exit()

if __name__ == '__main__':
    main()  # Run the main function
