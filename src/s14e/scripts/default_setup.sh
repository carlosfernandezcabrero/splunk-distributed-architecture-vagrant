echo "[INFO] Configuring timezone to Europe/Madrid"
#---------------------------------------------------
timedatectl set-timezone Europe/Madrid


echo "[INFO] Configuring limits for vagrant user"
#---------------------------------------------------
echo "" >> /etc/security/limits.conf

echo "#Parametros vagrant" >> /etc/security/limits.conf

echo "vagrant soft nofile $1" >> /etc/security/limits.conf
echo "vagrant hard nofile $1" >> /etc/security/limits.conf

echo "vagrant soft nproc $2" >> /etc/security/limits.conf
echo "vagrant hard nproc $2" >> /etc/security/limits.conf