for i in $(find /tmp/scripts_to_execute -type f | sort | grep -v ".gitignore"); do
    chmod +x $i
    $i
done