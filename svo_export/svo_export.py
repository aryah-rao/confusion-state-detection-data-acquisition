import sys
import pyzed.sl as sl
import numpy as np
import cv2
from pathlib import Path
import enum
import argparse
import os
import time
import json
import subprocess

# Function to display a progress bar in the console
def progress_bar(current, total, bar_length=50):
    """
    Generate a progress bar in the console.

    Args:
    - current (int): The current progress.
    - total (int): The total number of steps.
    - bar_length (int): The length of the progress bar. Default is 50.
    """
    # Calculate the percentage of completion
    percent_done = int(100 * current / total)

    # Calculate the length of the filled part of the progress bar
    done_length = int(bar_length * percent_done / 100)

    # Create the progress bar string
    # '=' represents filled part, '-' represents unfilled part
    bar = '=' * done_length + '-' * (bar_length - done_length)

    # Write the progress bar to the console
    # %s represents a string, %i represents an integer
    sys.stdout.write('[%s] %i%%\r' % (bar, percent_done))

    # Flush the output buffer to ensure the progress bar is updated immediately
    sys.stdout.flush()

# Enum to define application types for different video outputs
class AppType(enum.Enum):
    LEFT_AND_RIGHT = 1

# Function to calculate the average frame rate of an SVO file
def calculate_average_frame_rate(svo_path):
    """
    Calculate the average frame rate of an SVO file.

    Args:
    - svo_path (str): The path to the SVO file.

    Returns:
    - average_frame_rate (float): The average frame rate of the SVO file.
                                  Returns None if the average frame rate is not greater than zero.
    """

    # Initialize SVO initialization parameters
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_path)
    init_params.svo_real_time_mode = False  # Set the SVO in non-real-time mode

    # Open the SVO file
    zed = sl.Camera()
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open SVO file:", svo_path)
        return None

    # Get the total number of frames in the SVO file
    total_frames = zed.get_svo_number_of_frames()
    print(f"Total frames in the SVO file: {total_frames}")

    # Set the SVO position to the first frame
    zed.set_svo_position(0)

    # Grab the first frame
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Get the start timestamp of the SVO file
        start_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Start timestamp: {start_timestamp} microseconds")
    else:
        print("Failed to grab the first frame.")
        zed.close()
        return None

    # Set the SVO position to the last frame
    zed.set_svo_position(total_frames - 1)

    # Grab the last frame
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Get the end timestamp of the SVO file
        end_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Last frame timestamp: {end_timestamp} microseconds")
    else:
        print("Failed to grab the last frame.")
        zed.close()
        return None

    # Close the SVO file
    zed.close()

    # Calculate the elapsed time in seconds
    elapsed_time = (end_timestamp - start_timestamp) / 1000000.0
    print(f"Elapsed time in seconds: {elapsed_time}")

    # Calculate the number of successfully captured frames
    successfully_captured_frames = total_frames
    print(f"Successfully captured frames: {successfully_captured_frames}")

    # Calculate the average frame rate
    if successfully_captured_frames > 0 and elapsed_time > 0:
        average_frame_rate = successfully_captured_frames / elapsed_time
    else:
        average_frame_rate = 0

    # Check if the calculated average frame rate is greater than zero
    if average_frame_rate <= 0:
        print("Calculated average frame rate is not greater than zero.")
        return None

    # Print the average frame rate
    print("Average Frame Rate: ", average_frame_rate)

    # Return the average frame rate
    return average_frame_rate

