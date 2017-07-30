Arte Downloader
======

Synopsis
----------

arte-dl.py is a script to download videos from arte.tv.
It depends on curl and Python 2.7.

Usage
-----

```
Usage: arte-dl.py [-bh] [-d <-directory>] [ -l <language> ] [-c <choice>] [-o <file>] -u <url>
  -h display help
  -b only show videos with the best available quality
  -d the directory to download the video to
  -l regular expression to match a language
  -c selection of available videos
  -o name of the output file
  -u url to download the video from

```

There is no error handling. If the script fails either the arte site is down
or they changed the layout of their site.
