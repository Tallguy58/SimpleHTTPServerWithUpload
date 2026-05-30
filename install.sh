#!/bin/bash

cp -v -f SimpleHTTPServerWithUpload.py /bin

cat <<'EOF'>/bin/SimpleHTTPServerWithUpload.sh
#!/bin/bash
clear
cd /mnt/shared_media
python3 /bin/SimpleHTTPServerWithUpload.py 8080
EOF

cat <<'EOF'>/lib/systemd/system/SimpleHTTPServerWithUpload.service
[Unit]
Description=Simple HTTP Server With Upload

[Service]
ExecStart=/bin/SimpleHTTPServerWithUpload.sh
Restart=Always

[Install]
WantedBy=multi-user.target
EOF

chmod -v +x /bin/SimpleHTTPServerWithUpload.py
chmod -v +x /bin/SimpleHTTPServerWithUpload.sh
chmod -v 644 /lib/systemd/system/SimpleHTTPServerWithUpload.service

systemctl enable SimpleHTTPServerWithUpload
exit