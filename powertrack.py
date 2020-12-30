import sqlite3
import threading
import time

db = sqlite3.connect('powertrack.sqlite')

EVT_POWERON = 1
EVT_POWEROFF = 2

LAST_ON = 'last_on'
TIMESTAMPS_TABLE = 'timestamps'
shutdown_tolerance = 30

def dbinit():
    # declare event ENUM
    db.execute('''CREATE TABLE IF NOT EXISTS event (
    eventid INTEGER PRIMARY KEY,
    name TEXT,
    event_group TEXT
    ) ''')

    db.executemany('''INSERT OR IGNORE INTO event (eventid, name, event_group) VALUES (?,?,?)''', [
        (EVT_POWERON, "power_off", "power"),
        (EVT_POWEROFF, "power_on", "power"),
    ])

    # key-value timestamps
    db.execute('''CREATE TABLE IF NOT EXISTS timestamps (
    name TEXT UNIQUE,
    timestamp DATETIME
    ) ''')

    # events journal
    db.execute('''CREATE TABLE IF NOT EXISTS events (
    timestamp DATETIME NOT NULL,
    eventid INTEGER,
    FOREIGN KEY (eventid)
      REFERENCES event (eventid)

    ) ''')
    db.commit()

def get_last_on_time():
    """ returns epoch seconds or 0 if no timestamp found """
    res = db.execute('SELECT (timestamp) FROM timestamps WHERE name=?', [LAST_ON]).fetchall()
    if len(res) == 1:
        return int(res[0][0])
    else:
        return 0

def startup():
    last_on = get_last_on_time()
    time_now = int(time.time())
    if last_on != 0 and time_now - last_on > shutdown_tolerance:
        print("Detected offline time")
        print("Shutdown time: %s" % time.ctime(last_on))
        print("Power on time: %s" % time.ctime(time_now))
        print("Offline time(sec): %d" % (time_now - last_on))
        db.execute("INSERT INTO events(eventid, timestamp) VALUES (?, ?)", [EVT_POWEROFF, last_on])
        db.execute("INSERT INTO events(eventid, timestamp) VALUES (?, ?)", [EVT_POWERON, time_now])
        db.commit()
    else:
        print("No offline time detected")
        print("Last online time: %s" % time.ctime(last_on))
        print("App start time: %s" % time.ctime(time_now))


def watchdog():
    """ updates last timestamp """
    res = db.execute("INSERT OR REPLACE INTO timestamps(name, timestamp) VALUES (?, ?)", [LAST_ON, int(time.time())])
    db.commit()

def main():
    dbinit()
    startup()
    while True:
        watchdog()
        time.sleep(5)

if __name__ == "__main__":
    main()
