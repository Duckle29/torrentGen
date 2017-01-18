# Torrent feed generator
A script that checks a given link for a new version of software (based on filename)
and creates a torrent for the new software, seeds it and offers an RSS feed of
the torrents / magnetURIs

# Requirements

* python FeedGenerator
* pytz

Install then with these commands:

    pip install feedgen pytz

# Important note
This script was made for a specific purpose, and thus some of the code is rather specific to that used.

The main thing here is the version checking. It relies on a url to a file (https://urltofile/filename-0.0.0.zip)
The code relies on a dash in front of a dot seperated version, with a file extension.
If you wish to use this code for your own needs. You will probably have to tweak the version checking.
