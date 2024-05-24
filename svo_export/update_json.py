import json

# Function to read metadata JSON file and get the average frame rate
def get_average_frame_rate_from_metadata(metadata_file):
    with open(metadata_file, "r") as json_file:
        metadata = json.load(json_file)
        return metadata.get("average_frame_rate"), metadata.get("data", {})

# Function to convert seconds to frame numbers using the average frame rate
def seconds_to_frames(seconds, average_frame_rate):
    return [int(sec * average_frame_rate) for sec in seconds]

# Function to write metadata, seconds, and frame numbers into the JSON file
def write_data_to_json(metadata_file, average_frame_rate, seconds, frames):
    data = {"average_frame_rate": average_frame_rate, "seconds": seconds, "frames": frames}
    with open(metadata_file, "w") as json_file:
        json.dump(data, json_file, indent=4)

def main():
    metadata_file = "metadata.json"
    average_frame_rate, existing_data = get_average_frame_rate_from_metadata(metadata_file)
    if average_frame_rate is None:
        print("Failed to read average frame rate from metadata file.")
        return

    # Prompt user to input seconds separated by spaces
    seconds_input = input("Enter a list of seconds separated by spaces: ")
    seconds_list = [int(sec) for sec in seconds_input.split()]

    # Convert seconds to frame numbers
    frames_list = seconds_to_frames(seconds_list, average_frame_rate)

    # Update existing data with new data
    existing_data["seconds"] = seconds_list
    existing_data["frames"] = frames_list

    # Write metadata, seconds, and frame numbers into JSON file
    write_data_to_json(metadata_file, average_frame_rate, seconds_list, frames_list)
    print("Data has been written to", metadata_file)

if __name__ == "__main__":
    main()
