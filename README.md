# Diematic32MQTT
MQTT interface for De Dietrich Diematic3 heater regulator written in python

Today, allow only to read Diematic3 parameters

TODO: documentation, feature to write parameters

To run as a service on raspbian:
as root, copy and adapt Diematic32MQTT.service to /etc/systemd/system/ directory
sudo chmod 644 /etc/systemd/system/Diematic32MQTT.service
chmod +x /home/pi/Diematic32MQTT/Diematic32MQTT.py
sudo systemctl daemon-reload
sudo systemctl enable Diematic32MQTT.service
sudo systemctl start Diematic32MQTT.service
