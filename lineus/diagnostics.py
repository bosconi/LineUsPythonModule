import lineus
import threading
import json
import time


class Diagnostics(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.my_line_us = lineus.LineUs()
        self.diags = {}
        self.status_callback = None
        self.complete_callback = None

    def on_status(self, callback):
        self.status_callback = callback

    def on_complete(self, callback):
        self.complete_callback = callback

    def run(self):
        self.status('Finding networks')
        self.diags['networks'] = self.my_line_us.get_network_list()
        if self.diags['networks'] is not None:
            self.diags['scanned'] = {}
            networks = self.diags['networks']
            for i in range(0, len(networks)):
                self.status(f'Looking for Line-us on {networks[i]["name"]}')
                line_us_list = self.my_line_us.slow_search(network=i, return_first=False)
                self.diags['scanned'][networks[i]['name']] = line_us_list

        self.status('Looking for mdns Line-us')
        self.diags['mdns'] = self.my_line_us.get_line_us_list()

        self.status('Checking scanned Line-us')
        self.diags['connections_scanned'] = {}
        for network in self.diags['scanned']:
            for line_us in self.diags['scanned'][network]:
                self.status(f'Trying to contact {line_us[0]} by all methods')
                check_result = self.check_line_us(line_us)
                self.diags['connections_scanned'][line_us[0]] = check_result

        self.status('Checking for Line-us found by mdns')
        self.diags['connections_mdns'] = {}
        for line_us in self.diags['mdns']:
            self.status(f'Trying to contact {line_us[0]} by all methods')
            check_result = self.check_line_us(line_us)
            self.diags['connections_mdns'][line_us[0]] = check_result

        if self.complete_callback is not None:
            self.complete_callback(self.diags)

    def check_line_us(self, line_us):
        connection_result = {'info': line_us}
        types = ('DNS', 'mDNS', 'IP')
        for connection_type in range(0, 3):
            success, hello = self.connect_line_us(line_us[connection_type])
            connection_type_name = types[connection_type]
            # print(f'{line_us[0]} via {connection_type_name} is {success}. Hello={str(hello)}')
            connection_result[connection_type_name] = (success, hello)
            time.sleep(2)
        ping = self.my_line_us.ping(line_us[2])
        connection_result['ping'] = ping
        return connection_result

    def connect_line_us(self, line_us):
        success = self.my_line_us.connect(line_us)
        if success:
            return True, self.my_line_us.get_hello_string()
        else:
            return False, {}

    def status(self, message):
        if self.status_callback is not None:
            self.status_callback(message)

    def get_results(self):
        return self.diags


if __name__ == '__main__':

    def done(info):
        print(f'Finished:')
        print(json.dumps(info, indent=4))

    def status(info):
        print(f'Status: {info}')

    d = Diagnostics()
    d.on_complete(done)
    d.on_status(status)
    d.start()
    d.join()
