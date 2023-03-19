import pygame
from pygame import QUIT

from lock import AutoLockingValue
from network import SocketFactory
from .capture import CaptureStrategyBuilder, AbstractCaptureStrategy
from .encode import EncoderStrategyBuilder, AbstractEncoderStrategy
from .pipeline import EncoderComponent, CaptureComponent, NetworkComponent


class Client:
    def __init__(self, host: str, port: int, width: int, height: int, fps: int, title: str = "Client"):
        """
        The Client class sets up the capture, encoding, and networking pipeline for streaming
        screen captures to a remote server.

        Attributes:
            width (int): The width of the captured screen.
            height (int): The height of the captured screen.
            fps (int): The desired frame rate of the captured screen.
            socket (socket.socket): The TCP socket used for communication with the server.
            pipeline_running (bool): Flag indicating if the pipeline is running.
            capture_component (CaptureComponent): The screen capture component of the pipeline.
            encoder_component (EncoderComponent): The video encoder component of the pipeline.
            network_component (NetworkComponent): The networking component of the pipeline.
        """
        self._title = title
        self._width = width
        self._height = height
        self._fps = fps
        self._running = AutoLockingValue(False)

        self._socket = SocketFactory.connect(host, port)

        # pipeline creation
        self._pipeline_running = False
        self._capture_component = CaptureComponent(
            self._get_default_capture_strategy()
        )
        self._encoder_component = EncoderComponent(
            self._capture_component.output_queue,  # join queues between
            self._get_default_encoder_strategy()
        )
        self._network_component = NetworkComponent(
            self._encoder_component.output_queue,  # join queues between
            self._socket
        )

    def _get_default_capture_strategy(self) -> AbstractCaptureStrategy:
        return CaptureStrategyBuilder \
            .set_strategy_type("mss") \
            .set_option("widht", self._width) \
            .set_option("height", self._height) \
            .set_option("fps", self._fps) \
            .build()

    def _get_default_encoder_strategy(self) -> AbstractEncoderStrategy:
        return EncoderStrategyBuilder \
            .set_strategy_type("av") \
            .set_option("width", self._width) \
            .set_option("height", self._height) \
            .set_option("fps", self._fps) \
            .build()

    def is_running(self):
        return self._running.get()

    def run(self):
        if self._running.get():
            raise RuntimeError("The 'run' method can only be called once")
        self._running.set(True)

        pygame.init()
        screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(self._title)
        clock = pygame.time.Clock()

        while self._running.get():
            for event in pygame.event.get():
                if event.type == QUIT:
                    self._running.set(False)

            screen.fill((0, 0, 0))
            pygame.display.flip()
            clock.tick(self._fps)

        pygame.quit()

    def stop(self):
        self._running.set(True)
        self._capture_component.stop()
        self._encoder_component.stop()
        self._network_component.stop()
