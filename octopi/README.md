# Torrent feed generator
A script that checks a given link for a new version of software (based on filename)
and creates a torrent for the new software, seeds it and offers an RSS feed of
the torrents / magnetURIs

# Requirements

* Python 3
* Python FeedGenerator
* pytz
* [py3createtorrent](https://py3createtorrent.readthedocs.io/en/latest/user.html#installation)

Install them with these commands:

ubuntu based linux systems

    sudo apt install python3 python3-pip
    pip3 install feedgen pytz

# Important note
This script was made for a specific purpose, and thus some of the code is rather specific to that use.

The script does a regex for octopi-anyword-anyword-numbers.numbers.numbers.zip
It relies on the filename to end in a version, in the format 0.0.0.zip, as it strips the dots and the "zip" away, 
and gets an integer from that, and hence version 0.13.0.zip = 130, and version 0.14.1.zip = 141, etc.

## Usage
Setup the configuration variables. The included ones assume you are using deluged with autotorrent
for the torrent seeding with it's home in /var/lib/deluge,
and have a web server running with web root at /var/www/html/

It's then intended to run check.py periodically with a cronjob.

The script is what is running autotorrent.mikkel.cc
