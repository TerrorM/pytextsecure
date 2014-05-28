#!/usr/bin/env python3

from ws4py.client.threadedclient import WebSocketClient

import config
import base64

class DummyClient(WebSocketClient):
    def opened(self):
        def data_provider():
            for i in range(1, 200, 25):
                yield "#" * i

        self.send(data_provider())

        for i in range(0, 200, 25):
            print(i)
            self.send("*" * i)

    def closed(self, code, reason=None):
        print("Closed down", code, reason)

    def received_message(self, m):
        print(m)
        if len(m) == 175:
            self.close(reason='Bye bye')

if __name__ == '__main__':
    try:
        phone_number = '%2B' + config.getConfigOption('phone_number').decode('utf-8')[1:] + '.1'

        #need to do URL escaping!!
        password = config.getConfigOption('password').decode('utf-8')

        ws = DummyClient('wss://textsecure-service.whispersystems.org/v1/websocket/?user=' + phone_number
                          +'&password=' + password, protocols=['http-only', 'chat'])
        ws.connect()
        ws.run_forever()
        print('here')
    except KeyboardInterrupt:
        ws.close()
