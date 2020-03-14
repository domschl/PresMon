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
        request = ""
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8').strip()
            self.log.debug(f"got socket [{request}]")
            if request=='quit':
                response='quitting!'
            else:
                response=f'Error: {request}'
            writer.write(response.encode('utf8'))
            await writer.drain()
        self.log.warning('quit received')
        await asyncio.sleep(0.1)
        writer.close()
        exit(0)

    def close_daemon(self):
        pass
        
    def signal_handler(self, sig, frame):
        sys.exit(0)  # this will implicitly call atexit() handler close_daemon()

    async def check_register_socket(self):
        try:
            reader, writer = await asyncio.open_connection('localhost', self.port)
            message='quit\n'
            self.log.debug(f'Send: {message.strip()}')
            writer.write(message.encode())
            data = await reader.read(100)
            writer.close()
            self.log.debug(f'Received: {data.decode()!r}')
            await asyncio.sleep(1)
            if self.args.kill_daemon is True:
                print("Aborting after sending KILL signal")
                exit(0)
        except Exception as e:
            self.log.debug(f"Reading from socket failed: {e}")

        try:
            # self.server = self.loop.create_task(asyncio.start_server(self.handle_client, 'localhost', self.port))
            self.server = await asyncio.start_server(self.handle_client, 'localhost', self.port)
        except Exception as e:
            # if getattr(e, 'errno', None) == errno.EADDRINUSE:
            #     self.log.info(f"Server already runnning.")
            #     return None
            self.log.warning(f"Can't open server at port {self.port}: {e}")
            return None

        atexit.register(self.close_daemon)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        return self.server



