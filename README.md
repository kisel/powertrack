###
Simple python script to track poweroff / poweron events


### Quickstart

    ./powertrack.py --watch
    ./powertrack.py --list
    ./powertrack.py -h


### Install/Uninstall system service

    # installs /usr/local/bin/powertrack and systemd service
    sudo ./powertrack.py --install

    powertrack --list --db /var/lib/powertrack/powertrack.sqlite


    sudo powertrack --uninstall
