#!/bin/bash

GDRIVE=../gdrive-linux-rpi

DIR_ID="1RuexvSCz_XhJg621coEKBZ7nF9fYcWI-"

FILE_ID=`$GDRIVE list --query "'$DIR_ID' in parents" | grep tempi.png | awk '{print $1;}'`
for file_idx in $FILE_ID
do
  echo $file_idx
  $GDRIVE delete $file_idx
done

$GDRIVE upload --parent $DIR_ID /var/www/html/tempi.png
NEW_FILE_ID=`$GDRIVE list --query "'$DIR_ID' in parents" | grep tempi.png | awk '{print $1;}' | head -1`
if [ -z $NEW_FILE_ID ]
then
  echo
else
  $GDRIVE share $NEW_FILE_ID
fi


