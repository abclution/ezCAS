#!/bin/bash

fCount=$(find "$1" -type f | wc -l)
echo "FILES: $fCount"
#find ./.CAS-store.GALLERY_PhotosVideosImagesAudio/ -type f | wc -l
#find $1 -type f | wc -l


dCount=$(find "$1" -type d | wc -l)
echo "DIRS: $dCount"
#find ./.CAS-store.GALLERY_PhotosVideosImagesAudio/ -type d | wc -l
#find $1 -type d | wc -l
