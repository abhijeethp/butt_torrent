rm -rf storage
mkdir storage
mkdir $(echo storage/disk_{1..5})


seq 60 | awk '{print "File 1 Line "$1}' > storage/disk_1/file_1.txt
seq 200 | awk '{print "File 2 Line "$1}' > storage/disk_1/file_2.txt
seq 137 | awk '{print "File 3 Line "$1}' > storage/disk_1/file_3.txt
