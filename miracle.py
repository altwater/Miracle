import errno
import functools
import tornado.ioloop as ioloop
import socket
from scapy import *
import Queue
import time
import sys
from threading import Timer

from  OpenFlow import libopenflow as of
import OpenFlow.ofp_handler as ofp_handler
import database.timer_list as timer_list
sys.path.append('.')
"""
TODO:Define the OpenFlow packets handler functions
Author:Licheng
Time:2014/5/5

"""

fd_map = {}
message_queue_map = {}

global ready
ready = 0
handler = { 0:ofp_handler.hello_handler,
            1:ofp_handler.error_handler,
            2:ofp_handler.echo_request_handler,
            3:ofp_handler.echo_reply_handler,
            4:ofp_handler.echo_reply_handler,
            5:ofp_handler.features_request_handler,
            6:ofp_handler.features_reply_handler,
            7:ofp_handler.get_config_request_handler,
            8:ofp_handler.get_config_reply_handler,
            9:ofp_handler.set_config_handler,
            10:ofp_handler.packet_in_handler,
            11:ofp_handler.flow_removed_handler,
            12:ofp_handler.port_status_handler,
            13:ofp_handler.packet_out_handler,
            14:ofp_handler.flow_mod_handler,
            15:ofp_handler.port_mod_handler,
            16:ofp_handler.stats_request_handler,
            17:ofp_handler.stats_reply_handler,#body
            18:ofp_handler.barrier_request_handler,
            19:ofp_handler.barrier_reply_handler,
            20:ofp_handler.queue_get_config_request_handler,
            21:ofp_handler.queue_get_config_reply_handler,
            24:ofp_handler.cfeatrues_reply_handler #body
            }

def handle_connection(connection, address):
        print ">>>1 connection,", connection, address
def client_handler(address, fd, events):
    sock = fd_map[fd]
    if events & io_loop.READ:
        data = sock.recv(1024)
        if data == '':
            print ">>>Connection dropped"
            io_loop.remove_handler(fd)
        if len(data)<8:
            print ">>>Length of packet is too short"
        else:
            if len(data)>=8:
                rmsg = of.ofp_header(data[:8])
                #rmsg.show()
                body = data[8:]
            if rmsg.type == 0:
                msg = handler[0] (data)
                message_queue_map[sock].put(str(msg))
                message_queue_map[sock].put(str(of.ofp_header(type = 5)))
            elif rmsg.type == 6:
                handler[6] (data,fd)
            else:
                msg = handler[rmsg.type] (data,fd)
                message_queue_map[sock].put(str(msg))
            io_loop.update_handler(fd, io_loop.WRITE)

    if events & io_loop.WRITE:
        try:
            next_msg = message_queue_map[sock].get_nowait()
        except Queue.Empty:
            #print "%s queue empty" % str(address)
            io_loop.update_handler(fd, io_loop.READ)
        else:
            #print 'sending "%s" to %s' % (of.ofp_header(next_msg).type, address)
            sock.send(next_msg)

def connection_up(sock, fd, events):
    #print fd, sock, events
    try:
        connection, address = sock.accept()
    except socket.error, e:
        if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise
        return
    connection.setblocking(0)
    handle_connection(connection, address)
    fd_map[connection.fileno()] = connection
    connection_handler = functools.partial(client_handler, address)
    io_loop.add_handler(connection.fileno(), connection_handler, io_loop.READ)
    print ">>>connection_up: new switch", connection.fileno(), connection_handler
    message_queue_map[connection] = Queue.Queue()

def new_sock(block):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(block)
    return sock

if __name__ == '__main__':
    sock = new_sock(0)
    sock.bind(("", 6633))
    sock.listen(6633)
    
    io_loop = ioloop.IOLoop.instance()
    #callback = functools.partial(connection_ready, sock)
    callback = functools.partial(connection_up, sock)
    print sock, sock.getsockname()
    io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()        
        print ">>>quit" 

        for timer in timer_list.timer_list:
            timer.cancel()

        sys.exit(0)
