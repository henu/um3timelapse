Ultimaker 3 Timelapse Maker
===========================

A script that makes Octolapse-style timelapse videos from the onboard camera on your Ultimaker 3 using nothing but software.

[YouTube Video Test](https://youtu.be/NAAGY1Z1AdE)

### CHANGES FROM ORIGINAL:

People have been using an Octoprint plugin, Octolapse, to do this on their Prusa and other 3D printers already, but few have done this trick on an Ultimaker. I stumbled upon a post in the Ultimaker 3 Support group on Facebook and it led to this [Thingiverse page](https://www.thingiverse.com/thing:3121227). My main thing was I knew that unlimitedbacon's code worked (really well) and I liked the idea of moving the head out of the way to take a picture. Using this repository, you don't have to print anything extra to mount another camera to your printer. The only major changes are printing a dummy object on Extruder 2 and running this Python script somewhere.

Usage remains the same, and currently this will only work superbly well with one material. Load nothing material in Extruder 2 so nothing comes out of the nozzle, but make the printer thing there is something loaded. In my case that's PLA. Next, place an object to be printed on Extruder 2 out of the way of your main model and resize it to the height of your model with the X and Y being 1 and 1.

![screenshot](https://github.com/starbuck93/um3timelapse/raw/master/screenshot.png)

You can put any number for the delay, that option will be removed soon.


Usage
-----
```
$ ./timelapse.py HOST 1 OUTFILE
```



This script requires Python 3.5 or later and [FFmpeg](https://ffmpeg.org/).
Run the script. It will wait for your Ultimaker to begin printing, then it will start taking pictures when the printhead moves out of the way of the print. Theoretically it will only take one picture per layer.
When the print finishes, the script will compile all the snapshots it took into a video.
Video is encoded using H.264 at 30 fps, but you can easily change this by editing `ffmpegcmd` in the script.

| Option  | Description |
| ------- | ----------- |
| HOST    | The IP address of your Ultimaker 3. You can find this through the menu by going to System > Network > Connection Status. |
| DELAY   | Not used in this repository. I put a `1` here so the code doesn't freak out. |
| OUTFILE | This is the name of the video file you want to make. I recommend giving it either a .mkv or .mp4 extension, although you could choose any container format that supports H.264. |

Thanks
------

[Ultimaker 3 API library](https://ultimaker.com/en/community/23329-inside-the-ultimaker-3-day-3-remote-access-part-2) by Daid
