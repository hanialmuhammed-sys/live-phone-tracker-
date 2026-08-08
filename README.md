# 📍 Live Phone Tracker

A full-stack real-time phone and family location tracking web application built with **Python, Flask, Flask-SocketIO, JavaScript, Leaflet, and SQLite/PostgreSQL**.

The application allows users to share their live GPS location, view family members on an interactive map, monitor travel history, create geofences, receive notifications, and trigger emergency SOS alerts.

---

## 🚀 Features

### 📍 Live Location Tracking
- Real-time GPS location tracking
- Browser-based Geolocation API
- Automatic location updates
- Live marker movement on the map

### 🗺️ Interactive Map
- Leaflet.js integration
- OpenStreetMap map tiles
- Custom user markers
- Location information panels
- Live map updates

### 👨‍👩‍👧 Family Groups
- Create family groups
- Join families using invite codes
- Multiple family members
- Member status tracking
- Family management and roles

### 🔐 Authentication
- User registration
- Login/logout
- Password hashing
- Session management
- Protected dashboard

### 🛣️ Route History
- Store historical GPS locations
- Draw travel routes
- View previous movements
- Persistent location data

### 🏠 Geofencing
- Create safe places
- Custom geofence radius
- Entry detection
- Exit detection
- Geofence notifications

### 🚨 SOS Emergency System
- Emergency SOS button
- Sends current location
- Family emergency notifications
- SOS history
- Emergency status tracking

### 🔔 Notifications
- Geofence alerts
- SOS alerts
- Battery notifications
- Family activity notifications
- Real-time notification updates

### 📊 Travel Analytics
- Distance travelled
- Average speed
- Maximum speed
- Moving time
- Stationary time
- Visited places

### ▶️ Route Replay
- Select a previous date
- Replay recorded journeys
- Animated map marker
- Playback controls
- Timeline navigation
- Playback speed controls

### 👥 Family Administration
- Owner/Admin/Member roles
- Invite members
- Remove members
- Change member roles
- Family settings
- Activity logs

---

# 🛠️ Technology Stack

## Backend

- Python
- Flask
- Flask-SocketIO
- Flask-SQLAlchemy
- Flask-Login
- Flask-Bcrypt

## Frontend

- HTML5
- CSS3
- JavaScript
- Leaflet.js

## Database

- SQLite for local development
- PostgreSQL for production

## Mapping

- Leaflet.js
- OpenStreetMap

## Communication

- REST APIs
- WebSockets
- Socket.IO

---

# 📂 Project Structure

```text
live-phone-tracker/
│
├── app.py
├── config.py
├── extensions.py
├── models.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── tracking.py
│   ├── family.py
│   └── dashboard.py
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── phone.html
│   ├── family_setup.html
│   └── replay.html
│
├── static/
│   ├── style.css
│   └── script.js
│
└── instance/
    └── tracker.db
```

> The `instance/` directory is used for local development and should not be committed to GitHub when using SQLite.

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/live-phone-tracker.git
```

```bash
cd live-phone-tracker
```

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
```

Never commit `.env` to GitHub.

---

## 5. Run the application

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 📱 Phone Tracking

To share a phone's GPS location:

1. Open the tracking page on the phone.
2. Allow location access.
3. Keep the tracking page open.
4. The phone periodically sends its GPS coordinates to the Flask server.
5. The dashboard receives the location through the backend.
6. The marker is updated on the map.

For testing on a local network, the computer and phone need to be connected to the same network.

---

# 🔄 Application Architecture

```text
                  📱 Mobile Browser
                        │
                        │ GPS
                        ▼
                ┌─────────────────┐
                │   Flask API     │
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        PostgreSQL/SQLite       Socket.IO
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
                🖥️ Web Dashboard
                         │
                         ▼
                   🗺️ Leaflet Map
```

---

# 🔌 Main API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Home page |
| `/login` | GET/POST | User login |
| `/register` | GET/POST | User registration |
| `/logout` | GET | Logout |
| `/dashboard` | GET | Main tracking dashboard |
| `/phone` | GET | Phone GPS tracking page |
| `/location` | GET | Get latest location |
| `/location` | POST | Update phone location |
| `/history` | GET | Location history |
| `/geofence` | GET/POST | Manage geofences |
| `/sos` | POST | Trigger emergency alert |
| `/notifications` | GET | Get notifications |
| `/replay/<date>` | GET | Get route data for replay |
| `/analytics/today` | GET | Daily travel statistics |

---

# 🔐 Security

The application is designed with security considerations including:

- Password hashing
- Session-based authentication
- Protected routes
- Environment variables for secrets
- User/family authorization
- Input validation
- HTTPS for production deployment

Location data should only be shared with users who have been explicitly authorized.

---

# 🧪 Testing

Before deployment, test:

```text
Registration
    ↓
Login
    ↓
Dashboard
    ↓
Phone GPS
    ↓
Live Location
    ↓
Database
    ↓
Family Sharing
    ↓
Geofence
    ↓
Notification
    ↓
SOS
    ↓
Route Replay
```

---

# ☁️ Deployment

The application can be deployed using services such as **Render**.

Production architecture:

```text
Internet
   │
   ▼
Render
   │
   ├── Flask Application
   │
   ├── Flask-SocketIO
   │
   └── PostgreSQL
        │
        ▼
   Location Data
```

Environment variables should be configured through the hosting provider rather than committed to the repository.

---

# 🗺️ Roadmap

### Version 1.0

- [x] User authentication
- [x] Live GPS tracking
- [x] Interactive map
- [x] Route history
- [x] Family groups
- [x] Geofencing
- [x] SOS system
- [x] Notifications
- [x] Travel analytics
- [x] Route replay
- [x] Family administration

### Version 2.0

- [ ] Native Android application
- [ ] Background GPS tracking
- [ ] Push notifications
- [ ] Advanced location privacy controls
- [ ] PostgreSQL production optimization
- [ ] Redis for scalable real-time communication
- [ ] Docker deployment
- [ ] Automated testing
- [ ] CI/CD pipeline
- [ ] Custom domain

---



# ⚠️ Privacy Notice

This application handles sensitive location information.

Only track devices and users who have explicitly given permission to share their location. Do not use the application to secretly monitor another person's device.

Location data should be protected and only accessible to authorized users.

---

# 👨‍💻 Author

**Hani Al Muhammed**

B.Tech CSE — Cyber Security

Interested in:

- Cybersecurity
- Full-Stack Development
- Python
- Web Technologies
- Real-Time Systems

---

# ⭐ If You Like This Project

Consider giving the repository a ⭐ on GitHub.
