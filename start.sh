#!/bin/bash
#echo -e "\nHardware   : BCM2709" >> /etc/cpuinfo
if [ -e /etc/cpuinfo ] ; then
  mount --bind /etc/cpuinfo /proc/cpuinfo
fi

/usr/bin/python3 /home/prakhar/iot-sensors/sensor-iot.py
