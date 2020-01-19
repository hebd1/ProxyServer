# Eli Hebdon u0871009
from socket import *
import email
from urlparse import urlparse
import argparse


def begin_listening(server_port):
    """
    Create a new TCP proxy server and begin listening on the user specified port
    When a connection is established, the request is parsed and then forwarded to remote server
    """
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_address = ('localhost', server_port)
    server_socket.bind(server_address)
    server_socket.listen(1)
    print('Listening for incoming connections...')
    while True:
        connection_socket, address = server_socket.accept()
        http_request = connection_socket.recv(8192).decode()
        print('Connected to client ' + str(connection_socket.getpeername()[1]) + '...')

        # check for properly formatted HTTP request
        response, is_valid = is_valid_request(http_request)
        if not is_valid:
            connection_socket.send(response.encode())
            print('Closed connection with client ' + str(connection_socket.getpeername()[1]) + '...')
            connection_socket.close()
            continue;

        # format and forward request to remote server
        server_response = forward_request(format_request(http_request))
        print('Sending server response back to client ' + str(connection_socket.getpeername()[1]) + '...')
        connection_socket.send(server_response)
        print('Closed connection with client ' + str(connection_socket.getpeername()[1]) + '...')
        connection_socket.close()


def is_valid_request(http_request):
    """
    Verifies the input http_request is valid
    :param http_request:
    :return: tuple containing http response if invalid and bool indicating whether or not request was valid
    """
    http_response = 'HTTP/1.0'
    try:
        parsed_url = urlparse(http_request)
        all([parsed_url.scheme, parsed_url.netloc])
        # verify GET request
        if http_request.find('HTTP/1.0') == -1:
            http_response += ' 400 Bad Request\r\n'
            return http_response, False
        elif http_request.split(' ')[0] != 'GET':
            http_response += ' 501 Not Implemented\r\n'
            return http_response, False
        else:
            return http_response, True
    except ValueError:
        http_response += ' 400 Bad Request\r\n'
        return http_response, False



def forward_request(http_request):
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
        return server_response.encode()
    client_socket.send(http_request[0].encode())
    # receive until carriage return / line ends / end of response
    response = list()
    while True:
        piece = client_socket.recv(10000)
        if not piece:
            break;
        response.append(piece)
    server_response = ''.join(response)
    client_socket.close()
    return server_response


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
        host = headers['Host']
    for key, value in headers.items():
        if key.find('Connection') == -1:
            formatted_request += key + ': ' + value + '\r\n'
    formatted_request += 'Connection: close\r\n\r\n'
    print('Forwarding request to server..\n')
    return formatted_request, host, port


def main():
    # setup command line arguments
    parser = argparse.ArgumentParser(description='Basic web proxy server that forwards client requests to the remote origin server and filters results through virus scanning software.\n')
    parser.add_argument("--port", default=1440, type=int, help="the port number on which the proxy will listen for incoming connections. The default port is 1440")
    args = parser.parse_args()
    begin_listening(args.port)


if __name__ == '__main__':
    main()
