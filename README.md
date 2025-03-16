# SmartFlowPark Documentation 🚀

Welcome to **SmartFlowPark** – an advanced system designed to manage and control the flow of people in theme parks and large venues. By leveraging real-time video analytics, AI-driven monitoring, and robust security protocols, our solution helps prevent overcrowding and ensures safety while optimizing visitor experiences.

## Mission Statement 🎯

Our mission is to empower theme parks and event organizers with state-of-the-art technology that provides:  
- **Real-time monitoring** of crowd movement  
- **Accurate people counting** using AI and computer vision  
- **Proactive management** through early warnings and smart suggestions  

All while maintaining the highest standards in security and system performance.

---

## Table of Contents 📑

- [Monitoring Unit & Client Setup](#monitoring-unit--client-setup)
  - [Client API Key Configuration](#client-api-key-configuration)
- [API Documentation](#api-documentation)
  - [Authentication](#authentication)
  - [Endpoints](#endpoints)
    - [1. /login](#1-login)
    - [2. /app](#2-app)
      - [GET Method](#get-method)
      - [POST Method](#post-method)
      - [PUT Method](#put-method)
      - [DELETE Method](#delete-method)
    - [3. /connect](#3-connect)
    - [4. /update_count](#4-update_count)
  - [API Endpoints Summary 📌](#api-endpoints-summary-)
- [General Notes](#general-notes)
- [Contact & Support](#contact--support)

---

## Monitoring Unit & Client Setup 💻📱

Both the **Monitoring Unit** and **Client** applications are pre-built and available in the [Releases](https://github.com/KienPC1234/SmartFlowPark/releases) section for multiple operating systems.

### Monitoring Unit
- **Purpose:**  
  - Captures video data.
  - Uses YOLO for real-time people detection and counting.
  - Processes and sends data (including images and counts) to the Controller Server.
- **Model Switching:**  
  To change the AI model, simply replace the default `model.pt` with your preferred YOLO model (compatible with Ultralytics). Ensure that the file name is updated accordingly (e.g., `ultralytics`) so that the system recognizes it.

### Client Application
- **Purpose:**  
  - Provides a user-friendly interface to connect securely to the Controller Server.
  - Enables real-time monitoring, management of accounts, zones, and monitors.
- **Client API Key Configuration:**  
  The Client requires an API key to communicate with third-party services (e.g., Google AI). You can set or update the API key and the model type by editing the `settings.json` file located in the project directory.
  
  **Example `settings.json`:**
  ```json
  {
    "api_key": "your_google_ai_api_key",
    "model": "your_selected_model"
  }
  ```
  - **`api_key`:** Replace `"your_google_ai_api_key"` with your actual API key.
  - **`model`:** Set the model you wish to use. This can be the default model or one that you have switched to, as mentioned above.

---

## API Documentation 📡

The SmartFlowPark API is built using Flask and supports JSON-formatted requests and responses. Below, you will find detailed information about each endpoint, including authentication and usage examples.

---

### Authentication 🔐

Most endpoints (except `/connect` and `/update_count`) require a valid authentication token. To obtain a token, use the `/login` endpoint.

#### `/login` Endpoint

- **Method:** `POST`
- **Purpose:** Authenticate users and issue an authentication token.
- **Request Payload:**
  ```json
  {
    "username": "your_username",
    "password": "your_password"
  }
  ```
- **Successful Response:**
  ```json
  {
    "status": "OK",
    "token": "generated_token",
    "permissions": ["monitor", "zone", "home"]
  }
  ```
- **Error Response:**
  ```json
  {
    "status": "ERROR",
    "message": "Invalid credentials"
  }
  ```
Include the returned token in the `Authorization` header for subsequent API calls.

---

### Endpoints

#### 1. `/login`

Used for authentication. See the **Authentication** section above.

---

#### 2. `/app`

A multi-purpose endpoint for managing monitors, zones, and accounts. It supports GET, POST, PUT, and DELETE methods based on the query parameter `type` (which can be one of `monitors`, `zones`, or `accounts`).

**Common Requirements:**
- **Authorization:** Must include a valid token in the `Authorization` header.
- **URL Parameter:** `type` must be one of `monitors`, `zones`, or `accounts`.

##### 2.1 GET Method 🔍

**Purpose:** Retrieve lists and real-time data.

- **For Monitors:**  
  Returns real-time monitor data including `people_count`, captured `image`, status (OK or ERROR), and request delay.
  
  **Example Request:**
  ```sh
  curl -H "Authorization: your_token" "http://server_ip:port/app?type=monitors"
  ```
  
- **For Zones:**  
  Returns zones with aggregated people count computed by a specific mode (`max`, `min`, `avg`, or `sum`).
  
  **Example Request:**
  ```sh
  curl -H "Authorization: your_token" "http://server_ip:port/app?type=zones"
  ```
  
- **For Accounts:**  
  Returns a list of registered accounts.
  
  **Example Request:**
  ```sh
  curl -H "Authorization: your_token" "http://server_ip:port/app?type=accounts"
  ```

##### 2.2 POST Method ➕

**Purpose:** Add new items or perform special actions.

- **For Monitors:**  
  - **Reset Action:**  
    Use the action `reset` to reset the people counter for a specific monitor.
    
    **Request Payload:**
    ```json
    {
      "action": "reset",
      "key": "monitor_key",
      "name": "monitor_name"
    }
    ```
  - **Add Monitor:**  
    Provide monitor details (e.g., key, name) to add a new monitor.
    
    **Example Request:**
    ```json
    {
      "key": "monitor_key",
      "name": "monitor_name",
      "other_details": "..."
    }
    ```
  
- **For Zones:**  
  Create a new zone by providing details like name, aggregation mode, and associated monitors.
  
  **Example Request:**
  ```json
  {
    "name": "Zone A",
    "mode": "max",
    "monitors": ["monitor1", "monitor2"]
  }
  ```
  
- **For Accounts:**  
  Add a new user account with defined permissions.
  
  **Example Request:**
  ```json
  {
    "username": "new_user",
    "password": "secure_password",
    "permissions": ["home", "monitor"]
  }
  ```
On success, these endpoints return an appropriate status code (`201 Created`) and a status message.

##### 2.3 PUT Method 🔄

**Purpose:** Update existing items. The request must include the `id` of the item to update.

- **For Monitors:**  
  Update monitor details by specifying the monitor `id` and fields to update.
  
  **Example Request:**
  ```json
  {
    "id": 1,
    "name": "Updated Monitor Name",
    "other_field": "new_value"
  }
  ```
  
- **For Zones:**  
  Update zone details.
  
  **Example Request:**
  ```json
  {
    "id": 2,
    "name": "Updated Zone Name",
    "mode": "avg"
  }
  ```
  
- **For Accounts:**  
  Update account information (except for immutable fields like IP and port).
  
  **Example Request:**
  ```json
  {
    "id": 3,
    "username": "updated_username",
    "permissions": ["zone", "home"]
  }
  ```

##### 2.4 DELETE Method ❌

**Purpose:** Remove an item from the system by its `id`.

- **Example for Monitor Deletion:**
  ```sh
  curl -X DELETE -H "Authorization: your_token" "http://server_ip:port/app?type=monitors&id=1"
  ```
- **For Zones or Accounts:**  
  Similar DELETE requests apply with the respective `type` parameter and `id`.

---

#### 3. `/connect` 🔌

This endpoint is used by a Monitoring Unit to register its connection with the Controller Server.

- **Method:** `POST`
- **Request Payload:**
  ```json
  {
    "key": "monitor_key",
    "name": "monitor_name"
  }
  ```
- **Success Response:**
  ```json
  {
    "status": "OK",
    "key": "monitor_key",
    "name": "monitor_name"
  }
  ```
- **Error Response:**
  ```json
  {
    "status": "ERROR",
    "message": "Invalid key or name"
  }
  ```

---

#### 4. `/update_count` 🔢

This endpoint allows a Monitoring Unit to update its people count and optionally send an image (Base64 encoded).

- **Method:** `POST`
- **Request Payload:**
  ```json
  {
    "key": "monitor_key",
    "name": "monitor_name",
    "people_count": 25,
    "image": "base64_encoded_string_optional"
  }
  ```
- **Notes:**  
  - The endpoint updates the `last_request` timestamp and calculates the delay from the previous update.
  - If the monitor's counter reset flag is active, the counter resets and a special action response is returned.
- **Success Response:**
  ```json
  {
    "status": "OK"
  }
  ```
- **Reset Action Response:**
  ```json
  {
    "status": "OK",
    "action": "Reset Counter"
  }
  ```

---

### API Endpoints Summary 📌

| Endpoint          | Method(s) | Description                                                     |
|-------------------|-----------|-----------------------------------------------------------------|
| `/login`          | POST      | Authenticate users and provide tokens.                          |
| `/app?type=...`   | GET       | Retrieve data for monitors, zones, or accounts.                 |
| `/app?type=...`   | POST      | Add new monitors, zones, or accounts, or perform special actions. |
| `/app?type=...`   | PUT       | Update existing monitors, zones, or accounts.                   |
| `/app?type=...`   | DELETE    | Delete monitors, zones, or accounts by ID.                        |
| `/connect`        | POST      | Register a Monitoring Unit with the Controller Server.          |
| `/update_count`   | POST      | Update the people count and image data from a Monitoring Unit.    |

---

## General Notes ⚙️

- **Security:**  
  All communication should occur over HTTPS to protect sensitive data. Token-based authentication ensures secure access to the API.
  
- **Permissions:**  
  Endpoints enforce permission checks (e.g., `monitor`, `zone`, `home`). Ensure that tokens are associated with the appropriate permissions.
  
- **Deployment:**  
  The Controller Server can be deployed using `uwsgi` (with the provided `uwsgi.ini`) or any compatible WSGI server via `module main:app`. All server dependencies are listed in `requirements.txt`.
  
- **Real-Time Data:**  
  The system uses timestamps to verify that data from Monitoring Units is fresh. If the time difference exceeds a defined threshold (e.g., 15 seconds), the monitor status will be flagged as ERROR.

---

## Contact & Support 📞

For further questions, contributions, or support, please visit our [GitHub Repository](https://github.com/KienPC1234/SmartFlowPark) and open an issue or contact the development team via email.
