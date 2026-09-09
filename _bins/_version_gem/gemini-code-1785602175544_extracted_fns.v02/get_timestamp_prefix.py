def get_timestamp_prefix():
    now = datetime.datetime.now()
    return f"{int(time.time())}_{now.strftime('%Y.%m.%d')}"
