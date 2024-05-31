import json
import os
import argparse

# Function to read metadata JSON file and get the average frame rate
def get_average_frame_rate_from_metadata(metadata_file):
    """
    This function reads the metadata file, which contains the average frame rate,
    and returns the average frame rate and the entire metadata.
    
    Parameters:
    - metadata_file (str): The path to the metadata file.
    
    Returns:
    - average_frame_rate (float): The average frame rate.
    - metadata (dict): The entire metadata.
    """
    
    # Open the metadata file in read mode
    with open(metadata_file, "r") as json_file:
        # Read the JSON data from the file and store it in the metadata variable
        metadata = json.load(json_file)
        
        # Extract the average frame rate from the metadata
        average_frame_rate = metadata.get("average_frame_rate")
        
        # If the average frame rate is not found in the metadata, return None
        if average_frame_rate is None:
            return None, None
        
        # Return the average frame rate and the entire metadata
        return average_frame_rate, metadata

# Function to convert seconds to frame numbers using the average frame rate
def seconds_to_frames(seconds, average_frame_rate):
    """
    This function converts a list of seconds to a list of frames using the average frame rate.
    
    Parameters:
    - seconds (list): A list of seconds to convert to frames.
    - average_frame_rate (float): The average frame rate used for the conversion.
    
    Returns:
    - frames (list): A list of frames corresponding to the given seconds.
    """
    
    # Initialize an empty list to store the frames
    frames = []
    
    # Iterate over each second in the seconds list
    for sec in seconds:
        # Calculate the frame number for the current second using the average frame rate
        frame = int(sec * average_frame_rate)
        
        # Append the frame to the frames list
        frames.append(frame)
    
    # Return the list of frames
    return frames

# Function to write metadata, seconds, and frame numbers into the JSON file
def write_data_to_json(metadata_file, metadata):
    """
    This function writes the updated metadata to a JSON file.
    
    Parameters:
    - metadata_file (str): The path to the JSON file to write to.
    - metadata (dict): The updated metadata to write to the file.
    """
    
    # Open the JSON file in write mode
    # This mode opens the file for writing and creates the file if it does not exist
    # The file is opened in binary mode because the file is being written in JSON format
    # The 'with' statement is used to ensure that the file is properly closed
    with open(metadata_file, "w") as json_file:
        # Dump the updated metadata to the JSON file
        # The 'indent' parameter is used to format the JSON output with indentation
        # This makes the JSON output more readable
        # The 'json_file' object is the file object that was opened earlier
        # The 'metadata' object is the updated metadata that needs to be written to the file
        json.dump(metadata, json_file, indent=4)

def main():
    # Parse command line arguments to get the folder path where metadata.json is located
    parser = argparse.ArgumentParser(description="Process metadata JSON file in the specified folder.")
    parser.add_argument("--folder_path", type=str, required=True, help="Path to the folder containing metadata.json")
    args = parser.parse_args()

    # Construct the full path to the metadata.json file
    metadata_file = os.path.join(args.folder_path, "metadata.json")
    
    # Check if the metadata file exists at the specified path
    if not os.path.exists(metadata_file):
        # If the file does not exist, print an error message and exit
        print(f"Metadata file not found at {metadata_file}")
        return

    # Read the average frame rate and metadata from the JSON file
    # The function reads the average frame rate from the metadata file and returns it along with the entire metadata
    # The average frame rate is used to calculate the frame numbers from the given seconds
    # The metadata also contains other information such as the seconds and frames lists
    average_frame_rate, metadata = get_average_frame_rate_from_metadata(metadata_file)
    
    # If the average frame rate is not found in the metadata, print an error message and exit
    if average_frame_rate is None:
        print("Failed to read average frame rate from metadata file.")
        return

    # Get the list of seconds and frames from the metadata
    # The seconds list contains the time points in seconds at which the frames were recorded
    # The frames list contains the corresponding frame numbers
    seconds_list = metadata.get("seconds", [])
    frames_list = metadata.get("frames", [])

    # Check if the lengths of the seconds list and frames list are equal
    # If they are not equal, it means that the frames list needs to be recomputed
    if len(seconds_list) != len(frames_list):
        # Print a message to indicate that the lengths are not equal and that the frames list will be recomputed
        print("Mismatch in lengths of 'seconds' and 'frames'. Recomputing frames list.")
        
        # Recompute the frames list using the seconds list and the average frame rate
        # The function takes the seconds list and the average frame rate as input and returns the corresponding frame numbers
        frames_list = seconds_to_frames(seconds_list, average_frame_rate)
        
        # Update the frames list in the metadata
        metadata["frames"] = frames_list

    # Write the updated metadata back to the JSON file
    # The function opens the metadata file in write mode and writes the updated metadata to the file
    write_data_to_json(metadata_file, metadata)
    
    # Print a message to indicate that the data has been written to the metadata file
    print("Data has been written to", metadata_file)

if __name__ == "__main__":
    main()
