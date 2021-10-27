from datetime import datetime


def print_time_elapsed(func):
    """Print how long executing the function took"""

    def wrapper(*args, **kwargs):
        print(f"Starting `{func.__name__}`. ", end="", flush=True)
        start_time = datetime.now()
        func(*args, **kwargs)
        print(f"\n`{func.__name__}` complete! Time elapsed: {datetime.now() - start_time}")

    return wrapper
