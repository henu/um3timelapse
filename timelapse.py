#!/usr/bin/python3
import os
import argparse
from requests import exceptions
from tempfile import mkdtemp
from time import sleep
from urllib.request import urlopen
from um3api import Ultimaker3
import json
import math

cliParser = argparse.ArgumentParser(description=
			'Creates a time lapse video from the onboard camera on your Ultimaker 3.')
cliParser.add_argument('HOST', type=str,
			help='IP address of the Ultimaker 3')
cliParser.add_argument('POST_SEC', type=float,
			help='Seconds of postroll, or how much time to capture after the print is completed.')
cliParser.add_argument('OUTFILE', type=str,
			help='Name of the video file to create. Recommended formats are .mkv or .mp4.')
options = cliParser.parse_args()

imgurl = "http://" + options.HOST + ":8080/?action=snapshot"

api = Ultimaker3(options.HOST, "Timelapse")
#api.loadAuth("auth.data")

def printing():
	status = None
	# If the printer gets disconnected, retry indefinitely
	while status == None:
		try:
			status = api.get("api/v1/printer/status").json()
			if status == 'printing':
				state = api.get("api/v1/print_job/state").json()
				if state == 'wait_cleanup':
					return False
				else:
					return True
			else:
				return False
		except exceptions.ConnectionError as err:
			status = None
			print_error(err)

def progress():
	p = None
	# If the printer gets disconnected, retry indefinitely
	while p == None:
		try:
			p = api.get("api/v1/print_job/progress").json() * 100
			return "%05.2f %%" % (p)
		except exceptions.ConnectionError as err:
			print_error(err)

def print_error(err):
	print("Connection error: {0}".format(err))
	print("Retrying")
	print()
	sleep(1)

def location_check(json_object, variant):
	x = json_object["x"]
	y = json_object["y"]
	if variant == "Ultimaker 3":
		if math.fabs(x-209) <= 2: #if the absolute value of x minus a number is less than or equal to 2
			if math.fabs(x-193) <= 2:
				return True
	elif variant == "Ultimaker S5": 
		if x == 330:
			if y == 219:
				return True

def get_variant():
	variant = api.get("api/v1/system/variant").json()
	return variant


tmpdir = mkdtemp()
filenameformat = os.path.join(tmpdir, "%05d.jpg")
print(":: Saving images to",tmpdir)

if not os.path.exists(tmpdir):
	os.makedirs(tmpdir)

print(":: Getting machine type")
variant = get_variant()
print(":: Found", variant)

print(":: Waiting for print to start")
while not printing():
	sleep(1)
print(":: Printing")

count = 0

while printing():
	count += 1
	response = urlopen(imgurl)
	filename = filenameformat % count
	f = open(filename,'bw')
	f.write(response.read())
	f.close
	print("Print progress: %s Image: %05i" % (progress(), count), end='\r')
	# sleep(options.DELAY)
	#sleep while printing a layer, wait for extruder position change
	while not location_check(api.get("api/v1/printer/heads/0/position").json(), variant) and printing(): #location check should detect when printcore 2 is lifted back up
		sleep(1)
	sleep(5) # I think this is necessary because of the way the printer cools down and reheats the print cores between switching. To prevent taking multiple pictures of the same layer.

#caputre a few frames of postroll
print()
print(":: Printing Completed or Cancelled") #maybe I should write some code to detect when a print was cancelled
post_frames = 30 * options.POST_SEC
for x in range(0, int(post_frames)):
	count += 1
	response = urlopen(imgurl)
	filename = filenameformat % count
	f = open(filename,'bw')
	f.write(response.read())
	f.close
	print("Post-Print Capture progress: %05i Image: %05i" % (x, count), end='\r')
	sleep(0.1)

print()
print(":: Encoding video")
ffmpegcmd = "ffmpeg -r 30 -i " + filenameformat + " -vcodec libx264 -preset veryslow -crf 18 -loglevel panic " + options.OUTFILE
print(ffmpegcmd)
os.system(ffmpegcmd)
print(":: Done!")