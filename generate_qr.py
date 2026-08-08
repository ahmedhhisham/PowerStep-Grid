import qrcode, socket

local_ip = socket.gethostbyname(socket.gethostname())
url = f"http://{local_ip}:8501"
qrcode.make(url).save("dashboard_qr.png")
print(f"امسح الكود للوصول: {url}")