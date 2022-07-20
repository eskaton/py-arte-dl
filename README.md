Arte Downloader
======

Synopsis
----------

arte-dl.py is a script to download videos from arte.tv.
It depends on ffmpeg and Python 3.8.

Usage
-----

```
Usage: arte-dl.py [-bh] [-d <directory>] [-a <languages>] [-s <languages>] [-c <choice>] [-o <file>] -u <url> 
   -h display help
   -b select video with the best available quality
   -d the directory to download the video to
   -a comma separated list of audio languages or 'all' for all languages
   -s comma separated list of subtitle languages or 'all' for all languages
   -c selection of available videos
   -o name of the output file without extension
   -u url to download the video from
```

There is no error handling. If the script fails either the arte site is down
or they changed the layout of their site.
