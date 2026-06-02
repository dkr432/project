# ---------- HTTPS GET (리다이렉트 따라갈 때 사용) ----------
def https_get(url):
    host, path = parse_url(url)
    print(">>> GET 접속 호스트:", host)

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s = ssl.wrap_socket(s, server_hostname=host)

    request = (
        "GET " + path + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    s.write(request.encode())

    response = b""
    while True:
        chunk = s.read(512)
        if not chunk:
            break
        response += chunk
    s.close()
    return response.decode("utf-8", "ignore")
