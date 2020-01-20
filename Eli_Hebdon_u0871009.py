# Eli Hebdon u0871009
from socket import *
import email
from urlparse import urlparse
import argparse
import threading


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
        print ("New client connected: " + str(self.addr))

    def is_valid_request(self, http_request):
        """
        Verifies the input http_request is valid
        :param http_request:
        :return: tuple containing http response if invalid and bool indicating whether or not request was valid
        """
        print(str(http_request))
        http_response = 'HTTP/1.0'
        try:
            parsed_url = urlparse(http_request.split(' ')[1])
            all([parsed_url.scheme, parsed_url.netloc])
            # verify GET request
            if http_request.find('HTTP/1.0') == -1:
                http_response += ' 400 Bad Request\r\n'
                return http_response, False
            elif parsed_url.scheme == 'https':
                http_response += ' 400 Bad Request\r\n'
                return http_response, False
            elif http_request.split(' ')[0] != 'GET':
                http_response += ' 501 Not Implemented\r\n'
                return http_response, False
            elif parsed_url.hostname is None:
                http_response += ' 400 Bad Request\r\n'
                return http_response, False
            else:
                return http_response, True
        except ValueError:
            http_response += ' 400 Bad Request\r\n'
            return http_response, False

    def forward_request(self, http_request):
        """
        forwards the input http request to the remote server and waits for response
        port is set to 80 by default if not specified
        :param http_request:
        :return: response from remote server
        """
        port = 80 if http_request[2] is None else http_request[2]
        host = http_request[1]
        client_socket = socket(AF_INET, SOCK_STREAM)
        # initiate client-server connection/handshake
        try:
            client_socket.connect((host, port))
        except:
            # could not connect to remote server
            server_response = "Failed to connect to " + host + " port " + str(port) + ": Connection refused\r\n"
            self.csocket.send(server_response)
            return
        client_socket.send(http_request[0].encode())
        # receive and forward until carriage return / line ends / end of response
        print('Sending server response back to client: ' + str(self.addr))
        while True:
            piece = client_socket.recv(10000)
            if not piece:
                break
            self.csocket.send(piece)
        client_socket.close()
        print('Closed connection with client: ' + str(self.addr))
        self.csocket.close()

        return

    def format_request(self, http_request):
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
            host = headers['Host']
        for key, value in headers.items():
            if key.find('Connection') == -1:
                formatted_request += key + ': ' + value + '\r\n'
        formatted_request += 'Connection: close\r\n\r\n'
        print('Forwarding request to host: ' + host)
        return formatted_request, host, port

    def run(self):
        """
        Creates an instance of the Client Thread class to serve the current client.
        If the request is invalid, a proper error response is sent to the client.
        """
        http_request = self.csocket.recv(2048).decode()
        response, is_valid = self.is_valid_request(http_request)
        if not is_valid:
            self.csocket.send(response)
            print('Closed connection with client ' + str(self.addr))
            self.csocket.close()
        else:
            # format and forward request to remote server
            self.forward_request(self.format_request(http_request))


def begin_listening(server_port):
    """
    Create a new TCP proxy server and begin listening on the user specified port
    When a connection is established, the request is parsed and then forwarded to remote server
    """
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_address = ('localhost', server_port)
    server_socket.bind(server_address)
    print('Listening for incoming connections...')
    while True:
        server_socket.listen(0)
        client_socket, address = server_socket.accept()
        # create a new thread to serve client
        new_thread = ClientThread(address, client_socket)
        new_thread.start()


def main():
    # setup command line arguments
    parser = argparse.ArgumentParser(
        description='Basic web proxy server that forwards client requests to the remote origin server and filters results through virus scanning software.\n')
    parser.add_argument("--port", default=1440, type=int,
                        help="the port number on which the proxy will listen for incoming connections. The default port is 1440")
    args = parser.parse_args()
    begin_listening(args.port)


if __name__ == '__main__':
    main()
