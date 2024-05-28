import json
import os
import argparse

# Function to read metadata JSON file and get the average frame rate
def get_average_frame_rate_from_metadata(metadata_file):
    # Open and read the JSON file
    with open(metadata_file, "r") as json_file:
        metadata = json.load(json_file)
        # Return the average frame rate and the entire metadata
        return metadata.get("average_frame_rate"), metadata

# Function to convert seconds to frame numbers using the average frame rate
def seconds_to_frames(seconds, average_frame_rate):
    # Convert each second value to frames using the average frame rate
    return [int(sec * average_frame_rate) for sec in seconds]

# Function to write metadata, seconds, and frame numbers into the JSON file
def write_data_to_json(metadata_file, metadata):
    # Open the JSON file in write mode and dump the updated metadata
    with open(metadata_file, "w") as json_file:
        json.dump(metadata, json_file, indent=4)

def main():
    # Set up argument parser to get folder path from command line arguments
    parser = argparse.ArgumentParser(description="Process metadata JSON file in the specified folder.")
    parser.add_argument("--folder_path", type=str, required=True, help="Path to the folder containing metadata.json")
    args = parser.parse_args()

    # Construct the full path to the metadata.json file
    metadata_file = os.path.join(args.folder_path, "metadata.json")
    
    # Check if the metadata file exists at the specified path
    if not os.path.exists(metadata_file):
        print(f"Metadata file not found at {metadata_file}")
        return

    # Read the average frame rate and metadata from the JSON file
    average_frame_rate, metadata = get_average_frame_rate_from_metadata(metadata_file)
    if average_frame_rate is None:
        print("Failed to read average frame rate from metadata file.")
        return

    # Get the seconds and frames lists from the metadata
    seconds_list = metadata.get("seconds", [])
    frames_list = metadata.get("frames", [])

    # Check if the length of seconds list is equal to the length of frames list
    if len(seconds_list) != len(frames_list):
        # If lengths are not equal, recompute the frames list
        print("Mismatch in lengths of 'seconds' and 'frames'. Recomputing frames list.")
        frames_list = seconds_to_frames(seconds_list, average_frame_rate)
        # Update the frames list in the metadata
        metadata["frames"] = frames_list

    # Write the updated metadata back to the JSON file
    write_data_to_json(metadata_file, metadata)
    print("Data has been written to", metadata_file)

# Entry point of the script
if __name__ == "__main__":
    main()
