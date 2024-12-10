  
set -x

CURRENT_YEAR=$(date +"%Y")

line1="/* Copyright(C) 2018-2023 Advanced Micro Devices, Inc. All rights reserved. */"
if [[ $line1 =~ Copyright\ *\(C\)\ *([0-9-]+)\ +([a-zA-Z\ ]+),\ +Inc\.* ]]; then
    # Update the year in the existing copyright line
    updated=true

    echo "${BASH_REMATCH[0]}"
    echo "${BASH_REMATCH[1]}"
    echo "${BASH_REMATCH[2]}"
    echo $line1
    line2=`echo $line1| sed "s/${BASH_REMATCH[1]}/$CURRENT_YEAR/"`
    echo "$line2"
fi
