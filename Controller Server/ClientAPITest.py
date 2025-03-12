import requests

# 1️⃣ Đăng nhập để lấy token
login_url = "http://localhost:8080/login"
login_data = {"username": "user1", "password": "12345678"}
login_response = requests.post(login_url, json=login_data)
print(login_response)
if login_response.status_code == 200:
    token = login_response.json().get("token")
    if token:
        headers = {"Authorization": token}

        # 2️⃣ Lấy danh sách máy giám sát
        monitors_response = requests.get("http://localhost:8080/app?type=monitors", headers=headers)
        if monitors_response.status_code == 200:
            monitors = monitors_response.json().get("data", [])
            may1_info = next((m for m in monitors if m["name"] == "may1"), None)
            if may1_info:
                print("🔹 Thông tin máy giám sát may1:", may1_info)
            else:
                print("⚠ Không tìm thấy máy giám sát may1")
        else:
            print("❌ Lỗi khi lấy monitors:", monitors_response.json())

        # 3️⃣ Lấy dữ liệu của zone `nha1`
        zone_response = requests.get("http://localhost:8080/app?type=zones", headers=headers)
        if zone_response.status_code == 200:
            zone_data = zone_response.json().get("data", {})
            print("🏠 Thông tin zone nha1:", zone_data)
        else:
            print("❌ Lỗi khi lấy zone nha1:", zone_response.json())
    else:
        print("❌ Không nhận được token")
else:
    print("❌ Đăng nhập thất bại")
