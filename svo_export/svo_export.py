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
import numpy as np
import cv2
from pathlib import Path
import enum
import argparse
import os
import time
import json

def progress_bar(percent_done, bar_length=50):
    #Display a progress bar
    done_length = int(bar_length * percent_done / 100)
    bar = '=' * done_length + '-' * (bar_length - done_length)
    sys.stdout.write('[%s] %i%s\r' % (bar, percent_done, '%'))
    sys.stdout.flush()

class AppType(enum.Enum):
    LEFT_AND_RIGHT = 1
    LEFT_AND_DEPTH = 2
    LEFT_AND_DEPTH_16 = 3

def calculate_average_frame_rate(svo_path):
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_path)
    init_params.svo_real_time_mode = False  # Don't convert in realtime

    zed = sl.Camera()
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open SVO file:", svo_path)
        return None
    
    # Get the total number of frames
    total_frames = zed.get_svo_number_of_frames()
    print(f"Total frames in the SVO file: {total_frames}")

    # Go to the first frame and get the timestamp
    zed.set_svo_position(0)
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        start_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Start timestamp: {start_timestamp} microseconds")
    else:
        print("Failed to grab the first frame.")
        zed.close()
        return None
    
    # Go to the last frame and get the timestamp
    zed.set_svo_position(total_frames - 2)
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        end_timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_microseconds()
        print(f"Last frame timestamp: {end_timestamp} microseconds")
    else:
        print("Failed to grab the last frame.")
        zed.close()
        return None

    # Close the camera
    zed.close()

    # Calculate the real average frame rate
    elapsed_time = (end_timestamp - start_timestamp) / 1000000.0  # Convert microseconds to seconds
    print(f"Elapsed time in seconds: {elapsed_time}")
    successfully_captured_frames = total_frames
    print(f"Successfully captured frames: {successfully_captured_frames}")

    if successfully_captured_frames > 0 and elapsed_time > 0:
        average_frame_rate = successfully_captured_frames / elapsed_time
    else:
        average_frame_rate = 0

    if average_frame_rate <= 0:
        print("Calculated average frame rate is not greater than zero.")
        return None

    print("Average Frame Rate: ", average_frame_rate)
    
    return average_frame_rate

def main():
    # Get input parameters
    svo_input_path = opt.input_svo_file
    
    # Extract directory and filename from input_svo_file
    directory, filename = os.path.split(svo_input_path)
    
    # Construct output AVI file path
    output_avi_path = os.path.join(directory, os.path.splitext(filename)[0] + ".avi")
    
    app_type = AppType.LEFT_AND_RIGHT
    if opt.mode == 1 or opt.mode == 3:
        app_type = AppType.LEFT_AND_DEPTH
    if opt.mode == 4:
        app_type = AppType.LEFT_AND_DEPTH_16

    # Calculate average frame rate
    average_frame_rate = calculate_average_frame_rate(svo_input_path)
    if average_frame_rate is None:
        print("Failed to calculate average frame rate.")
        exit()

    # Write average frame rate to metadata JSON file
    metadata = {"average_frame_rate": average_frame_rate}
    metadata_path = os.path.join(directory, "metadata.json")
    with open(metadata_path, "w") as json_file:
        json.dump(metadata, json_file)

    # Specify SVO path parameter
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_input_path)
    init_params.svo_real_time_mode = False  # Don't convert in realtime
    init_params.coordinate_units = sl.UNIT.MILLIMETER  # Use milliliter units (for depth measurements)
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE  # Set the depth mode for performance

    # Create ZED objects
    zed = sl.Camera()

    # Open the SVO file specified as a parameter
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open SVO file:", svo_input_path)
        exit()
    
    # Get image size
    image_size = zed.get_camera_information().camera_configuration.resolution
    width = image_size.width
    height = image_size.height
    width_sbs = width * 2
    
    # Prepare side by side image container equivalent to CV_8UC4
    svo_image_sbs_rgba = np.zeros((height, width_sbs, 4), dtype=np.uint8)

    # Prepare single image containers
    left_image = sl.Mat()
    right_image = sl.Mat()
    depth_image = sl.Mat()

    # Create video writer with calculated average frame rate
    video_writer = cv2.VideoWriter(output_avi_path,
                                   cv2.VideoWriter_fourcc('M', '4', 'S', '2'),
                                   average_frame_rate,
                                   (width_sbs, height))
    if not video_writer.isOpened():
        print("OpenCV video writer cannot be opened. Please check the .avi file path and write permissions.")
        zed.close()
        exit()

    rt_param = sl.RuntimeParameters()

    # Start SVO conversion to AVI/SEQUENCE
    print("Converting SVO... Use Ctrl-C to interrupt conversion.")

    nb_frames = zed.get_svo_number_of_frames()

    while True:
        err = zed.grab(rt_param)
        if err == sl.ERROR_CODE.SUCCESS:
            svo_position = zed.get_svo_position()

            # Retrieve SVO images
            zed.retrieve_image(left_image, sl.VIEW.LEFT)

            if app_type == AppType.LEFT_AND_RIGHT:
                zed.retrieve_image(right_image, sl.VIEW.RIGHT)
            elif app_type == AppType.LEFT_AND_DEPTH:
                zed.retrieve_image(right_image, sl.VIEW.DEPTH)
            elif app_type == AppType.LEFT_AND_DEPTH_16:
                zed.retrieve_measure(depth_image, sl.MEASURE.DEPTH)

            # Copy the left image to the left side of SBS image
            svo_image_sbs_rgba[0:height, 0:width, :] = left_image.get_data()

            # Copy the right image to the right side of SBS image
            svo_image_sbs_rgba[0:, width:, :] = right_image.get_data()

            # Convert SVO image from RGBA to RGB
            ocv_image_sbs_rgb = cv2.cvtColor(svo_image_sbs_rgba, cv2.COLOR_RGBA2RGB)

            # Write the RGB image in the video
            video_writer.write(ocv_image_sbs_rgb)

            # Display progress
            progress_bar((svo_position + 1) / nb_frames * 100, 30)

        if err == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            progress_bar(100, 30)
            print("\nSVO end has been reached. Exiting now.")
            break

    # Close the video writer
    video_writer.release()

    zed.close()
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--mode', type=int, required=True, help=" Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
    parser.add_argument('--input_svo_file', type=str, required=True, help='Path to the .svo file')
    opt = parser.parse_args()
    if opt.mode > 4 or opt.mode < 0:
        print("Mode should be between 0 and 4 included. \n Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
        exit()
    if not opt.input_svo_file.endswith(".svo") and not opt.input_svo_file.endswith(".svo2"):
        print("--input_svo_file parameter should be a .svo file but is not : ", opt.input_svo_file, "Exit program.")
        exit()
    if not os.path.isfile(opt.input_svo_file):
        print("--input_svo_file parameter should be an existing file but is not : ", opt.input_svo_file,
              "Exit program.")
        exit()

    main()
