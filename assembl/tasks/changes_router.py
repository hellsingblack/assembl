import signal
import time

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream

from tornado import web
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado.httpserver import HTTPServer

# Inspired by socksproxy.

context = zmq.Context.instance()
ioloop.install()
io_loop = ioloop.IOLoop.instance()  # ZMQ loop

td = zmq.devices.ThreadDevice(zmq.FORWARDER, zmq.XSUB, zmq.XPUB)
td.connect_in('ipc:///tmp/assembl_changes/0')
td.bind_out('inproc://assemblchanges')
td.setsockopt_in(zmq.IDENTITY, 'SUB')
#td.setsockopt_in(zmq.SUBSCRIBE, "")
td.setsockopt_out(zmq.IDENTITY, 'PUB')
td.start()


class ZMQRouter(SockJSConnection):

    def on_open(self, request):
        self.socket = context.socket(zmq.SUB)
        self.socket.connect('inproc://assemblchanges')
        # TODO: choose discussion.
        self.socket.setsockopt(zmq.SUBSCRIBE, '')
        self.loop = zmqstream.ZMQStream(self.socket, io_loop=io_loop)
        self.loop.on_recv(self.on_recv)

    def on_recv(self, data):
        self.send(data)

    def on_message(self, msg):
        print "got message", msg

    def on_close(self):
        self.loop.stop_on_recv()
        self.socket.close()
        print "closing"


sockjs_router = SockJSRouter(ZMQRouter, io_loop=io_loop)
routes = sockjs_router.urls
web_app = web.Application(routes, debug=False)


def term(*_ignore):
    web_server.stop()
    io_loop.add_timeout(time.time() + 0.3, io_loop.stop)
    io_loop.start() # Let the IO loop finish its work

signal.signal(signal.SIGTERM, term)

web_server = HTTPServer(web_app)
web_server.listen(8080)
try:
    io_loop.start()
except KeyboardInterrupt:
    term()