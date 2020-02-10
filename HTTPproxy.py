# Eli Hebdon u0871009
from StringIO import StringIO
from httplib import HTTPResponse
from socket import *
import email
from urlparse import urlparse
from optparse import OptionParser
import threading
import io
import hashlib
import requests
import urllib3

#global variables
proxy_port = 2100
apikey = "0b4062da626725e5bb400ea46d73d639954348ed774fb45770f8eafe415e8704"


class ClientThread(threading.Thread):

    def __init__(self, client_address, client_socket):
        """
        Initializes a new instance of the Client Thread class.
        :param client_address:
        :param client_socket:
        """
        threading.Thread.__init__(self)
        self.csocket = client_socket
        self.addr = client_address

    def run(self):
        """
        Creates an instance of the Client Thread class to serve the current client.
        If the request is invalid, a proper error response is sent to the client.
        """
        try:
            http_request = self.csocket.recv(2048)
            response, is_valid = is_valid_request(http_request)
            if not is_valid:
                self.csocket.send(response.encode())
            else:
                # format and forward request to remote server
                server_response = forward_request(format_request(http_request))
                # filter malware from response
                if contains_malware(server_response):
                    server_response = "HTTP/1.0 200 OK\r\n\r\ncontent blocked\r\n"
                print('Sending server response back to client: ' + str(self.addr))
                bytes = io.BytesIO(server_response)
                while True:
                    chunk = bytes.read(10000)
                    if not chunk:
                        break
                    self.csocket.send(chunk)
            # complete transaction with client and close connection
            print('Closed connection with client ' + str(self.addr))
            self.csocket.close()
        except:
            print('Closed connection with client: ' + str(self.addr))
            self.csocket.close()
            return


class HTTPObject():
    def __init__(self, response_str):
        self._file = StringIO(response_str)
    def makefile(self, *args, **kwargs):
        return self._file

def filter_malware(response_str):
    global apikey
    source = HTTPObject(response_str)
    http_response = HTTPResponse(source)
    http_response.begin()
    url = 'https://www.virustotal.com/vtapi/v2/file/report'
    content = http_response.read(len(response_str))
    hash = hashlib.md5(content).hexdigest()
    params = {'apikey': apikey, 'resource': hash}
    response = requests.get(url, params=params)
    return response

def contains_malware(response_str):
    virus_total_response = filter_malware(response_str)
    if "true" in virus_total_response.text:
        return True
    else:
        return False

def is_valid_request(http_request):
    """
    Verifies the input http_request is valid
    :param http_request:
    :return: tuple containing http response if invalid and bool indicating whether or not request was valid
    """
    http_response = 'HTTP/1.0'
    try:
        request_line, headers_raw = http_request.split('\r\n', 1)
        headers = dict(email.message_from_string(headers_raw))
        parsed_url = urlparse(request_line.split(' ')[1])
        all([parsed_url.scheme, parsed_url.netloc])
        if request_line.split(' ')[2] != 'HTTP/1.0':
            http_response += ' 400 Bad Request\r\n\r\n'
            return http_response, False
        if parsed_url.scheme == 'https':
            http_response += ' 400 Bad Request\r\n\r\n'
            return http_response, False
        elif request_line.split(' ')[0] != 'GET':
            http_response += ' 501 Not Implemented\r\n\r\n'
            return http_response, False
        elif parsed_url.hostname is None:
            http_response += ' 400 Bad Request\r\n\r\n'
            return http_response, False
        else:
            return http_response, True
    except:
        http_response += ' 400 Bad Request\r\n\r\n'
        return http_response, False


def format_request(http_request):
    """
    formats the input http request to the relative URL + HOST header format
    :param http_request:
    :return: tuple containing the formatted request, host, and port if specified
    """
    request_line, headers_alone = http_request.split('\r\n', 1)
    headers = dict(email.message_from_string(headers_alone))
    url = urlparse(request_line.split(' ')[1])
    port = url.port
    formatted_request = 'GET ' + url.path + ' HTTP/1.0\r\n'
    if 'Host' not in headers.keys():
        formatted_request += 'Host: ' + url.hostname + '\r\n'
        host = url.hostname
    else:
        host = headers['Host'].split(":")[0]
    for key, value in headers.items():
        # ignore connection headers
        if key.find('Connection') == -1:
            formatted_request += key + ': ' + value + '\r\n'
    formatted_request += 'Connection: close\r\n\r\n'
    print('Forwarding request to host: ' + host)
    return formatted_request, host, port


def forward_request(http_request):
    """
    forwards the input http request to the remote server and waits for response
    port is set to 80 by default if not specified
    :param http_request:
    :return: response from remote server
    """
    port = 80 if http_request[2] is None else http_request[2]
    host = http_request[1]
    # initiate client-server connection/handshake
    try:
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((host, port))
    except:
        # could not connect to remote server
        server_response = "HTTP/1.0 400 Bad Request\r\n\r\nFailed to connect to " + host + " port " + str(port) + ": Connection refused\r\n"
        return server_response
    client_socket.send(http_request[0].encode())
    # receive and forward until carriage return / line ends / end of response
    print('Downloading requested item from host: ' + host)
    server_response = recvall(client_socket, 10000)
    print('item downloaded: ' + host)
    client_socket.close()
    return server_response



def recvall(socket, size):
    bytes = []
    while True:
        piece = socket.recv(size)
        if not piece:
            break
        bytes.append(piece)
    return ''.join(bytes)


def begin_listening():
    """
    Create a new TCP proxy server and begin listening on the user specified port
    When a connection is established, the request is parsed and then forwarded to remote server
    """
    global proxy_port
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_address = ('localhost', proxy_port)
    server_socket.bind(server_address)
    print('Listening for incoming connections...')
    while True:
        server_socket.listen(100)
        client_socket, address = server_socket.accept()
        print('New client connected: ' + str(address))
        # create a new thread to serve client
        new_thread = ClientThread(address, client_socket)
        new_thread.start()



def main():
    # setup command line arguments
    urllib3.disable_warnings()
    global proxy_port
    global apikey

    parser = OptionParser()
    parser.add_option("-p", "--port", action="store", dest="proxy_port", help="The port number on which the proxy will listen for incoming connections. The default port is 1440")
    parser.add_option("-k", "--key", action="store", dest="apikey")
    (options, args) = parser.parse_args()
    if options.proxy_port is not None:
        proxy_port = options.proxy_port
    if options.apikey is not None:
        apikey = options.apikey
    begin_listening()


if __name__ == '__main__':
    main()
