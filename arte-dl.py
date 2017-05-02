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
import re
import requests
import subprocess
import sys

from lxml import etree

def usage():
   sys.stderr.write('Usage: {} -u <url> [-o <output-file>]\n'.format(sys.argv[0]))
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

def checkVideosFound(lst):
   if len(lst) < 1:
      print("No videos found")
      sys.exit(1)

if __name__ == "__main__":
   url = None
   outFile = None

   argc = 1

   while argc + 1 < len(sys.argv):
      if sys.argv[argc] == "-h":
         usage()
      elif sys.argv[argc] == "-o":
         outFile = sys.argv[argc+1]
         argc += 2
      elif sys.argv[argc] == "-u":
         url = sys.argv[argc+1] 
         argc += 2
      else:
         break
            
   if url is None or argc < len(sys.argv):
      usage()

   enc = sys.stdout.encoding
   page = requests.get(url)
   tree = etree.HTML(page.text)
   players = tree.xpath('//div[@class="video-player"]/iframe/@src')

   checkVideosFound(players)

   player = requests.get(players[0])
   jsonStrings = re.findall("var js_json = ({.*});", player.text)

   checkVideosFound(jsonStrings)

   video = json.loads(jsonStrings[0])
   jsonPlayer = video['videoJsonPlayer']

   streams = dict(filter(lambda item: item[1]['mimeType'] == 'video/mp4', jsonPlayer['VSR'].items()))

   print("\n{}\n\n{}\n".format(jsonPlayer['VTI'].encode(enc), 
      jsonPlayer['V7T'].encode(enc)))

   streamsList = []

   for key in streams.keys():
      stream = streams[key]
      if not 'videoFormat' in stream or stream['videoFormat'] == 'RMP4':
         streamsList.append(streams[key])

   streamsList = sorted(streamsList, cmp=quality)

   index = 1

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
      outFile = "{}.mp4".format(jsonPlayer['VTI'].encode(enc))

   subprocess.call(["curl", streamUrl, "-o", outFile])
