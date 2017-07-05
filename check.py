#!/usr/bin/env python3
import re
from urllib.request import urlopen
from urllib.request import urlretrieve
from urllib.parse import urlparse
from urllib.parse import urlencode
from py3bencode import bdecode
from py3bencode import bencode
from os.path import isfile
from os.path import isdir
from os import mkdir
from os import system
from os import rename
import pickle
import hashlib
import base64
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz

#CONFIG
pickle_dir     = 'glass_jar'       # The name of the dir to store pickles in
version_pickle = 'lastVersion.p' # The name of the file used to save the last known version
feedGen_pickle = 'feedgen.p'     # The name of the file used to save the feed generator object

file_regex       = r'(octopi\-\w+\-\w+\-\d+\.\d+\.\d+\.zip)'     # Regex to find the file to download and torrent
file_location    = '/var/lib/deluge/torrents/'                   # Location you want to store the file to be torrented in
script_location  = '/var/lib/deluge/autotorrent/octopi/'         # Location of the script. Add a trailing slash!
torrent_location = '/var/lib/deluge/autoadd/'                    # Location of the .torrent file
maglink_location = '/var/www/html/octopi/magnetLinks/'           # Location of the .txt file that holds the magnet link

# A string of first the main tracker, followed by any backup trackers you want. Remember to have a space infront of each tracker!
trackers = (' udp://tracker.coppersurfer.tk:6969'
            ' udp://tracker.opentrackr.org:1337'
            ' udp://tracker.leechers-paradise.org:6969')

RSS_feed_title       = 'RSS feed for octopi torrents'
RSS_feed_link        = {'href':'http://flipflapflop.top/octopi/rss.xml','rel':'self'}
RSS_feed_description = 'An RSS feed for torrents of octopi images. Mainly to be used for automatic spread of initial seeders'
RSS_feed_base_URL    = 'http://flipflapflop.top/octopi/'
RSS_XML_location     = '/var/www/html/octopi/rss.xml'
#END CONFIG

# Create script specific directories
if not isdir(pickle_dir):
    mkdir(pickle_dir)

if not isdir('tempTorrentDir'):
    mkdir('tempTorrentDir')
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
    print("New version found. Downloading it and making a torrent for it.\n")
    localFile, headers = urlretrieve(latestURI, file_location + filename)
    system('/usr/bin/python3 {}py3createtorrent.py -o {}tempTorrentDir '.format(script_location, script_location) + localFile + trackers)

    # Calculating the magnet link and storing it in a file
    torrent = open('{}tempTorrentDir/'.format(script_location) + filename + '.torrent', 'rb').read()
    metadata = bdecode(torrent)

    hashcontents = bencode(metadata['info'])
    digest = hashlib.sha1(hashcontents).hexdigest()

    params = {'dn': metadata['info']['name'],
              'tr': metadata['announce'],
              'xl': metadata['info']['length']}
    paramstr = urlencode(params)
    magneturi = 'magnet:?xt=urn:btih:{}&{}'.format(digest,paramstr)
    with open(maglink_location + filename + '.txt', 'w') as file:
        file.write(magneturi + '\n')

    # Magnet has been calculated, move torrent to autoadd folder
    rename('{}tempTorrentDir/'.format(script_location) + filename + '.torrent', torrent_location + filename + '.torrent')
    # Generate an RSS entry
    if isfile(pickle_dir + '/' + feedGen_pickle):
        fg = pickle.load(open(pickle_dir + '/' + feedGen_pickle, 'rb'))
    else: # First time this is run, we have to set up the feed.
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
