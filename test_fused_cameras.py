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
   This sample shows how to detect a human bodies and draw their 
   modelised skeleton in an OpenGL window
"""
import cv2
import sys
import pyzed.sl as sl
import time
import ogl_viewer.viewer as gl
import numpy as np
import json
import argparse
from signal import signal, SIGINT
# Handler to deal with CTRL+C properly

zcameras = []
body_json = []


def handler(signal_received, frame):
    global zcameras, body_json
    print("got sigint, shutting cameras")
    for cam in zcameras:
        cam.disable_recording()
        cam.close()
    print("dumping json")
    with open('body_tracking.json', 'w') as outfile:
        json.dump(body_json, outfile)
    print("exiting")
    sys.exit(0)

signal(SIGINT, handler)

def serialize_body(body, timestamp):
    return {
        "id": body.unique_object_id,
        "ts": timestamp,
        "keypoint": body.keypoint.tolist(),
        "confidence": body.confidence,
        # "tracking_state": body.tracking_state,
        # "action_state": body.action_state
    }

def main():
    global zcameras, body_json
    if len(sys.argv) < 2:
        print("This sample displays the fused body tracking of multiple cameras.")
        print("It needs a Localization file in input. Generate it with ZED 360.")
        print("The cameras can either be plugged to your devices, or already running on the local network.")
        exit(1)

    filepath = sys.argv[1]
    fusion_configurations = sl.read_fusion_configuration_file(filepath, sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP, sl.UNIT.METER)
    if len(fusion_configurations) <= 0:
        print("Invalid file.")
        exit(1)

    senders = {}
    network_senders = {}
    

    # common parameters
    init_params = sl.InitParameters()
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_params.coordinate_units = sl.UNIT.METER
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 30
    

    communication_parameters = sl.CommunicationParameters()
    communication_parameters.set_for_shared_memory()

    positional_tracking_parameters = sl.PositionalTrackingParameters()
    positional_tracking_parameters.set_as_static = True

    body_tracking_parameters = sl.BodyTrackingParameters()
    body_tracking_parameters.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
    body_tracking_parameters.body_format = sl.BODY_FORMAT.BODY_34
    body_tracking_parameters.enable_body_fitting = True
    body_tracking_parameters.enable_tracking = True

    for conf in fusion_configurations:
        print("Try to open ZED", conf.serial_number)
        init_params.input = sl.InputType()
        # network cameras are already running, or so they should
        if conf.communication_parameters.comm_type == sl.COMM_TYPE.LOCAL_NETWORK:
            network_senders[conf.serial_number] = conf.serial_number

        # local camera needs to be run form here, in the same process than the fusion
        else:
            init_params.input = conf.input_type
            
            senders[conf.serial_number] = sl.Camera()

            init_params.set_from_serial_number(conf.serial_number)
            status = senders[conf.serial_number].open(init_params)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error opening the camera", conf.serial_number, status)
                del senders[conf.serial_number]
                continue

            status = senders[conf.serial_number].enable_positional_tracking(positional_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the positional tracking of camera", conf.serial_number)
                del senders[conf.serial_number]
                continue

            status = senders[conf.serial_number].enable_body_tracking(body_tracking_parameters)
            if status != sl.ERROR_CODE.SUCCESS:
                print("Error enabling the body tracking of camera", conf.serial_number)
                del senders[conf.serial_number]
                continue

            senders[conf.serial_number].start_publishing(communication_parameters)

        print("Camera", conf.serial_number, "is open")
    
    if len(senders) + len(network_senders) < 1:
        print("No enough cameras")
        exit(1)

    print("Senders started, running the fusion...")
        
    init_fusion_parameters = sl.InitFusionParameters()
    init_fusion_parameters.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init_fusion_parameters.coordinate_units = sl.UNIT.METER
    init_fusion_parameters.output_performance_metrics = False
    init_fusion_parameters.verbose = True
    communication_parameters = sl.CommunicationParameters()
    fusion = sl.Fusion()
    camera_identifiers = []

    fusion.init(init_fusion_parameters)
        
    print("Cameras in this configuration : ", len(fusion_configurations))

    # warmup ###recording code
    #parser = argparse.ArgumentParser()
    #parser.add_argument('--output_svo_file', type=str, help='Path to the SVO file that will be written', required=True)
    #opt = parser.parse_args()
    bodies = sl.Bodies()    


    for serial in senders:
        # senders is a dict keyed on camera serial number, so camera object is at senders[serial]

        # add camera to global list to close when shutdown
        zcameras.append(senders[serial])
        
        # name the svo file according to the camera serial number f"{serial}.svo
        recording_param = sl.RecordingParameters(f"{serial}_experiment_suryansh_1.svo", sl.SVO_COMPRESSION_MODE.H265) # Enable recording with the filename specified in argument

        # get a handle for the camera object
        zed = senders[serial]

        # start recording for this one specific camera
        err = zed.enable_recording(recording_param)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Error enabling recording on {serial}: {err}")
            sys.exit(1)
        print ('both cameraas recording')    
        # test out one body retrieval
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_bodies(bodies)
        


    for i in range(0, len(fusion_configurations)):
        conf = fusion_configurations[i]
        uuid = sl.CameraIdentifier()
        uuid.serial_number = conf.serial_number
        print("Subscribing to", conf.serial_number, conf.communication_parameters.comm_type)

        status = fusion.subscribe(uuid, conf.communication_parameters, conf.pose)
        if status != sl.FUSION_ERROR_CODE.SUCCESS:
            print("Unable to subscribe to", uuid.serial_number, status)
        else:
            camera_identifiers.append(uuid)
            print("Subscribed.")

    if len(camera_identifiers) <= 0:
        print("No camera connected.")
        sys.exit(1)

    body_tracking_fusion_params = sl.BodyTrackingFusionParameters()
    body_tracking_fusion_params.enable_tracking = True
    body_tracking_fusion_params.enable_body_fitting = False
    
    fusion.enable_body_tracking(body_tracking_fusion_params)

    rt = sl.BodyTrackingFusionRuntimeParameters()
    rt.skeleton_minimum_allowed_keypoints = 7
    #viewer = gl.GLViewer()
   # viewer.init()

    # Create ZED objects filled in the main loop
    bodies = sl.Bodies()
    single_bodies = [sl.Bodies]


    while True:
        for serial in senders:
           zed = senders[serial]
           if zed.grab() == sl.ERROR_CODE.SUCCESS:
               zed.retrieve_bodies(bodies)

        if fusion.process() == sl.FUSION_ERROR_CODE.SUCCESS:
            
            # Retrieve detected objects
            fusion.retrieve_bodies(bodies, rt)
            body_json.append([serialize_body(b, bodies.timestamp.get_milliseconds()) for b in bodies.body_list])
            # for debug, you can retrieve the data send by each camera, as well as communication and process stat just to make sure everything is okay
            # for cam in camera_identifiers:
            #     fusion.retrieveBodies(single_bodies, rt, cam); 
            #viewer.update_bodies(bodies)
            
    for sender in senders:
        senders[sender].close()


    #viewer.exit()

if __name__=='__main__':
    main()
