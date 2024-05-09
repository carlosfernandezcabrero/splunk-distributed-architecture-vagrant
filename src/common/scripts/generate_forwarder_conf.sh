echo "[general]" > /usr/local/$4/etc/system/local/server.conf
echo "serverName = $3" >> /usr/local/$4/etc/system/local/server.conf
echo "" >> /usr/local/$4/etc/system/local/server.conf

echo "[tcpout]" > /usr/local/$4/etc/system/local/outputs.conf
echo "defaultGroup = de_group" >> /usr/local/$4/etc/system/local/outputs.conf
echo "" >> /usr/local/$4/etc/system/local/outputs.conf
echo "[tcpout:de_group]" >> /usr/local/$4/etc/system/local/outputs.conf
echo "server = $2" >> /usr/local/$4/etc/system/local/outputs.conf
echo "" >> /usr/local/$4/etc/system/local/outputs.conf
echo "[tcpout:pr_group]" >> /usr/local/$4/etc/system/local/outputs.conf
echo "server = $1" >> /usr/local/$4/etc/system/local/outputs.conf
echo "" >> /usr/local/$4/etc/system/local/outputs.conf