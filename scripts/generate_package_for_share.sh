rm -rfv /tmp/splunk-distributed-architecture-vagrant

cp -r ../../splunk-distributed-architecture-vagrant /tmp

cd /tmp/splunk-distributed-architecture-vagrant

rm -rfv src/*/.vagrant
rm -rfv .git/
rm -rfv .vscode/
rm -rfv .github/
rm -rfv .venv/
rm -rfv .idea/
rm -v .gitignore
rm -v .DS_Store