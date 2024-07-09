import sys
import pyzed.sl as sl # type: ignore
import numpy as np
import cv2 # type: ignore
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
    This function generates a progress bar to display the progress of a task
    in the console. It takes three arguments:
        - current: the current progress value
        - total: the total number of steps in the task
        - bar_length: the length of the progress bar (default is 50)
    The function calculates the percentage of progress and the length of the
    progress bar, and then creates a visual representation of the progress bar
    using either '=' characters for progress and '-' characters for remaining
    progress. The function then prints the progress bar to the console.
    """
    # Calculate the percentage of progress
    percent_done = int(100 * current / total)
    # Calculate the length of the progress bar
    done_length = int(bar_length * percent_done / 100)
    # Create the visual representation of the progress bar
    # This is achieved by creating a string where the first 'done_length'
    # characters are '=' and the remaining characters are '-'.
    bar = '=' * done_length + '-' * (bar_length - done_length)
    # Print the progress bar to the console
    # The '%s' is a placeholder for the progress bar string, and the '%i%%'
    # is a placeholder for the percentage of progress as an integer.
    # The '\r' at the end of the string tells the console to overwrite the
    # previous progress bar with the updated progress bar.
    sys.stdout.write('[%s] %i%%\r' % (bar, percent_done))
    sys.stdout.flush()

# Enum to define application types for different video outputs
class AppType(enum.Enum):
    LEFT_AND_RIGHT = 1    # Export LEFT and RIGHT views
    LEFT_AND_DEPTH = 2    # Export LEFT view and DEPTH view
    LEFT_AND_DEPTH_16 = 3 # Export LEFT view and 16-bit DEPTH view

# Function to calculate the average frame rate of an SVO file
def calculate_average_frame_rate(svo_path):
    # Initialize ZED camera parameters
    # These parameters are used to configure the ZED camera
    # for reading the SVO file
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_path)
    # Disable real-time mode for conversion
    # This mode is used when capturing frames in real-time
    # but we are not capturing frames in real-time, so we disable it
    init_params.svo_real_time_mode = False

    # Create a ZED camera object
    # This object is used to interact with the ZED camera
    zed = sl.Camera()
    # Try to open the SVO file using the specified parameters
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        # If the SVO file cannot be opened, print an error message and return None
        print("Failed to open SVO file:", svo_path)
        return None

    # Get the total number of frames in the SVO file
    # This function returns the number of frames in the SVO file
    total_frames = zed.get_svo_number_of_frames()
    print(f"Total frames in the SVO file: {total_frames}")

    # Move to the first frame and get the timestamp
    # Move to the first frame in the SVO file
    zed.set_svo_position(0)
    # Try to grab the first frame
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Get the timestamp of the first frame
        start_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Start timestamp: {start_timestamp} microseconds")
    else:
        # If the first frame cannot be grabbed, print an error message and close the ZED camera
        print("Failed to grab the first frame.")
        zed.close()
        return None

    # Move to the last frame and get the timestamp
    # Move to the last frame in the SVO file
    zed.set_svo_position(total_frames - 2)
    # Try to grab the last frame
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Get the timestamp of the last frame
        end_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Last frame timestamp: {end_timestamp} microseconds")
    else:
        # If the last frame cannot be grabbed, print an error message and close the ZED camera
        print("Failed to grab the last frame.")
        zed.close()
        return None

    # Close the ZED camera
    # This function is used to close the ZED camera and release any resources
    zed.close()

    # Calculate the elapsed time between the first and last frames in seconds
    # Calculate the elapsed time by subtracting the start timestamp from the end timestamp
    # and then dividing the result by 1 million (to convert microseconds to seconds)
    elapsed_time = (end_timestamp - start_timestamp) / 1000000.0
    print(f"Elapsed time in seconds: {elapsed_time}")

    # Calculate the number of successfully captured frames
    # The number of successfully captured frames is the total number of frames minus one
    # because the last frame cannot be grabbed
    successfully_captured_frames = total_frames - 1
    print(f"Successfully captured frames: {successfully_captured_frames}")

    # Calculate average frame rate
    # Calculate the average frame rate by dividing the number of successfully captured frames
    # by the elapsed time
    if successfully_captured_frames > 0 and elapsed_time > 0:
        average_frame_rate = successfully_captured_frames / elapsed_time
    else:
        average_frame_rate = 0

    # Check if the calculated average frame rate is greater than zero
    # If the average frame rate is not greater than zero, print an error message and return None
    if average_frame_rate <= 0:
        print("Calculated average frame rate is not greater than zero.")
        return None

    # Print the calculated average frame rate
    print("Average Frame Rate: ", average_frame_rate)

    # Return the calculated average frame rate
    return average_frame_rate

# Main function
def main():
    # Get input parameters from command line
    folder_path = opt.folder_path
    
    # Find all .svo2 files in the specified folder
    # Sort the .svo2 files to ensure consistent ordering
    svo_files = sorted(Path(folder_path).rglob("*.svo2"))
    if not svo_files:
        print("No .svo2 files found in the specified folder.")
        exit()

    # Set application type based on mode input
    # The application type determines the type of image sequence to export
    app_type = AppType.LEFT_AND_RIGHT
    #if opt.mode == 1 or opt.mode == 3:
        #app_type = AppType.LEFT_AND_DEPTH
    #if opt.mode == 4:
        #app_type = AppType.LEFT_AND_DEPTH_16

    # Get the file paths
    current_folder_name = os.path.basename(folder_path)
    output_avi_path = os.path.join(folder_path, f"{current_folder_name}.avi")
    audio_file_path = os.path.join(folder_path, "audio_recording.wav")
    output_final_video_path = os.path.join(folder_path, f"{current_folder_name}_with_audio.mp4")

    # Calculate average frame rate based on the first SVO file
    # The average frame rate is used to set the frame rate of the output AVI file
    average_frame_rate = calculate_average_frame_rate(str(svo_files[0]))
    if average_frame_rate is None:
        print("Failed to calculate average frame rate.")
        exit()

    # Write average frame rate to metadata JSON file
    # The metadata JSON file is used to store information about the export process
    metadata = {"average_frame_rate": average_frame_rate, "seconds": [], "frames": []}
    metadata_path = os.path.join(folder_path, "metadata.json")
    with open(metadata_path, "w") as json_file:
        json.dump(metadata, json_file)

    # Create ZED objects for each SVO file
    # Initialize each ZED camera with the SVO file
    zeds = [sl.Camera() for _ in svo_files]
    init_params = sl.InitParameters()
    rt_param = sl.RuntimeParameters()

    for zed, svo_path in zip(zeds, svo_files):
        init_params.set_from_svo_file(str(svo_path))
        init_params.svo_real_time_mode = False
        init_params.coordinate_units = sl.UNIT.MILLIMETER
        init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE

        if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
            print("Failed to open SVO file:", svo_path)
            exit()

    # Get image size from the first camera
    image_size = zeds[0].get_camera_information().camera_configuration.resolution
    width = image_size.width
    height = image_size.height
    width_sbs = width * len(svo_files)

    # Prepare a side-by-side image container
    # This container will hold the images from each camera
    svo_image_sbs_rgba = np.zeros((height, width_sbs, 4), dtype=np.uint8)

    # Prepare single image containers for each camera
    # These containers will hold the images retrieved from each camera
    left_images = [sl.Mat() for _ in svo_files]
    right_images = [sl.Mat() for _ in svo_files]
    depth_images = [sl.Mat() for _ in svo_files]

    # Create video writer with the calculated average frame rate
    # The video writer is used to write the images to the output AVI file
    video_writer = cv2.VideoWriter(output_avi_path,
                                   cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'),
                                   average_frame_rate,
                                   (width_sbs, height))
    if not video_writer.isOpened():
        print("OpenCV video writer cannot be opened. Please check the .avi file path and write permissions.")
        for zed in zeds:
            zed.close()
        exit()

    # Get the total number of frames in the shortest SVO file
    # The total number of frames is used to create a progress bar
    total_frames = min(zed.get_svo_number_of_frames() for zed in zeds)

    # Start SVO conversion to AVI
    print("Converting SVO files... Use Ctrl-C to interrupt conversion.")

    current_frame = 0
    while True:
        end_of_files = True
        for idx, zed in enumerate(zeds):
            err = zed.grab(rt_param)
            if err == sl.ERROR_CODE.SUCCESS:
                end_of_files = False
                zed.retrieve_image(left_images[idx], sl.VIEW.LEFT)

                if app_type == AppType.LEFT_AND_RIGHT:
                    zed.retrieve_image(right_images[idx], sl.VIEW.RIGHT)
                elif app_type == AppType.LEFT_AND_DEPTH:
                    zed.retrieve_image(right_images[idx], sl.VIEW.DEPTH)
                elif app_type == AppType.LEFT_AND_DEPTH_16:
                    zed.retrieve_measure(depth_images[idx], sl.MEASURE.DEPTH)

                # Copy the retrieved image data to the side-by-side container
                svo_image_sbs_rgba[0:height, idx*width:(idx+1)*width, :] = left_images[idx].get_data()

        if end_of_files:
            break

        # Convert RGBA image to RGB format for OpenCV
        # The RGBA image is converted to RGB format to match the expected format for the video writer
        ocv_image_sbs_rgb = cv2.cvtColor(svo_image_sbs_rgba, cv2.COLOR_RGBA2RGB)
        # Write the frame to the video file
        video_writer.write(ocv_image_sbs_rgb)

        # Update progress bar
        current_frame += 1
        progress_bar(current_frame, total_frames)

    # Close the video writer
    video_writer.release()
    for zed in zeds:
        zed.close()

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
    # Argument parser for command line options
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    #parser.add_argument('--mode', type=int, required=True, help=" Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
    parser.add_argument('--folder_path', type=str, required=True, help='Path to the folder containing .svo2 files')
    opt = parser.parse_args()
    
    # Validate the mode input
    #if opt.mode > 4 or opt.mode < 0:
        #print("Mode should be between 0 and 4 included. \n Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
        #exit()
    
    # Validate the folder path
    if not os.path.isdir(opt.folder_path):
        print("--folder_path parameter should be an existing directory but is not: ", opt.folder_path)
        exit()
    
    # Run the main function
    main()
