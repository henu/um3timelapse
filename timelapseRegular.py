#!/bin/python3
import os
import sys
import argparse
import math
import requests
from requests import exceptions
from tempfile import mkdtemp
from time import sleep
from urllib.request import urlopen

cliParser = argparse.ArgumentParser(description=
			'Creates a time lapse video from a mjpg-streamer camera.')
cliParser.add_argument('HOST', type=str,
			help='IP address of the camera')
cliParser.add_argument('PHOST', type=str,
			help='IP address of the Duet 3D printer board')
cliParser.add_argument('PASSWORD', type=str,
			help='Password of the Duet 3D printer board')
cliParser.add_argument('DELAY', type=float,
			help='Time between snapshots in seconds')
cliParser.add_argument('LENGTH', type=float,
			help='Time of the print in seconds')
cliParser.add_argument('OUTFILE', type=str,
			help='Name of the video file to create. Recommended formats are .mkv or .mp4.')
options = cliParser.parse_args()

imgurl = "http://" + options.HOST + ":8080/?action=snapshot"

def percent():
	r = requests.get('http://' + str(options.PHOST) + '/rr_connect?password=' + str(options.PASSWORD))
	percent = float(requests.get('http://' + str(options.PHOST) + '/rr_status?type=3').json()["fractionPrinted"])
	return percent

def printing():
	status = None
	# If the printer gets disconnected, retry indefinitely
	while status == None:
		r = requests.get('http://' + str(options.PHOST) + '/rr_connect?password=' + str(options.PASSWORD))
		status = requests.get('http://' + str(options.PHOST) + '/rr_status?type=3').json()["status"]
		if status == "P": # processing
			return True
		elif status == "I": # idle
			return False
		elif status == "D":	# Pausing / Decelerating
			return paused()
		elif status == "S":	# Paused / Stopped
			return paused()
		# elif status == "F":	# Flashing new firmware
		# 	return False
		# elif status == "O":	# Off
		# 	return False
		# elif status == "H":	# Halted
		# 	return False
		# elif status == "R":	# Resuming
		# 	return False
		# elif status == "M":	# Simulating
		# 	return False
		# elif status == "B":	# Busy
		# 	return False
		# elif status == "T":	# Changing tool
		# 	return False

def paused():
	while not status == "P": # Loop while paused and wait forever until we're printing again before returning True
		r = requests.get('http://' + str(options.PHOST) + '/rr_connect?password=' + str(options.PASSWORD))
		status = requests.get('http://' + str(options.PHOST) + '/rr_status?type=3').json()["status"]
		time.sleep(1)
	return True




tmpdir = mkdtemp()
filenameformat = os.path.join(tmpdir, "%05d.jpg")
print(":: Saving images to",tmpdir)

if not os.path.exists(tmpdir):
	os.makedirs(tmpdir)

print("How long do you want your timelapse to be? For example, if you enter \"10\" then you will get a 10 second video.")
video_length_input = int(input("How long do you want your timelapse to be? "))
print_time_input = int(input("How long is the print in seconds? "))

if not video_length_input and not print_time_input:
	print("Got bad response... quitting")
	sys.exit()

time_between_frames = print_time_input / (video_length_input*30)
new_delay = options.DELAY
new_length = options.LENGTH

if math.fabs(time_between_frames - options.DELAY) > 10:
	print("Warning, it looks like the input DELAY and the calculated delay are different.")
print("Do you want to use the command line DELAY or the calculated delay?")
print ("    Enter \"1\" for command line DELAY of " + str(options.DELAY))
print ("    Enter \"2\" for calculated delay of " + str(time_between_frames))
re = int(input("Response: "))
if re == 1:
	print("Using cmd line DELAY")
elif re == 2:
	print("Using calculated delay")
	new_delay = time_between_frames
	new_length = print_time_input
else:
	print("Got bad response... quitting")
	sys.exit()


print(":: Starting Timelapse")

count = 0

while printing(): 
	count += 1
	response = urlopen(imgurl)
	filename = filenameformat % count
	f = open(filename,'bw')
	f.write(response.read())
	f.close
	print("Print Progress: %05i Image: %05i" % (percent(), count), end='\r')
	sleep(new_delay)

print()
print(":: Print completed")
print(":: Encoding video")
ffmpegcmd = "ffmpeg -r 30 -i " + filenameformat + " -vcodec libx264 -preset veryslow -crf 18 " + options.OUTFILE
print(ffmpegcmd)
os.system(ffmpegcmd)
