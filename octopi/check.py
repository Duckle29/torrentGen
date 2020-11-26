#!/usr/bin/env python3
import re
import tempfile
from pathlib import Path
from subprocess import run
from os import rename
from shutil import copy
from datetime import datetime

from urllib.request import urlopen, urlretrieve
from urllib.parse import urlparse, urlencode
from py3bencode import bdecode, bencode

import pickle
import hashlib
import base64
from feedgen.feed import FeedGenerator
import pytz


# CONFIG
pickle_dir     = Path('glass_jar')              # The name of the dir to store pickles in
version_pickle = pickle_dir / 'lastVersion.p'   # The name of the file used to save the last known version
feedGen_pickle = pickle_dir / 'feedgen.p'       # The name of the file used to save the feed generator object

file_regex       = r'(octopi\-\w+\-\w+\-\d+\.\d+\.\d+\.zip)'     # Regex to find the file to download and torrent
file_location    = Path('/srv/deluge/torrentGen/torrents/')      # Location you want to store the file to be torrented in
torrent_location = Path('/srv/deluge/torrentGen/autoadd/')       # Location of the .torrent file
webroot          = Path('/srv/autotorrent.mikkel.cc/octopi/')    # Location of the root web folder to host torrents


# A tuple of trackers. Main tracker followed by any backup trackers.
trackers = (
    'udp://tracker.internetwarriors.net:1337/announce',
    'udp://tracker.leechers-paradise.org:6969/announce',
    'udp://tracker.coppersurfer.tk:6969/announce',
    'udp://tracker.pirateparty.gr:6969/announce',
    'http://explodie.org:6969/announce',
    'http://torrent.nwps.ws/announce',
    'udp://tracker.cyberia.is:6969/announce'
)

RSS_feed_title       = 'RSS feed for octopi torrents'
RSS_feed_link        = {'href': 'https://autotorrent.mikkel.cc/octopi/rss.xml', 'rel': 'self'}
RSS_feed_description = 'An RSS feed for torrents of octopi images. Mainly to be used for automatic spread of initial seeders'
RSS_feed_base_URL    = 'https://autotorrent.mikkel.cc/octopi/torrents/'
RSS_XML_location     = '/var/www/autotorrent.mikkel.cc/octopi/rss.xml'
# END CONFIG

script_location = Path(__file__).resolve().parent
magnet_web = webroot / 'magnetLinks'
torrent_web = webroot / 'torrents'

if not script_location:
    raise FileNotFoundError("Can't find location of current script")

# Create script specific directories
if not pickle_dir.is_dir():
    pickle_dir.mkdir()

if not file_location.is_dir():
    file_location.mkdir()

if not torrent_location.is_dir():
    torrent_location.mkdir()

if not webroot.is_dir():
    webroot.mkdir()

if not magnet_web.is_dir():
    magnet_web.mkdir()

if not torrent_web.is_dir():
    torrent_web.mkdir()

# End

if version_pickle.is_file():
    lastVersion = pickle.load(version_pickle.open('rb'))
else:
    lastVersion = 0

response = urlopen('https://octopi.octoprint.org/latest')
latestURI = response.geturl()
searchObj = re.search(file_regex, latestURI, re.I)
filename = searchObj.group(1)

versionBlob = filename.split('-')[-1].split('.')
versionBlob.pop()
version = int(''.join(versionBlob))

if version > lastVersion:
    with tempfile.TemporaryDirectory() as tempDir:
        print("New version found. Downloading it and making a torrent for it.\n")
        localFile, headers = urlretrieve(latestURI, file_location / filename)
        command = [
            '/usr/bin/python3',
            '{}/py3createtorrent.py'.format(script_location),
            '-o', tempDir,
            localFile,
            ' '.join(trackers)
        ]
        run(command)

        # Calculating the magnet link and storing it in a file
        torrent = (tempDir / (filename + '.torrent')).open('rb').read()
        metadata = bdecode(torrent)

        hashcontents = bencode(metadata['info'])
        digest = hashlib.sha1(hashcontents).hexdigest()

        params = {'dn': metadata['info']['name'],
                  'tr': metadata['announce'],
                  'xl': metadata['info']['length']}
        paramstr = urlencode(params)
        magneturi = 'magnet:?xt=urn:btih:{}&{}'.format(digest,paramstr)
        with (webroot / 'magnetLinks' / (filename + '.txt')).open('w') as file:
            file.write(magneturi + '\n')

        # Magnet has been calculated, put a copy of the torrent in the web root
        copy(tempDir / (filename + '.torrent'), webroot + 'torrents/')

        # move torrent to autoadd folder
        rename(tempDir / (filename + '.torrent'), torrent_location / (filename + '.torrent'))

    # Generate an RSS entry
    if feedGen_pickle.is_file():
        fg = pickle.load(feedGen_pickle.open('rb'))

    else:  # First time this is run, we have to set up the feed.
        fg = FeedGenerator()
        fg.title(RSS_feed_title)
        fg.link(RSS_feed_link)
        fg.description(RSS_feed_description)
        fg.load_extension('torrent')

    fe = fg.add_entry()
    fe.id(RSS_feed_base_URL+filename+'.torrent')
    fe.title(filename)
    fe.link(href=RSS_feed_base_URL+filename+'.torrent')
    fe.torrent.filename(filename+'.torrent')
    fe.torrent.infohash(digest)
    fe.published(datetime.now(pytz.utc))

    fg.rss_file(RSS_XML_location)

    pickle.dump(fg, feedGen_pickle.open('wb'))

    lastVersion = version
else:
    print("No new version found. Skipping")


pickle.dump(lastVersion, version_pickle.open('wb'))
