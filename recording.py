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

import sys
import pyzed.sl as sl
from signal import signal, SIGINT
import time
import os

cam = sl.Camera()

# Handler to deal with CTRL+C properly
def handler(signal_received, frame):
    """
    Handler function to deal with CTRL+C properly.
    
    This function is called when the user presses CTRL+C. It disables the recording
    of the camera, closes the camera, and then exits the program.
    
    Parameters:
    - signal_received: The signal that was received (in this case, SIGINT)
    - frame: The current stack frame (not used in this function)
    """
    
    # Disable the recording of the camera
    cam.disable_recording()
    
    # Close the camera
    cam.close()
    
    # Exit the program
    sys.exit(0)

signal(SIGINT, handler)

def create_context_folder(context):
    """
    Creates a folder for the current date and context.
    
    This function creates a folder for the current date and context. It first
    constructs the path to the folder by joining the experiments path with the
    current date and the context. If the folder does not already exist, it is
    created. The path to the folder is then returned.
    
    Parameters:
    - context: The context for the experiment (e.g., "walking", "sitting", etc.)
    
    Returns:
    - folder_path: The path to the folder for the current date and context
    """
    
    # Define the path to the experiments folder
    experiments_path = "./experiments/"
    
    # Get the current date in the format "YYYY-MM-DD"
    current_date = time.strftime("%Y-%m-%d")
    
    # Construct the path to the folder for the current date and context
    folder_path = os.path.join(experiments_path, current_date, current_date + "_" + context)
    
    # Check if the folder already exists
    if not os.path.exists(folder_path):
        # If the folder does not exist, create it
        os.makedirs(folder_path)
    
    # Return the path to the folder
    return folder_path

def main():
    """
    Main function that records SVO files using ZED camera.
    
    This function prompts the user to enter a context for the experiment. It then
    creates a folder for the current date and context using the `create_context_folder`
    function. It opens the ZED camera and retrieves the serial number of the camera.
    It creates a recording filename using the current date, serial number, and context.
    It enables recording with the filename specified and starts recording SVO files.
    It then enters a loop to continuously grab images from the camera and increments a
    frame counter. The loop is terminated with a Ctrl-C command.
    """
    
    # Prompt user to enter context for the experiment
    context = input("Please enter the context for the experiment: ")
    
    # Create experiment folder
    experiment_folder = create_context_folder(context)
    
    # Initialize ZED camera
    init = sl.InitParameters()
    init.depth_mode = sl.DEPTH_MODE.NONE  # Set configuration parameters for the ZED

    # Open the ZED camera
    status = cam.open(init)
    
    # Check if the camera was successfully opened
    if status != sl.ERROR_CODE.SUCCESS:
        print("Camera Open", status, "Exit program.")
        exit(1)

    # Get the serial number of the camera
    serial = cam.get_camera_information().serial_number
    
    # Create recording filename
    recording_filename = os.path.join(experiment_folder, f"{time.strftime('%Y-%m-%d')}_{serial}_{context}.svo")
    
    # Enable recording with the filename specified
    recording_param = sl.RecordingParameters(recording_filename, sl.SVO_COMPRESSION_MODE.H264)
    err = cam.enable_recording(recording_param)
    
    # Check if recording was successfully enabled
    if err != sl.ERROR_CODE.SUCCESS:
        print("Recording ZED : ", err)
        exit(1)

    # Initialize runtime parameters
    runtime = sl.RuntimeParameters()
    
    # Print message indicating SVO recording has started
    print("SVO is Recording, use Ctrl-C to stop.")
    
    # Initialize frame counter
    frames_recorded = 0

    # Enter loop to continuously grab images from the camera
    while True:
        # Check if a new image is successfully acquired
        if cam.grab(runtime) == sl.ERROR_CODE.SUCCESS:
            # Increment frame counters
            frames_recorded += 1
            
            # Print frame count
            print("Frame count: " + str(frames_recorded), end="\r")

if __name__ == "__main__":
    main()
