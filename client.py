import pygame
from pygame import QUIT

from connection import ReconnectingClientConnection
from lock import AutoLockingValue
from pipeline import EncoderComponent, CaptureComponent, SocketWriterComponent, CaptureEncodeNetworkPipeline
from pread import SocketDataReader
from pwrite import SocketDataWriter


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
            network_component (SocketWriterComponent): The networking component of the pipeline.
        """
        self._title = title
        self._width = width
        self._height = height

        self._fps = fps
        self._running = AutoLockingValue(False)

        self._connection = ReconnectingClientConnection(host, port)
        self._socket_reader = SocketDataReader(self._connection)
        self._socket_writer = SocketDataWriter(self._connection)
        self._pipeline = CaptureEncodeNetworkPipeline(self._socket_writer, fps)

    def is_running(self):
        return self._running.get()

    def run(self):
        if self._running.get():
            raise RuntimeError("The 'run' method can only be called once")
        self._running.set(True)
        self._connection.start()
        self._pipeline.start()

        pygame.init()
        screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(self._title)
        clock = pygame.time.Clock()

        while self._running.get():
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.stop()
                    break

            screen.fill((0, 0, 0))
            pygame.display.flip()
            clock.tick(self._fps)

        pygame.quit()

    def stop(self):
        self._connection.stop()
        self._pipeline.stop()
        self._running.set(False)


HOST = "127.0.0.1"
PORT = 8085
FPS = 25

if __name__ == "__main__":
    client = Client(HOST, PORT, 200, 200, FPS)
    client.run()
