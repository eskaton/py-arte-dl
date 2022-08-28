#!/usr/bin/env python3.8

# Copyright (c) 2013-2022, Adrian Moser
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

import hashlib
import json
import m3u8
import os
import re
import requests
import subprocess
import sys
import webvtt

from functools import cmp_to_key


def usage():
    sys.stderr.write(
        'Usage: {} [-bhv] [-d <directory>] [-a <languages>] [-s <languages>] [-c <choice>] [-o <file>] -u <url> \n'.format(sys.argv[0]))
    sys.stderr.write('   -h display help\n')
    sys.stderr.write('   -b select video with the best available quality\n')
    sys.stderr.write('   -d the directory to download the video to\n')
    sys.stderr.write('   -a comma separated list of audio languages, \'all\' for all languages or \'none\'\n')
    sys.stderr.write('   -s comma separated list of subtitle languages, \'all\' for all languages or \'none\'\n')
    sys.stderr.write('   -c selection of available videos\n')
    sys.stderr.write('   -o name of the output file without extension\n')
    sys.stderr.write('   -u url to download the video from\n')
    sys.stderr.write('   -v verbose mode\n')
    sys.exit(1)


def quality(a, b):
    return a.stream_info.bandwidth - b.stream_info.bandwidth


def choose(last):
    print("")

    while True:
        sys.stdout.write("Please choose [1-{}]: ".format(last))
        sys.stdout.flush()
        s = sys.stdin.readline()
        try:
            n = int(s)
            if 1 <= n <= last:
                break
        except:
            pass

    return n


def get_streams(streams):
    audio_streams = dict()
    subtitle_streams = dict()

    video_streams = sorted(m3u8.load(streams[0]['url']).playlists, key=cmp_to_key(quality))

    for stream in streams:
        stream_file = m3u8.load(stream['url'])

        audio_media = [media for media in stream_file.media if media.type == "AUDIO"]
        subtitles_media = [media for media in stream_file.media if media.type == "SUBTITLES"]

        for am in audio_media:
            if not am.name.endswith("AUD"):
                media_stream_file = m3u8.load(am.absolute_uri)

                audio_streams.update({am.language: {
                    'name': am.name,
                    'language': am.language,
                    'uri': media_stream_file.segments[0].absolute_uri
                }})

        for sm in subtitles_media:
            media_stream_file = m3u8.load(sm.absolute_uri)

            subtitle_streams.update({sm.name: {
                'name': sm.name,
                'language': sm.language,
                'uri': media_stream_file.segments[0].absolute_uri
            }})

    return video_streams, audio_streams.values(), subtitle_streams.values()


def choose_resolution(last):
    print("")

    while True:
        sys.stdout.write("Please choose a resolution [1-{}]: ".format(last))
        sys.stdout.flush()
        s = sys.stdin.readline().strip()

        try:
            n = int(s)
            if 1 <= n <= last:
                break
        except:
            pass

    return n


def choose_stream(last, type_name):
    print("")

    while True:
        sys.stdout.write(
            "Please choose one or more {} languages (comma separated), 'all' or 'none' [1-{}]: ".format(type_name, last))
        sys.stdout.flush()
        s = sys.stdin.readline().strip()

        try:
            if s == "none":
                return []
            elif s == "all":
                return list(range(1, last + 1))

            idxs = [int(idx) for idx in s.split(",")]

            for idx in idxs:
                if not 1 <= idx <= last:
                    continue

            return idxs
        except:
            pass


def select_video_stream(streams, selection):
    if len(streams) == 1:
        return streams[0]

    if selection is None:
        print("")

        index = 1

        for video_stream in streams:
            resolution = video_stream.stream_info.resolution
            print("{}) {}x{}".format(index, resolution[0], resolution[1]))
            index = index + 1

        resolution_idx = choose_resolution(index - 1)
    else:
        resolution_idx = selection

    video_stream = streams[resolution_idx - 1]

    return video_stream


def select_streams(streams, type_name, selection):
    if len(streams) == 1:
        return [list(streams)[0]]

    index = 1

    if selection is None:
        print("")

        if len(streams) > 0:
            for stream in streams:
                print("{}) {} - {}".format(index, stream['name'], stream['language']))
                index = index + 1

            idxs = choose_stream(index - 1, type_name)
        else:
            idxs = []
    else:
        if selection == "all":
            idxs = list(range(1, len(streams) + 1))
        else:
            languages = set(selection.split(","))
            idxs = []

            for stream in streams:
                if stream['language'] in languages:
                    idxs.append(index)

                index = index + 1

    result = []

    for idx in idxs:
        result.append(list(streams)[idx - 1])

    return result


