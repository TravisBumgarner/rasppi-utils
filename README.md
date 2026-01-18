# Setup

## Rasberry Pi

1. Just use HDMI, keyboard, mouse. Setting creds in Raspberry Pi imager seems terrible.
1. Enable SSH
1. Setup :allthethings:

```
sudo apt update && sudo apt full-upgrade -y

```

## Macbook

1. Remove old SSH `ssh-keygen -R raspberrypi.local`
1. ssh `admin@raspberrypi.local`