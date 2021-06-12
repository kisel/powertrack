#!/usr/bin/env python3

import sqlite3
import threading
import time
import argparse
from typing import NamedTuple

class Options(NamedTuple):
    interval: int
    tolerance: int

EVT_POWERON = 1
EVT_POWEROFF = 2

LAST_ON = 'last_on'
TIMESTAMPS_TABLE = 'timestamps'
DEFAULT_DB_PATH = '/var/lib/powertrack/powertrack.sqlite'

def dbinit(db):
    # declare event_types ENUM
    db.execute('''CREATE TABLE IF NOT EXISTS event_types (
        event_type_id INTEGER PRIMARY KEY,
        name TEXT,
        event_group TEXT
        ) ''')

    db.executemany('''INSERT OR IGNORE INTO event_types (event_type_id, name, event_group) VALUES (?,?,?)''', [
        (EVT_POWERON, "power_on", "power"),
        (EVT_POWEROFF, "power_off", "power"),
        ])

    # key-value timestamps
    db.execute('''CREATE TABLE IF NOT EXISTS timestamps (
        name TEXT UNIQUE,
        timestamp DATETIME
        ) ''')

    # events journal
    db.execute('''CREATE TABLE IF NOT EXISTS journal (
        timestamp DATETIME NOT NULL,
        event_type_id INTEGER,
        FOREIGN KEY (event_type_id)
        REFERENCES event_types (event_type_id)
        ) ''')
    db.execute('''CREATE VIEW IF NOT EXISTS journal_human AS
        select
            datetime(journal.timestamp, 'unixepoch', 'localtime') AS timestr,
            journal.timestamp AS timestamp,
            event_types.name AS event
        from journal join event_types
        on journal.event_type_id=event_types.event_type_id''')

    db.commit()

def get_last_on_time(db):
    """ returns epoch seconds or 0 if no timestamp found """
    res = db.execute('SELECT (timestamp) FROM timestamps WHERE name=?', [LAST_ON]).fetchall()
    if len(res) == 1:
        return int(res[0][0])
    else:
        return 0

def startup(db, opt: Options):
    last_on = get_last_on_time(db)
    time_now = int(time.time())
    if last_on != 0 and time_now - last_on > opt.tolerance:
        print("Detected offline time")
        print("Shutdown time: %s" % time.ctime(last_on))
        print("Power on time: %s" % time.ctime(time_now))
        print("Offline time(sec): %d" % (time_now - last_on))
        db.execute("INSERT INTO journal(event_type_id, timestamp) VALUES (?, ?)", [EVT_POWEROFF, last_on])
        db.execute("INSERT INTO journal(event_type_id, timestamp) VALUES (?, ?)", [EVT_POWERON, time_now])
        db.commit()
    else:
        print("No offline time detected")
        print("Last online time: %s" % time.ctime(last_on))
        print("App start time: %s" % time.ctime(time_now))


def watchdog(db):
    """ updates last timestamp """
    res = db.execute("INSERT OR REPLACE INTO timestamps(name, timestamp) VALUES (?, ?)", [LAST_ON, int(time.time())])
    db.commit()

def watch(db, opt: Options):
    dbinit(db)
    startup(db, opt)
    while True:
        watchdog(db)
        time.sleep(opt.interval)

def print_events(db):
    res = db.execute('SELECT timestr, event FROM journal_human').fetchall()
    print("Found %d events:" % len(res))
    for ts, evtname in res:
        print("{:20} {}".format(ts, evtname))

def sh(shellcmd):
    import os
    print(shellcmd)
    os.system(shellcmd)

def install():
    sh('cp -v powertrack.py /usr/local/bin/powertrack')
    sh('chmod 755 /usr/local/bin/powertrack')
    sh('cp -v powertrack.service /etc/systemd/system/powertrack.service')
    sh('chmod 755 /etc/systemd/system/powertrack.service')
    sh('systemctl enable --now powertrack.service')
    sh('systemctl status powertrack.service')

def uninstall():
    sh('systemctl disable --now powertrack.service')
    sh('rm /usr/local/bin/powertrack')
    sh('rm /etc/systemd/system/powertrack.service')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--db', default=DEFAULT_DB_PATH, help='database path(defaults to %s)' % DEFAULT_DB_PATH)
    parser.add_argument('--interval', default=60, type=int, help='update last online interval')
    parser.add_argument('--tolerance', default=0, type=int, help='ignore offline shorter than N sec(default=0)')
    parser.add_argument('--watch', action='store_true', help='watch for shutdown')
    parser.add_argument('--list', action='store_true', help='print journal')
    parser.add_argument('--install', action='store_true', help='install system service(run with sudo)')
    parser.add_argument('--uninstall', action='store_true', help='uninstall system service(run with sudo)')
    args = parser.parse_args()

    if args.install:
        install()
        return
    if args.uninstall:
        uninstall()
        return

    db = sqlite3.connect(args.db)
    if args.list:
        print_events(db)
    elif args.watch:
        watch(db, Options(interval=args.interval, tolerance=args.tolerance))
    else:
        print("no actions selected. see -h")

if __name__ == "__main__":
    main()
