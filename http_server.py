import socket
import sys
import mimetypes
import os
from subprocess import check_output

WEBROOT="webroot"
log_buffer = sys.stdout

def response_ok(body=b"This is a minimal response", mimetype=b"text/plain"):
    """
    returns a basic HTTP response
    Ex:
        response_ok(
            b"<html><h1>Welcome:</h1></html>",
            b"text/html"
        ) ->
        b'''
        HTTP/1.1 200 OK\r\n
        Content-Type: text/html\r\n
        \r\n
        <html><h1>Welcome:</h1></html>\r\n
        '''
    """

    resp = b"\r\n".join([
                b"HTTP/1.1 200 OK",
                b"Content-Type: " + mimetype,
                b"",
                body,])
    return resp


def parse_request(request):

    """
    Parse the request
    """

    # fall-through values
    method = False
    uri = False
    version = False
    headers = {}

    # request can be multiple lines, split them up
    request_lines = request.splitlines()

    # catch an empty request
    try:
        # decode the first line
        method, uri, version = request_lines[0].split()
        # stuff all the headers into a dict
        headers = {}
        for line in request_lines[1:]:
            if line:
                key, value = line.split(": ")
                headers[key] = value
    except IndexError:
        print("Got empty request!", file=log_buffer)

    # return decoded request
    return (method, uri, version, headers)


def response_method_not_allowed():
    """Returns a 405 Method Not Allowed response"""
    print("Sending method not allowed", file=log_buffer)
    resp = b"\r\n".join([b"HTTP/1.1 405 Method Not Allowed"])
    return resp


def response_not_found():
    """Returns a 404 Not Found response"""
    print("Sending response_not_found", file=log_buffer)
    resp = b"\r\n".join([b"HTTP/1.1 404 Not Found"])
    return resp


def not_implemented():
    """Returns a 404 Not Found response"""
    print("Sending not implemented", file=log_buffer)
    resp = b"\r\n".join([b"HTTP/1.1 501 Not Implemented"])
    return resp


def resolve_uri(uri):
    """
    This method should return appropriate content and a mime type.

    If the requested URI is a directory, then the content should be a
    plain-text listing of the contents with mimetype `text/plain`.

    If the URI is a file, it should return the contents of that file
    and its correct mimetype.

    If the URI does not map to a real location, it should raise an
    exception that the server can catch to return a 404 response.

    Ex:
        resolve_uri('/a_web_page.html') -> (b"<html><h1>North Carolina...",
                                            b"text/html")

        resolve_uri('/images/sample_1.png')
                        -> (b"A12BCF...",  # contents of sample_1.png
                            b"image/png")

        resolve_uri('/') -> (b"images/, a_web_page.html, make_type.py,...",
                             b"text/plain")

        resolve_uri('/a_page_that_doesnt_exist.html') -> Raises a NameError

    Raise a NameError if the requested content is not present
    under webroot.

    Fill in the appropriate content and mime_type give the URI.

    """

    # you have to strip the leading "/" when using strip, else it things it's an absolute path
    effective_uri = os.path.join(WEBROOT,uri.strip("/"))

    # verify the target exists
    if os.path.exists(effective_uri):

        # check to see if it is a directory
        if os.path.isdir(effective_uri):
            print("Requested target is a directory", file=log_buffer)
            mime_type = "text/plain".encode("utf8")
            # lazy approach to get semi legible formatted directory listing
            content = check_output(["ls -l " + effective_uri], shell=True)

        else:
            # target is a file
            # guess_type returns a tuple (mime_type, strict), we only care about mime_type
            mime_type = mimetypes.guess_type(effective_uri)[0]
            if mime_type:
                # for easy reference
                base_type, sub_type = mime_type.split("/")
                if base_type == "text":
                    # text file processing
                    print("Requested target is a non-binary file", file=log_buffer)
                    with open(effective_uri, 'r') as target_file:
                        content = target_file.read()
                    content = content.encode("utf8")
                else:
                    # binary file processing
                    print("Requested target is a binary file", file=log_buffer)
                    with open(effective_uri, 'rb') as target_file:
                        content=target_file.read()
                mime_type = mime_type.encode("utf8")
            else:
                # unknown mime type
                content = False
    else:
        # no such file or directory
        raise NameError

    return content, mime_type


def server(log_buffer=sys.stderr):

    # hack to figure out my outgoing ip address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    myaddr = s.getsockname()[0]
    s.close()

    address = ('0.0.0.0', 10000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("making a server on {0}:{2}, bound to {1}".format(myaddr, *address), file=log_buffer)
    sock.bind(address)
    sock.listen(1)

    try:
        while True:
            print('Waiting for a connection', file=log_buffer)
            conn, addr = sock.accept()  # blocking
            try:
                print('Connection - {0}:{1}'.format(*addr), file=log_buffer)
                request = ''
                while True:
                    # grab the request
                    data = conn.recv(1024)
                    request += data.decode('utf8')
                    if len(data) < 1024:
                        break
                print("Received data", file=log_buffer)
                # parse the request
                method, uri, version, headers = parse_request(request)
                print('Decoded request: method "{}", uri "{}", version "{}"'.format(method, uri, version), file=log_buffer)
                if method:
                    # try to get the requested data
                    try:
                        content, mime_type = resolve_uri(uri)
                        print("Target of request is mime_type of: ",mime_type, file=log_buffer)
                        if mime_type:
                            response = response_ok(content, mime_type)
                        else:
                            response = not_implemented()
                    except NameError:
                        response = response_not_found()
                else:
                    # empty request
                    response = response_method_not_allowed()
                conn.sendall(response)
            finally:
                conn.close()

    except KeyboardInterrupt:
        sock.close()
        return


if __name__ == '__main__':
    server()
    sys.exit(0)


