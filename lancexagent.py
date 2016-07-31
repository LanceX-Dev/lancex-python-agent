# -*- coding: utf-8 -*-
import socket
import os, os.path
import json
import asyncore
import logging
import threading
import pyinotify

usock="/tmp/lancex-usock"
pythonUsock='/tmp/lancex-python-usock'
lancexPID = '/tmp/lancexd.pid'

class Dispatcher(asyncore.dispatcher):
    """Receives connections and establishes handlers for each client.
    """
    
    def __init__(self, address):
        self.logger = logging.getLogger('Dispatcher')
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(address):
            os.unlink(address)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.logger.debug('binding to %s', self.address)
        self.listen(1)
        return

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        self.logger.debug('handle_accept() -> %s', client_info[1])
        IncomingHandler(sock=client_info[0])
        # We only want to deal with one client at a time,
        # so close as soon as we set up the handler.
        # Normally you would not do this and the server
        # would run forever or until it received instructions
        # to stop.
        #self.handle_close()
        return
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return

handlers={}
def fn(incoming):
    pkt = json.loads(incoming)
    response = json.dumps({'status':'404'}) 
    uri = "/".join(pkt["path"])
    if uri in handlers:
        response = handlers[uri](incoming)
    return response

def registerURI(uri):
    if os.path.exists(usock):
        client = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
        client.connect(usock)
        z={}
        request={'method':'POST'}
        request['uri'] = uri
        request['path'] = ['uris']
        request['usock'] = pythonUsock
        z['module'] = 'IPC'
        z['request'] = json.dumps(request)
        x = json.dumps(z)
        client.send(x.encode('utf-8'))
        y = client.recv(1024)
        client.close()
        print y
        
def handleRequest(uri,cb):
    registerURI(uri)    
    handlers[uri] = cb

class IncomingHandler(asyncore.dispatcher):
    """Handles echoing messages from a single client.
    """
    
    def __init__(self, sock, chunk_size=8192):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('IncomingHandler%s' % str(sock.getsockname()))
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = []
        self.data_read = []
        self.callback = fn
        return
    
    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        self.logger.debug('writable() -> %s', response)
        return response
    
    def handle_write(self):
        """Write as much as possible of the most recent message we have received."""
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('handle_write() -> (%d) "%s"', sent, data[:sent])
        if not self.writable():
            self.handle_close()

    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(self.chunk_size)
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        self.data_read.insert(0, data)
        self.data_to_write.insert(0, fn(self.data_read.pop()))
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

class crashWatch(pyinotify.ProcessEvent):
    def __init__(self, callback):
        self.callback = callback
        with open(lancexPID,"r") as f:
            self.pid = f.read().rstrip('\n')
    def process_IN_MODIFY(self, event):
        if event.pathname == lancexPID:
            with open(lancexPID,"r") as f: 
                read_data = f.read().rstrip('\n')
            if (self.pid !=read_data):
                print "pid %s -> pid %s" % (self.pid , read_data)
                self.pid = read_data
                self.callback()
        
def crashWatchThread(callback):
    # watch manager
    wm = pyinotify.WatchManager()
    wm.add_watch(lancexPID, pyinotify.ALL_EVENTS, rec=True)
    # event handler
    eh = crashWatch(callback)
    # notifier
    notifier = pyinotify.Notifier(wm, eh)
    notifier.loop()
    
def registerHandlers():
    for uri, fn in handlers.items():
        print "register " + uri
        registerURI(uri)

def loop():
    t = threading.Thread(target=crashWatchThread,args=(registerHandlers,))
    t.setDaemon(True)
    t.start()

    logging.basicConfig(level=logging.DEBUG,format='%(name)s: %(message)s',)
    server = Dispatcher(pythonUsock)
    asyncore.loop()
