#!/bin/bash

export PYTHONPATH="/var/www/ryanair:/var/www/ryanair/ryanair:/var/envs/ryanair/lib/python2.7/site-packages:/var/envs/ryanair/bin"

PATH=$PATH:/var/envs/ryanair/bin
export PATH                                                                                            

scrapy crawl ryanair
