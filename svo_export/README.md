# SVO Export and Metadata Management

## Overview

This folder contains two main scripts:

1. `svo_export.py`: This script reads SVO files, calculates the real frame rate to compensate for frame drops, merges multiple SVO files into a single AVI file, and creates a `metadata.json` file with the average frame rate and empty lists for seconds and frames. It can also convert a SVO in the following png image sequences: LEFT+RIGHT, LEFT+DEPTH_VIEW, and LEFT+DEPTH_16Bit.
2. `update_metadata.py`: This script processes the `metadata.json` file to ensure the lengths of the seconds and frames lists are equal. If not, it converts the timestamps to frame numbers using the average frame rate.

## Getting Started
 - Get the latest [ZED SDK](https://www.stereolabs.com/developers/release/) and [pyZED Package](https://www.stereolabs.com/docs/app-development/python/install/)
 - Check the [Documentation](https://www.stereolabs.com/docs/)

## Running `svo_export.py`

To run the `svo_export.py` script, use the following command:

```bash
python svo_export.py --mode <mode> --folder_path <folder_path>
```
Arguments: 
  - --mode Mode 0 is to export LEFT+RIGHT AVI. <br /> Mode 1 is to export LEFT+DEPTH_VIEW Avi. <br /> Mode 2 is to export LEFT+RIGHT image sequence. <br /> Mode 3 is to export LEFT+DEPTH_View image sequence. <br /> Mode 4 is to export LEFT+DEPTH_16BIT image sequence.
  - --folder_path Path to an existing folder containing two .svo files 

### Features
  - Calculate Real Frame Rate: Computes the real frame rate from SVO files to compensate for frame drops.
  - Merge SVO Files: Merges multiple SVO files into a single AVI file.
  - Metadata Generation: Creates a metadata.json file with the average frame rate and empty lists for seconds and frames.

Modes:  
 - Export .svo file to LEFT+RIGHT .avi
 - Export .svo file to LEFT+DEPTH_VIEW .avi
 - Export .svo file to LEFT+RIGHT image sequence
 - Export .svo file to LEFT+DEPTH_View image sequence
 - Export .svo file to LEFT+DEPTH_16BIT image sequence
Examples : 
```
python svo_export.py --mode 0 --folder_path <folder_path>
python svo_export.py --mode 1 --folder_path <folder_path>
python svo_export.py --mode 2 --folder_path <folder_path>
python svo_export.py --mode 3 --folder_path <folder_path>
python svo_export.py --mode 4 --folder_path <folder_path>
```

## Running `update_metadata.py`

To run the `update_metadata.py` script, use the following command:

```bash
python update_metadata.py --folder_path <folder_path>
```

Arguments:
  -  --folder_path: Path to the folder containing metadata.json.

### Features
  - Metadata Validation: Checks if the lengths of seconds and frames lists are equal.
  - Timestamp Conversion: Converts timestamps to frame numbers using the average frame rate if the lists are not equal.

## Support
If you need assistance go to their Community site at https://community.stereolabs.com/
