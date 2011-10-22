#! /usr/bin/env bash
mkvirtualenv --no-site-packages --python python2 ci
workon ci
add2virtualenv .
pip install -U pip
pip install -r requirements.txt
gem install bundle
bundle install
