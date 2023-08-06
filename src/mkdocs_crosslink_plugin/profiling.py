import time
from functools import wraps
# local
from . import info

class Profiler:
    def __init__(self) -> None:
        self.timing_map: dict[str, list[float]] = {}

    def profile(self, f):
        @wraps(f)
        def wrap(*args, **kw):
            start_time = time.monotonic()
            result = f(*args, **kw)
            end_time = time.monotonic()

            name = f.__name__
            time_taken = end_time - start_time
            
            if name in self.timing_map:
                self.timing_map[name].append(time_taken)
            else:
                self.timing_map[name] = [time_taken]

            return result
        return wrap
    
    def log_stats(self):
        for name, time_list in self.timing_map.items():
            count = len(time_list)
            time_sum = sum(time_list)
            message = f"(Profiler) Function '{name}' was called {count} time(s) and took {time_sum:0.2f} seconds."
            if count > 1:
                # Statistics (min, max, avg, mean) only make sense when there are multiple values
                sorted_time = list(sorted(time_list))
                time_avg = sum(time_list)
                time_min = sorted_time[0]
                time_max = sorted_time[-1]

                mid_index = int(count / 2)
                if count % 2 == 0:
                    # Average of the two middle values
                    time_mean = (sorted_time[mid_index-1] + sorted_time[mid_index]) / 2
                else:
                    time_mean = sorted_time[mid_index]

                message += f"\nStats: min={ms(time_min)} max={ms(time_max)} avg={ms(time_avg)} mean={ms(time_mean)}"

            info(message)

def ms(time_in_seconds: float) -> str:
    return f"{round(time_in_seconds * 1_000)}ms"