# Main function
def main():
    # Get the folder path from command line arguments
    folder_path = opt.folder_path
    
    # Get the list of SVO files in the specified folder
    svo_files = sorted(Path(folder_path).rglob("*.svo2")) + sorted(Path(folder_path).rglob("*.svo"))
    
    # If no SVO files are found, print an error message and exit
    if not svo_files:
        print("No .svo or .svo2 files found in the specified folder.")
        exit()
    
    # Get the path to the first SVO file
    svo_path = svo_files[0]

    # Set the app type to LEFT_AND_RIGHT
    app_type = AppType.LEFT_AND_RIGHT

    # Get the file paths
    current_folder_name = os.path.basename(folder_path)
    output_avi_path = os.path.join(folder_path, f"{current_folder_name}.avi")
    audio_file_path = os.path.join(folder_path, "audio_recording.wav")
    output_final_video_path = os.path.join(folder_path, f"{current_folder_name}_with_audio.mp4")

    # Calculate the average frame rate of the SVO file
    average_frame_rate = calculate_average_frame_rate(str(svo_path))
    
    # If the average frame rate is not calculated successfully, print an error message and exit
    if average_frame_rate is None:
        print("Failed to calculate average frame rate.")
        exit()

    # Create a dictionary to store metadata
    metadata = {"average_frame_rate": average_frame_rate, "seconds": [], "frames": []}
    
    # Construct the path to the metadata file and write the metadata to it
    metadata_path = os.path.join(folder_path, "metadata.json")
    with open(metadata_path, "w") as json_file:
        json.dump(metadata, json_file)

    # Initialize the ZED camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    
    # Set the initialization parameters to use the SVO file
    init_params.set_from_svo_file(str(svo_path))
    init_params.svo_real_time_mode = False
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE

    # Open the SVO file
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open SVO file:", svo_path)
        exit()

    # Get the image size from the ZED camera
    image_size = zed.get_camera_information().camera_configuration.resolution
    width = image_size.width
    height = image_size.height
    width_sbs = width * 2

    # Create a numpy array to store the images
    svo_image_sbs_rgba = np.zeros((height, width_sbs, 4), dtype=np.uint8)
    
    # Create two sl.Mat objects to store the left and right images
    left_image = sl.Mat()
    right_image = sl.Mat()

    # Create an OpenCV video writer to write the AVI file
    video_writer = cv2.VideoWriter(output_avi_path,
                                   cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'),
                                   average_frame_rate,
                                   (width_sbs, height))
    
    # If the video writer cannot be opened, print an error message and exit
    if not video_writer.isOpened():
        print("OpenCV video writer cannot be opened. Please check the .avi file path and write permissions.")
        zed.close()
        exit()

    # Get the total number of frames in the SVO file
    total_frames = zed.get_svo_number_of_frames()

    # Print a progress bar to indicate the conversion progress
    print("Converting SVO file... Use Ctrl-C to interrupt conversion.")

    # Initialize a counter for the current frame
    current_frame = 0
    
    # Create a sl.RuntimeParameters object
    rt_param = sl.RuntimeParameters()

    # Start the conversion loop
    while True:
        # Grab a frame from the SVO file
        if zed.grab(rt_param) == sl.ERROR_CODE.SUCCESS:
            # Retrieve the left and right images from the ZED camera
            zed.retrieve_image(left_image, sl.VIEW.LEFT)
            zed.retrieve_image(right_image, sl.VIEW.RIGHT)

            # Copy the left and right images to the svo_image_sbs_rgba numpy array
            svo_image_sbs_rgba[0:height, 0:width, :] = left_image.get_data()
            svo_image_sbs_rgba[0:height, width:width_sbs, :] = right_image.get_data()

            # Convert the svo_image_sbs_rgba numpy array to an OpenCV image
            ocv_image_sbs_rgb = cv2.cvtColor(svo_image_sbs_rgba, cv2.COLOR_RGBA2RGB)
            
            # Write the OpenCV image to the AVI file
            video_writer.write(ocv_image_sbs_rgb)

            # Increment the current frame counter
            current_frame += 1
            
            # Print the progress bar
            progress_bar(current_frame, total_frames)
        else:
            # If grabbing a frame fails, break the loop
            break

    # Release the video writer and close the ZED camera
    video_writer.release()
    zed.close()

    # Print a completion message
    print("\nConversion completed.")
    
    # Combine the AVI file with the WAV file
    if os.path.exists(audio_file_path):
        ffmpeg_command = [
            "ffmpeg",
            "-i", output_avi_path,
            "-i", audio_file_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_final_video_path
        ]

        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
        print(result.stderr.decode())
        print("AVI and WAV files combined successfully.")
    else:
        print(f"Audio file not found at {audio_file_path}. Skipping audio merging.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--mode', type=int, required=True, help=" Mode 0 is to export LEFT+RIGHT AVI.")
    parser.add_argument('--folder_path', type=str, required=True, help='Path to the folder containing .svo or .svo2 files')
    opt = parser.parse_args()

    if opt.mode != 0:
        print("Mode should be 0 for exporting LEFT+RIGHT AVI.")
        exit()
    
    if not os.path.isdir(opt.folder_path):
        print("--folder_path parameter should be an existing directory but is not: ", opt.folder_path)
        exit()

    main()
