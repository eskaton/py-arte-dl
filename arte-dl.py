#!/usr/bin/env python2.7

# Copyright (c) 2013, Adrian Moser
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# * Neither the name of the author nor the
# names of its contributors may be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
import re
import requests
import subprocess
import sys

def usage():
   sys.stderr.write('Usage: {} [-bh] [-d <-directory>] [ -l <language> ] [-c <choice>] [-o <file>] -u <url> \n'.format(sys.argv[0]))
   sys.stderr.write('   -h display help\n')
   sys.stderr.write('   -b only show videos with the best available quality\n')
   sys.stderr.write('   -d the directory to download the video to\n')
   sys.stderr.write('   -l regular expression to match a language\n')
   sys.stderr.write('   -c selection of available videos\n')
   sys.stderr.write('   -o name of the output file\n')
   sys.stderr.write('   -u url to download the video from\n')
   sys.exit(1)

def quality(a, b):
   return a['bitrate'] - b['bitrate']

def choose(last):
   print("")

   while True:
      sys.stdout.write("Please choose [1-{}]: ".format(last))
      s = sys.stdin.readline()
      try:
         n = int(s)
         if n >= 1 and n <= last:
            break
      except:
         pass

   return n

if __name__ == "__main__":
   langRegexStr = None
   url = None
   outFile = None
   bestQuality = False
   downloadFirst = False
   chose = False
   choice = 0

   argc = 1

   while argc + 1 < len(sys.argv):
      if sys.argv[argc] == "-h":
         usage()
      elif sys.argv[argc] == "-d":
         os.chdir(sys.argv[argc+1])
         argc += 2
      elif sys.argv[argc] == "-l":
         langRegexStr = sys.argv[argc+1]
         argc += 2
      elif sys.argv[argc] == "-o":
         outFile = sys.argv[argc+1]
         argc += 2
      elif sys.argv[argc] == "-u":
         url = sys.argv[argc+1] 
         argc += 2
      elif sys.argv[argc] == "-c":
         try:
            choice = int(sys.argv[argc+1])
            chose = True
         except:
            usage()
         argc += 2
      elif sys.argv[argc] == "-b":
         bestQuality = True
         argc += 1
      elif sys.argv[argc] == "-f":
         downloadFirst = True
         argc += 1
      else:
         break
            
   if url is None or argc < len(sys.argv):
      usage()

   enc = sys.stdout.encoding

   ident = re.findall("videos/([^/]+)/", url)[0]
   player = requests.get("https://api.arte.tv/api/player/v1/config/de/" + ident)
   config = json.loads(player.text)
   jsonPlayer = config['videoJsonPlayer']

   streams = dict(filter(lambda item: item[1]['mimeType'] == 'video/mp4', jsonPlayer['VSR'].items()))

   print("\n{}\n\n{}\n".format(jsonPlayer['VTI'].encode(enc), 
      jsonPlayer['V7T'].encode(enc) if 'V7T' in jsonPlayer else ""))

   streamsList = []

   for key in streams.keys():
      stream = streams[key]
      if not 'videoFormat' in stream or stream['videoFormat'] == 'RMP4':
         streamsList.append(streams[key])

   streamsList = sorted(streamsList, cmp=quality)

   if bestQuality:
      highestBitrate = streamsList[len(streamsList)-1]['bitrate']
      streamsList = [stream for stream in streamsList if stream['bitrate'] == highestBitrate]

   if langRegexStr is not None:
      langRegex = re.compile(langRegexStr)
      streamsList = [stream for stream in streamsList if langRegex.match(stream['versionLibelle'])]

   index = 1

   if chose:
      n = choice
   elif len(streamsList) == 1 or downloadFirst:
      n = 1
   else:
      for stream in streamsList:
         if 'videoFormat' in stream:
            print("[{}] {} / {} bits / {} / {}".format(index, stream['quality'], 
               stream['bitrate'], stream['videoFormat'], 
               stream['versionLibelle'].encode(enc)))
         else:
            print("[{}] {} / {} bits / {}".format(index, stream['quality'], 
               stream['bitrate'], stream['versionLibelle'].encode(enc)))
         index += 1
      n = choose(index-1)

   stream = streamsList[n-1]
   streamUrl = stream['url']

   if outFile is None:
      outFile = "{}.mp4".format(jsonPlayer['VTI'].encode(enc)).replace("/", "-")

   subprocess.call(["curl", streamUrl, "-o", outFile])
