import json
import time
import os
import sys
import platform
import logging
import socket
import errno
import signal 
import atexit
import argparse
import asyncio
import yaml


class AsyncSignalServer:
 
    def __init__(self, loop, config, args, port=17345):
        self.log=logging.getLogger("SigServer")
        self.port=port
        self.loop=loop
        self.args=args
        self.config=config

    async def handle_client(self, reader, writer):
        request = None
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8')
            response = str(eval(request)) + '\n'
            writer.write(response.encode('utf8'))
            await writer.drain()
        writer.close()

    def close_socket(self):
        pass
        # self.sock.close()
        # os.unlink(self.socket_address)

    def signal_handler(self, sig, frame):
        sys.exit(0)  # this will implicitly call atexit() handler close_socket()

    def check_register_socket(self, address):
        try:
            self.loop.create_task(asyncio.start_server(self.handle_client, 'localhost', self.port))
        except Exception as e:
            if getattr(e, 'errno', None) == errno.EADDRINUSE:
                self.log.info(f"Server already runnning.")
                return False
            self.log.warning(f"Can't open server at port {self.port}: {e}")
            return False

        atexit.register(self.close_socket)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        return True



