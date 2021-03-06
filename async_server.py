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


class AsyncSignalServer:
    """ Check if another instance is already running using a socket server. Terminate old instance and
    start new instance (if kill option was not set.) """
    def __init__(self, loop, config, args, port=17345):
        self.log=logging.getLogger("SigServer")
        self.port=port
        self.loop=loop
        self.args=args
        self.config=config
        self.exit_future=self.loop.create_future()

    async def handle_client(self, reader, writer):
        request = ""
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8').strip()
            self.log.debug(f"got socket [{request}]")
            if request=='quit':
                response='quitting!\n'
            elif request=='help':
                response="help: this help\nquit: stop this daemon.\n"
            else:
                response=f'Error: {request} (try: help)\n'
            writer.write(response.encode('utf8'))
            await writer.drain()
        self.log.warning('quit received')
        writer.close()
        self.exit_future.set_result(True)
        self.exit=True

    async def get_command(self):
        ret=await self.exit_future
        return {'cmd': 'quit', 'retstate': ret}

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
            data = await reader.read(100) # until('\n')
            writer.close()
            await asyncio.sleep(1)  # otherwise new instance of keyboard fails
            
            self.log.debug(f'Received: {data.decode()!r}')
            if 'quitting' in data.decode():
                print('Other instance did terminate.')
                self.log.info("Old instance terminated.")
            if self.args.kill_daemon is True:
                print("Exiting after quitting other instance.")
                exit(0)
        except Exception as e:
            self.log.debug(f"Reading from socket failed: {e}")

        try:
            self.server = await asyncio.start_server(self.handle_client, 'localhost', self.port)
        except Exception as e:
            self.log.warning(f"Can't open server at port {self.port}: {e}")
            return None

        atexit.register(self.close_daemon)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        return self.server
