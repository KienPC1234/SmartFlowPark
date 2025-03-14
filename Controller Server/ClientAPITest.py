import requests

# Bước 1: Đăng nhập để lấy token
login_url = "http://localhost:8080/login"
login_data = {"username": "admin", "password": "12345678"}

response = requests.post(login_url, json=login_data)

if response.status_code == 200:
    token = response.json().get("token")
    print("Login successful, token:", token)

    # Bước 2: Xóa máy giám sát có id = 2
    delete_monitor_url = "http://localhost:8080/app?type=monitors&id=2"
    headers = {"Authorization": token}

    response = requests.delete(delete_monitor_url, headers=headers)
    print("Delete monitor response:", response.status_code, response.text)

else:
    print("Login failed:", response.status_code, response.text)
