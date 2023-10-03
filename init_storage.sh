rm -rf storage
mkdir storage
mkdir $(echo storage/disk_{1..5})


seq 60 | awk '{print "File 1 Line "$1}' > storage/disk_1/file_1.txt
seq 200 | awk '{print "File 2 Line "$1}' > storage/disk_1/file_2.txt
seq 137 | awk '{print "File 3 Line "$1}' > storage/disk_1/file_3.txt
radius=50
image_size=150
circle_center=$((image_size / 2))
cat > storage/disk_1/file_4.svg <<EOF
<svg width="$image_size" height="$image_size" xmlns="http://www.w3.org/2000/svg">
    <circle cx="$circle_center" cy="$circle_center" r="$radius" fill="blue" />
    <rect x="$((circle_center - radius))" y="$((circle_center - radius))" width="$((radius*2))" height="$((radius*2))" fill="none" stroke="red" stroke-width="2" />
</svg>
EOF
cp init_storage/image_* storage/disk_1/
