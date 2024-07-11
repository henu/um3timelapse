#!/usr/bin/python3
import os
import argparse
from requests import exceptions
from tempfile import mkdtemp
from urllib.request import urlopen
from um3api import Ultimaker3
import json
import math
import time
import re
import collections
from PIL import Image

cliParser = argparse.ArgumentParser(
    description='Creates a time lapse video from the onboard camera on your Ultimaker 3.')
cliParser.add_argument(
    'HOST', type=str, help='IP address of the Ultimaker 3')
cliParser.add_argument(
    'POST_SEC', type=float, help='Seconds of postroll, or how much time to capture after the print is completed.')
cliParser.add_argument(
    'OUTFILE', type=str, help='Name of the video file to create. Recommended formats are .mkv or .mp4.')
options = cliParser.parse_args()

imgurl = "http://" + options.HOST + ":8080/?action=snapshot"

api = Ultimaker3(options.HOST, "Timelapse")


def get_status():
    # If the printer gets disconnected, retry indefinitely
    while True:
        try:
            status = api.get("api/v1/printer/status").json()
            if status == 'idle':
                return 'idle'
            elif status == 'printing':
                state = api.get("api/v1/print_job/state").json()
                if state == 'none':
                    time.sleep(0.25)
                    continue
                # TODO: Is there any state I missed?
                if state not in ['pre_print', 'printing', 'post_print', 'wait_cleanup', 'wait_user_action', 'message']:
                    raise Exception(f'Unknown printing state \"{state}\"!')
                return state
            else:
                raise Exception(f'Unknown printer status \"{status}\"!')
        except exceptions.ConnectionError as err:
            print_error(err)
            time.sleep(1)


def print_error(err):
    print("Connection error: {0}".format(err))
    print("Retrying")
    print()


tmpdir = mkdtemp()
filenameformat = os.path.join(tmpdir, "%05d.jpg")
print(":: Saving images to", tmpdir)

if not os.path.exists(tmpdir):
    os.makedirs(tmpdir)

print(":: Waiting for print to start")
while get_status() != 'printing':
    time.sleep(1)
print(":: Printing")

while get_status() == 'printing':
    # Take screenshot
    response = urlopen(imgurl)

    # Use current time and print head to form a filename that contains all the necessary data
    printhead_pos = api.get("api/v1/printer/heads/0/position").json()
    filename = '{}_{}_{}_{}.jpg'.format(
        time.time(),
        printhead_pos['x'],
        printhead_pos['y'],
        printhead_pos['z'],
    )

    # Write screenshot to temporary directory
    with open(os.path.join(tmpdir, filename), 'wb') as f:
        f.write(response.read())

    time.sleep(0.5)

# Iterate all captured frames, and group them by their layer
print(":: Blending captured images into frames")
# First collect all images from same layer
IMAGE_FILENAME_RE = re.compile('^(?P<timestamp>[\\d\\.]+)_(?P<x>[\\d\\.]+)_(?P<y>[\\d\\.]+)_(?P<z>[\\d\\.]+).jpg$')
images_by_layers = collections.defaultdict(list)
for image_path in os.listdir(tmpdir):
    image_match = IMAGE_FILENAME_RE.match(image_path)
    if image_match:
        layer_key = str(round(100 * float(image_match.groupdict()['z']))).zfill(10)
        images_by_layers[layer_key].append(image_path)

# Convert multiple images in layers into single frames
frame_num = 0
for layer_key, layer_images in sorted(images_by_layers.items()):
    # Open all images with PIL and blend them into one
    final_image = Image.open(os.path.join(tmpdir, layer_images[0]))
    for layer_image_i in range(1, len(layer_images)):
        with Image.open(os.path.join(tmpdir, layer_images[layer_image_i])) as image:
            final_image = Image.blend(final_image, image, 1 / (layer_image_i + 1))
    # Write frame to disk
    final_image.save(filenameformat % frame_num)
    frame_num += 1

print()
print(":: Encoding video")
ffmpegcmd = "ffmpeg -r 30 -i " + filenameformat + " -vcodec libx264 -preset veryslow -crf 18 -loglevel panic " + options.OUTFILE
print(ffmpegcmd)
os.system(ffmpegcmd)
print(":: Done!")
