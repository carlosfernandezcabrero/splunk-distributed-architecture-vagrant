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


echo "[INFO] Configuring THP (Transparent HugePage) at boot time"
#---------------------------------------------------
sed -i "s/GRUB_CMDLINE_LINUX=\"/&transparent_hugepage=never /" /etc/default/grub

source /etc/os-release

rhel_ids=("rhel" "centos" "fedora")
debian_ids=("debian" "ubuntu")

if [[ " ${rhel_ids[@]} " =~ " ${ID} " ]]; then
    grub2-mkconfig -o /boot/grub2/grub.cfg
elif [[ " ${debian_ids[@]} " =~ " ${ID} " ]]; then
    update-grub
else
    echo "[ERROR] OS not supported"
    exit 1
fi
