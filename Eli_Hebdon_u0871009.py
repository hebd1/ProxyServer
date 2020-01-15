# Eli Hebdon u0871009
from socket import *
from urllib.parse import urlparse
import email
import argparse

def begin_listening():
    """
    Create a new TCP proxy server and begin listening on the user specified port
    When a connection is established, the request is parsed and then forwarded to remote server
    """
    #setup command line arguments
    parser = argparse.ArgumentParser(description='Basic web proxy server\nWhen running, enter a valid ' +
                                                 'proxy port number and the proxy will begin listening for incoming connections.')
    parser.parse_args()

    while True:
        try:
            server_port = int(input("Enter a proxy port number: "))
            if 1 <= server_port <= 65535:
                break;
            else:
                raise ValueError
        except ValueError:
            print("This is NOT a VALID port number.")

    #server_port = 1440
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_address = ('localhost', server_port)
    server_socket.bind(server_address)
    server_socket.listen(1)
    print('Listening for incoming connections...')
    while True:
        connection_socket, address = server_socket.accept()
        http_request = connection_socket.recv(1024).decode()
        print(http_request)

        # check for properly formatted HTTP request
        is_valid, response = is_valid_request(http_request)
        if not is_valid:
            connection_socket.send(response.encode())
            connection_socket.close()
            return;

        # format and forward request to remote server
        server_response = forward_request(format_request(http_request))
        print('Sending server response back to client...')
        connection_socket.send(server_response)
        connection_socket.close()


def is_valid_request(http_request):
    """
    Verifies the input http_request is valid
    :param http_request:
    :return: tuple containing http response if invalid and bool indicating whether or not request was valid
    """
    http_response = 'HTTP/1.0'
    # verify GET request
    if http_request.split(' ')[0] != 'GET':
        http_response += ' 501 Not Implemented\n'
        return http_response, False
    # verify absolute URI
    # elif bool(urlparse(http_request.split(' ')[1]).netloc) is False:
    #     http_response += ' 400 Bad Request\n'
    #     return
    # verify HTTP version
    elif http_request.find('HTTP/1.0') == -1:
        http_response += ' 400 Bad Request\n'
        return http_response, False
    else:
        return http_response, True


def forward_request(http_request):
    """
    forwards the input http request to the remote server and waits for response
    port is set to 80 by default if not specified
    :param http_request:
    :return: response from remote server
    """
    port = 80 if http_request[2] is None else http_request[2]
    client_socket = socket(AF_INET, SOCK_STREAM)
    # initiate client-server connection/handshake
    client_socket.connect((http_request[1], port))
    client_socket.send(http_request[0].encode())
    # receive until carriage return / line ends
    server_response = client_socket.recv(1024)
    print('From Server: ', server_response.decode())
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
    print(formatted_request)
    print('Forwarding request to server..\n')
    return formatted_request, host, port


def main():
    begin_listening()


if __name__ == '__main__':
    main()
