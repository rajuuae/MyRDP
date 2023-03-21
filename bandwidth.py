import time
from collections import deque
from enum import EnumMeta, Enum
from threading import Lock
from typing import Callable

from enums import Resolution


class BandwidthMonitor:
    """
    A class to monitor the bandwidth of a data using a moving median window.

    Attributes:
        window_size (int): The size of the moving median window in seconds.
        bytes_received (deque): A deque to store the number of bytes received.
        timestamps (deque): A deque to store the timestamps of received bytes.
        lock (Lock): A threading lock for synchronization.
    """

    def __init__(self, window_size: int = 60) -> None:
        """
        Initializes the BandwidthMonitor with the given window size.

        Args:
            window_size (int): The size of the moving median window in seconds. Default is 60 seconds.
        """
        self.window_size = window_size
        self.bytes_received = deque()
        self.timestamps = deque()
        self.lock = Lock()

    def register_received_bytes(self, received_bytes: int) -> None:
        """
        Registers the received bytes and updates the deques accordingly.

        Args:
            received_bytes (int): The number of bytes received.
        """
        with self.lock:
            current_time = time.time()
            self.bytes_received.append(received_bytes)
            self.timestamps.append(current_time)

            while len(self.timestamps) > 0 and current_time - self.timestamps[0] > self.window_size:
                self.timestamps.popleft()
                self.bytes_received.popleft()

    def get_bandwidth(self) -> int:
        """
        Calculates and returns the bandwidth based on the received bytes and the elapsed time.

        Returns:
            float: The bandwidth in bytes per second.
        """
        with self.lock:
            elapsed_time = self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 1
            total_bytes_received = sum(self.bytes_received)
            return int(total_bytes_received / elapsed_time)


class BandwidthCategoryMeta(EnumMeta):
    """
    Metaclass for the BandwidthCategory enumeration.

    This metaclass generates unique bandwidth categories based on the Resolution enumeration
    and additional parameters like frame rate and color depth. The BandwidthCategory enumeration
    members will be sorted in ascending order based on their bandwidth values.

    The metaclass first calculates the unique bandwidth values for all combinations of resolution,
    frame rate, and color depth, taking into account a specified compression ratio. Then, it sorts
    the unique bandwidth values and creates the BandwidthCategory enumeration members accordingly.
    """

    def __new__(mcs, cls, bases, dct):
        # Create a set to store unique bandwidth values
        unique_bandwidths = set()

        # Iterate through the temporary enumeration members
        for resolution in Resolution:
            for fps in (24, 30):
                for color_depth in (16, 32):
                    # Calculate the bandwidth with a given compression_ratio
                    compression_ratio = 0.07  # Adjust this value according to your requirements
                    bandwidth = int(resolution.width * resolution.height * fps * color_depth * compression_ratio / 8)
                    unique_bandwidths.add(bandwidth)

        # Sort the unique bandwidths in ascending order
        sorted_bandwidths = sorted(list(unique_bandwidths))
        for i, bandwidth in enumerate(sorted_bandwidths):
            dct[f"BANDWIDTH_{i}"] = bandwidth

        return super().__new__(mcs, cls, bases, dct)


class BandwidthFormatter:
    @staticmethod
    def format(bandwidth: int):
        if bandwidth < 1000:
            return f"{bandwidth} Bps"
        elif bandwidth < 1000 * 1000:
            return f"{bandwidth / 1000:.0f} Kbps"
        elif bandwidth < 1000 * 1000 * 1000:
            return f"{bandwidth / (1000 * 1000):.0f} Mbps"
        else:
            return f"{bandwidth / (1000 * 1000 * 1000):.0f} Gbps"


class BandwidthCategory(Enum, metaclass=BandwidthCategoryMeta):
    """
    An enumeration representing bandwidth categories based on video characteristics.

    This enumeration is generated by the BandwidthCategoryMeta metaclass, which creates
    enum members for various combinations of video resolutions, frame rates, color depths,
    and compression ratios.
    """

    def to_human_readable(self):
        return BandwidthFormatter.format(self.value)


class BandwidthStateMachine:
    """
    A class to represent a state machine that changes its internal state based on the bandwidth.

    Attributes:
        bandwidth_monitor (BandwidthMonitor): An instance of BandwidthMonitor.
        current_state (BandwidthCategory): The current state of the state machine.
        observers (List[Callable]): A list of observer functions to be called when the state changes.
    """

    def __init__(self):
        """
        Initializes the BandwidthStateMachine with a given BandwidthMonitor instance.
        """
        self.current_state = BandwidthCategory.BANDWIDTH_0
        self.observers = []

    def register_observer(self, observer: Callable):
        """
        Registers an observer function to be called when the state changes.

        Args:
            observer (Callable): The observer function.
        """
        self.observers.append(observer)

    def notify_observers(self):
        """
        Notifies all registered observers of a state change.
        """
        for observer in self.observers:
            observer(self.current_state)

    def update_state(self, bandwidth: int):
        """
        Updates the internal state of the state machine based on the current bandwidth.
        """
        previous_state = self.current_state
        categories = list(BandwidthCategory)

        current_index = categories.index(self.current_state)
        lower_index = max(current_index - 1, 0)
        upper_index = min(current_index + 1, len(categories) - 1)

        if bandwidth < categories[current_index].value:
            self.current_state = categories[lower_index]
        elif bandwidth >= 2 * categories[current_index].value:
            self.current_state = categories[upper_index]

        if self.current_state != previous_state:
            self.notify_observers()

    def get_current_state(self) -> BandwidthCategory:
        """
        Returns the current state of the state machine.

        Returns:
            BandwidthCategory: The current state of the state machine.
        """
        return self.current_state
