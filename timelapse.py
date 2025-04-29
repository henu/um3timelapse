#!/usr/bin/python3
import os
import argparse
import datetime
from requests import exceptions
import tempfile
from urllib.request import urlopen
from um3api import Ultimaker3
import time
import re
import collections
from PIL import Image


# TODO: Remind user that firewall is needed to be turned off. Developer mode is not needed


def parse_args():

    args = argparse.ArgumentParser(
        description='Monitors your Ultimaker 3/S3 printer, and creates timelapse videos of all prints.'
    )
    args.add_argument('host', type=str, help='Hotsname or IP address of your printer')
    args.add_argument('directory', type=str, help='Directory where videos are stored.')

    return args.parse_args()


def get_status(api):
    # If the printer gets disconnected, retry indefinitely
    while True:
        try:
            status = api.get('api/v1/printer/status').json()
            if status == 'idle':
                return 'idle'
            elif status == 'printing':
                state = api.get('api/v1/print_job/state').json()
                if state == 'none':
                    time.sleep(0.25)
                    continue
                # TODO: Is there any state I missed?
                if state not in ['pre_print', 'printing', 'post_print', 'wait_cleanup', 'wait_user_action', 'message']:
                    raise Exception(f'Unknown printing state "{state}"!')
                return state
            else:
                raise Exception(f'Unknown printer status "{status}"!')
        except exceptions.ConnectionError as err:
            print(f'Connection error: {err}')
            print('Retrying...')
            time.sleep(1)


if __name__ == '__main__':

    options = parse_args()

    api = Ultimaker3(options.host, 'Timelapse')

    imgurl = f'http://{options.host}:8080/?action=snapshot'

    while True:

        # Wait until printing starts
        print('Waiting for new print to start')
        while get_status(api) != 'printing':
            time.sleep(1)
        print('Printing started!')

        print_started = datetime.datetime.now(datetime.timezone.utc)

        # Create a directory for storing frames
        with tempfile.TemporaryDirectory() as tmpdir:

            filenameformat = os.path.join(tmpdir, '%05d.jpg')

            print('Saving images to', tmpdir)

            # TODO: Check what happens when material runs out. Could we pause frame capturing during that time?
            while get_status(api) == 'printing':
                # Take screenshot
                response = urlopen(imgurl)

                # Use current time and print head to form a filename that contains all the necessary data
                printhead_pos = api.get('api/v1/printer/heads/0/position').json()
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

            # TODO: Do the video encoding in seprate thread, so we don't miss the next print!

            # Printing is now complete.  Iterate all captured frames, and group them by their layer
            print('Blending captured images into frames')
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

            print('Encoding video...')
            video_path = os.path.join(options.directory, 'print_{}.mp4'.format(print_started.isoformat()))
            ffmpegcmd = f'ffmpeg -r 30 -i {filenameformat} -vcodec libx264 -preset veryslow -crf 18 -loglevel panic "{video_path}"'
            os.system(ffmpegcmd)
            print('Done!')
