sudo apt-get update
sudo apt install -y nginx
rm -rf /usr/share/nginx/html/* && rm -rf conf.d/*
                
echo "events {" > /etc/nginx/nginx.conf
echo "}">> /etc/nginx/nginx.conf
echo "" >> /etc/nginx/nginx.conf
echo "http {" >> /etc/nginx/nginx.conf
echo "  upstream splunk {" >> /etc/nginx/nginx.conf
echo "      ip_hash;" >> /etc/nginx/nginx.conf
echo "      $1" >> /etc/nginx/nginx.conf
echo "  }">> /etc/nginx/nginx.conf
echo "" >> /etc/nginx/nginx.conf
echo "  server {" >> /etc/nginx/nginx.conf
echo "      location ~ / {" >> /etc/nginx/nginx.conf
echo "          proxy_pass http://splunk;" >> /etc/nginx/nginx.conf
echo "      }" >> /etc/nginx/nginx.conf
echo "  }" >> /etc/nginx/nginx.conf
echo "}" >> /etc/nginx/nginx.conf
echo "" >> /etc/nginx/nginx.conf
sudo service nginx restart