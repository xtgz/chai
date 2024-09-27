import time

# use inspect to print the line of code as well?
# caller = inspect.currentframe().f_back
# filename = caller.f_code.co_filename, lineno = caller.f_lineno


def as_minutes(seconds: float) -> float:
    return seconds / 60


class Logger:
    SILENT = 0
    NORMAL = 1
    VERBOSE = 2

    def __init__(self, name: str, mode=VERBOSE, start=time.time()) -> None:
        self.name = name
        self.start = start
        self.mode = int(mode)
        self.debug("logging is working")

    def print(self, msg: str):
        print(f"{self.time_diff():.2f}: [{self.name}]: {msg}")

    def error(self, message):
        self.print(f"[ERROR]: {message}")

    def log(self, message):
        if self.mode >= Logger.NORMAL:
            self.print(f"{message}")

    def debug(self, message):
        if self.mode >= Logger.VERBOSE:
            self.print(f"[DEBUG]: {message}")

    def warn(self, message):
        if self.mode >= Logger.NORMAL:
            self.print(f"[WARN]: {message}")

    def is_verbose(self):
        return self.mode >= Logger.VERBOSE

    def time_diff(self):
        return time.time() - self.start
