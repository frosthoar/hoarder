import datetime


def now_str() -> str:
    return datetime.datetime.strftime(
        datetime.datetime.now().astimezone(), "%Y-%m-%d %H:%M:%S%z"
    )
