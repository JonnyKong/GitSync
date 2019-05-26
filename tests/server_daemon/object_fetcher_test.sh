#!/bin/bash
# Integration test for ObjectFetcher

# Init objects_test_1, clear objects_test_2
python3 db_init.py e8932bad31b14c89bb34dd526d844a24a21c9f54

../../build/bin/object_fetcher_main server &
PID_1=$!
sleep 1
../../build/bin/object_fetcher_main client e8932bad31b14c89bb34dd526d844a24a21c9f54 &
PID_2=$!
sleep 5
kill -9 $PID_1
kill -9 $PID_2

# COUNT_1=$(echo "use gitsync\n db.objects_test_1.count()" | mongo | tail -2 | head -n 1)
# COUNT_2=$(echo "use gitsync\n db.objects_test_2.count()" | mongo | tail -2 | head -n 1)
echo "Please manually check whether collection objects_test_1 and objects_test_2 in gitsync have same count"

exit $?