def get_sha256(file_name):
    sha256_hash = hashlib.sha256()

    with open(file_name, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(block)

    return sha256_hash.hexdigest()


def download(url, file_name, verbose):
    sha_file = file_name + ".sha256"

    if os.path.isfile(file_name) and os.path.isfile(sha_file):
        if verbose:
            print("{} already exists. Verifying checksum...".format(file_name))

        with open(sha_file, 'r') as fs:
            sha256 = fs.read().rstrip()

            if sha256 == get_sha256(file_name):
                if verbose:
                    print("Checksum matches. skipping...")

                return sha_file, file_name
            else:
                if verbose:
                    print("Checksum mismatch. Re-downloading...")

    if verbose:
        print("Downloading {}...".format(url))

    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with open(file_name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    f.write(chunk)

    with open(sha_file, "w") as fs:
        fs.write(get_sha256(file_name))

    return sha_file, file_name


if __name__ == "__main__":
    video_selection = None
    audio_lang_selection = None
    subtitle_lang_selection = None
    url = None
    out_file_prefix = None
    best_quality = False
    chose = False
    verbose = False
    choice = 0

    argc = 1

    while argc + 1 < len(sys.argv):
        if sys.argv[argc] == "-h":
            usage()
        elif sys.argv[argc] == "-d":
            os.chdir(sys.argv[argc + 1])
            argc += 2
        elif sys.argv[argc] == "-a":
            audio_lang_selection = sys.argv[argc + 1]
            argc += 2
        elif sys.argv[argc] == "-s":
            subtitle_lang_selection = sys.argv[argc + 1]
            argc += 2
        elif sys.argv[argc] == "-o":
            out_file_prefix = sys.argv[argc + 1]
            argc += 2
        elif sys.argv[argc] == "-u":
            url = sys.argv[argc + 1]
            argc += 2
        elif sys.argv[argc] == "-c":
            try:
                video_selection = int(sys.argv[argc + 1])
            except:
                usage()
            argc += 2
        elif sys.argv[argc] == "-b":
            best_quality = True
            argc += 1
        elif sys.argv[argc] == "-v":
            verbose = True
            argc += 1
        else:
            break

    if url is None or argc < len(sys.argv):
        usage()

    files_to_delete = []

    ident = re.findall("videos/([^/]+)/", url)[0]
    player = requests.get("https://api.arte.tv/api/player/v2/config/de/" + ident)
    config = json.loads(player.text)

    if not ('data' in config):
        sys.stderr.write("'data' not found in configuration:\n\n{}\n".format(config))
        exit(1)

    attributes = config['data']['attributes']
    metadata = attributes['metadata']
    title = metadata['title']
    description = metadata['description']
    streams = attributes['streams']

    print("{}\n\n{}".format(title, description))

    (video_streams, audio_streams, subtitle_streams) = get_streams(streams)

    video_streams = sorted(video_streams, key=cmp_to_key(quality))

    if best_quality:
        video_streams = [video_streams[len(video_streams) - 1]]

    video_stream = select_video_stream(video_streams, video_selection)
    audio_streams = select_streams(audio_streams, "audio", audio_lang_selection)
    subtitle_streams = select_streams(subtitle_streams, "subtitle", subtitle_lang_selection)

    if out_file_prefix is None:
        out_file_prefix = "{}".format(title).replace("/", "-")

    video_file = out_file_prefix + ".mp4"
    video_stream_file = m3u8.load(video_stream.absolute_uri)

    args = ["ffmpeg", "-y", "-nostats"]
    input_args = []
    map_args = []
    copy_args = ["-c:v", "copy"]
    metadata_args = []

    files_to_delete.extend(download(video_stream_file.segments[0].absolute_uri, video_file, verbose))

    input_args.extend(["-i", video_file])
    map_args.extend(["-map", "0:v"])

    stream_idx = 1
    audio_idx = 0
    subtitle_idx = 0

    if len(audio_streams) > 0:
        for audio_stream in audio_streams:
            audio_file = out_file_prefix + "_" + audio_stream['language'] + "_" + str(audio_idx) + ".aac"
            files_to_delete.extend(download(audio_stream['uri'], audio_file, verbose))

            input_args.extend(["-i", audio_file])
            map_args.extend(["-map", "{}:a".format(stream_idx)])
            metadata_args.extend(["-metadata:s:a:{}".format(audio_idx), "language={}".format(audio_stream['language'])])
            stream_idx = stream_idx + 1
            audio_idx = audio_idx + 1

        copy_args.extend(["-c:a", "copy"])

    if len(subtitle_streams) > 0:
        for subtitle_stream in subtitle_streams:
            subtitle_file = out_file_prefix + "_" + subtitle_stream['language'] + "_" + str(subtitle_idx) + ".vtt"
            files_to_delete.extend(download(subtitle_stream['uri'], subtitle_file, verbose))

            vtt = webvtt.read(subtitle_file)
            vtt.save_as_srt()

            subtitle_file_srt = subtitle_file.replace("vtt", "srt")
            files_to_delete.append(subtitle_file_srt)

            input_args.extend(["-i", subtitle_file_srt])
            map_args.extend(["-map", "{}:s".format(stream_idx)])
            metadata_args.extend(["-metadata:s:s:{}".format(subtitle_idx), "language={}".format(subtitle_stream['language'])])
            stream_idx = stream_idx + 1
            subtitle_idx = subtitle_idx + 1

        copy_args.extend(["-c:s", "copy"])

    args.extend(input_args)
    args.extend(map_args)
    args.extend(copy_args)
    args.extend(metadata_args)

    args.append(out_file_prefix + ".mkv")

    if verbose:
        print("Multiplexing all streams with ffmpeg command: {}".format(" ".join(args)))

    subprocess.call(args)

    for file in files_to_delete:
        os.remove(file)
