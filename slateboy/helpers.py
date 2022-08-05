from datetime import datetime, timezone


def getNow():
    dt = datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    cur_ts = utc_time.timestamp()
    return cur_ts
