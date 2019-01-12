#!/usr/bin/env python3
import re
import tempfile
from urllib.request import urlopen, urlretrieve
from urllib.parse import urlparse, urlencode
from py3bencode import bdecode, bencode
from os.path import isfile, isdir, abspath
from os import system, mkdir, rename
from shutil import copy
import pickle
import hashlib
import base64
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz


# CONFIG
pickle_dir     = 'glass_jar'      # The name of the dir to store pickles in
version_pickle = 'lastVersion.p'  # The name of the file used to save the last known version
feedGen_pickle = 'feedgen.p'      # The name of the file used to save the feed generator object

file_regex       = r'(octopi\-\w+\-\w+\-\d+\.\d+\.\d+\.zip)'   # Regex to find the file to download and torrent
file_location    = '/srv/deluge/torrentGen/torrents/'          # Location you want to store the file to be torrented in
torrent_location = '/srv/deluge/torrentGen/autoadd/'           # Location of the .torrent file
webroot          = '/var/www/autotorrent.mikkel.cc/octopi/'    # Location of the root web folder to host torrents


# A string of first the main tracker, followed by any backup trackers you want. Remember to have a space infront of each tracker!
trackers = (' udp://tracker.coppersurfer.tk:6969'
            ' udp://tracker.opentrackr.org:1337'
            ' udp://tracker.leechers-paradise.org:6969')

RSS_feed_title       = 'RSS feed for octopi torrents'
RSS_feed_link        = {'href': 'https://autotorrent.mikkel.cc/octopi/rss.xml', 'rel': 'self'}
RSS_feed_description = 'An RSS feed for torrents of octopi images. Mainly to be used for automatic spread of initial seeders'
RSS_feed_base_URL    = 'https://autotorrent.mikkel.cc/octopi/'
RSS_XML_location     = '/var/www/autotorrent.mikkel.cc/octopi/rss.xml'
# END CONFIG

script_location = abspath(__file__)[0:-len(__file__)]

# Create script specific directories
if not isdir(pickle_dir):
    mkdir(pickle_dir)

if not isdir(file_location):
    mkdir(file_location)

if not isdir(torrent_location):
    mkdir(torrent_location)

if not isdir(webroot):
    mkdir(webroot)

if not isdir(webroot + 'magnetLinks'):
    mkdir(webroot + 'magnetLinks')

if not isdir(webroot + 'torrents'):
    mkdir(webroot + 'torrents')

# End

if isfile(pickle_dir + '/' + version_pickle):
    lastVersion = pickle.load(open(pickle_dir + '/' + version_pickle, 'rb'))
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
        localFile, headers = urlretrieve(latestURI, file_location + filename)
        system('/usr/bin/python3 {}/py3createtorrent.py -o {} {}{}'.format(script_location, tempDir, localFile, trackers))

        # Calculating the magnet link and storing it in a file
        torrent = open(tempDir + '/' + filename + '.torrent', 'rb').read()
        metadata = bdecode(torrent)

        hashcontents = bencode(metadata['info'])
        digest = hashlib.sha1(hashcontents).hexdigest()

        params = {'dn': metadata['info']['name'],
                  'tr': metadata['announce'],
                  'xl': metadata['info']['length']}
        paramstr = urlencode(params)
        magneturi = 'magnet:?xt=urn:btih:{}&{}'.format(digest,paramstr)
        with open(webroot + 'magnetLinks/' + filename + '.txt', 'w') as file:
            file.write(magneturi + '\n')

        # Magnet has been calculated, put a copy of the torrent in the web root
        copy(tempDir + '/' + filename + '.torrent', webroot + 'torrents/')

        # move torrent to autoadd folder
        rename(tempDir + '/' + filename + '.torrent', torrent_location + filename + '.torrent')

    # Generate an RSS entry
    if isfile(pickle_dir + '/' + feedGen_pickle):
        fg = pickle.load(open(pickle_dir + '/' + feedGen_pickle, 'rb'))

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

    pickle.dump(fg, open(pickle_dir + '/' + feedGen_pickle, 'wb'))

    lastVersion = version
else:
    print("No new version found. Skipping")


pickle.dump(lastVersion, open(pickle_dir + '/' + version_pickle, 'wb'))
