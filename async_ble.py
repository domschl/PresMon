import json
import sys
import time
import logging
import socket
import asyncio
import uuid

from bluepy.btle import Scanner, DefaultDelegate, Peripheral


class AsyncBLEPresence():
    def __init__(self, timeout=60):
        self.log = logging.getLogger("BLE")
        self.devs={}
        self.timeout=timeout

    async def discover(self):
        class ScanDelegate(DefaultDelegate):
            def __init__(self, log):
                self.log = log
                DefaultDelegate.__init__(self)

            def handleDiscovery(self, dev, isNewDev, isNewData):
                # asyncio.task(asyncio.sleep(0.0))
                if isNewDev:
                    self.log.debug("Discovered device {}".format(dev.addr))
                elif isNewData:
                    self.log.debug(
                        "Received new data from {}".format(dev.addr))

        scanner=Scanner().withDelegate(ScanDelegate(self.log))

        scan=[]
        scan += scanner.scan(0.05)

        for dev in scan:
            self.devs[dev.addr]={'last_seen': time.time(), 'rssi': dev.rssi, 'addrType': dev.addrType}
            for (adtype, desc, value) in dev.getScanData():
                self.devs[dev.addr][desc]=value
                await asyncio.sleep(0)

        dels=[]
        for dev in self.devs:
            if time.time()-self.devs[dev]['last_seen']>self.timeout:
                self.log.debug(f'Removing {dev} (T/O)')
                dels += dev
            await asyncio.sleep(0)
        for dev in dels:
            del self.devs[dev]

        xdevs={'cmd': 'ble',
                'devs': self.devs}
        return xdevs
