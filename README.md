🚗 DriveSafe-AI

Real-Time Driver Safety & Risk Monitoring System

DriveSafe-AI is an end-to-end intelligent driver safety platform that combines real-time drowsiness detection with environmental risk analysis to proactively prevent road accidents. The system monitors driver alertness using computer vision and augments it with geospatial road-risk intelligence to generate live safety insights.


✨ Key Features
👁️ Driver Drowsiness Detection

>Real-time face monitoring using MediaPipe Face Mesh
>Eye Aspect Ratio (EAR) based blink and drowsiness detection
>Instant audible alerts (beep) on drowsy condition
>Floating camera monitoring mode


🧠 Risk Intelligence Engine

>Combines driver state + road environment risk
>Weighted risk scoring model
>Real-time safety level classification (Safe → Critical)


🗺️ Geospatial Risk Analysis

>Road risk evaluation using OpenStreetMap data
>Intersection, crossing, and signal analysis
>Dynamic risk heatmap generation
>Nearby emergency services detection


📊 Live Dashboard

>Real-time risk meter
>Driver event log
>Heatmap visualization
>Trip lifecycle monitoring


🔗 Telemetry & Event Pipeline

>Trip start/stop tracking
>Event streaming to backend
>Async FastAPI services
>Scalable REST architecture


🏗️ System Architecture
Camera → Frontend (JS) → FastAPI Backend → Risk Engine → Dashboard

Flow:

>Camera captures driver face
>EAR algorithm detects drowsiness
>Frontend sends telemetry events
>Backend computes risk
>Dashboard updates in real time


🧪 Live vs Demo Components
Component	Status
Drowsiness detection	✅ Live
Camera monitoring	✅ Live
Trip & event pipeline	✅ Live
Risk scoring	✅ Live
Heatmap generation	⚡ Semi-live (OSM based)
Dashboard charts	🧪 Demo/seeded
Predictive risk model	🧪 Lightweight heuristic


🛠️ Tech Stack

Backend

Python
FastAPI
AsyncIO
HTTPX
Computer Vision
MediaPipe Face Mesh
OpenCV
EAR algorithm

Frontend

JavaScript
HTML/CSS
REST API integration
Data Sources
OpenStreetMap (Overpass API)


🚀 Getting Started

1️⃣ Clone Repository
git clone https://github.com/<your-username>/DriveSafe-AI.git
cd DriveSafe-AI

2️⃣ Backend Setup
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Open:
http://127.0.0.1:8000/docs

3️⃣ Frontend Setup
cd frontend_static
python -m http.server 5500

Open:
http://localhost:5500


🎯 Demo Flow

Click Start Monitoring
Camera activates
Drowsiness triggers alert
Risk meter updates
Events appear in dashboard


🔒 Design Decisions

Lightweight deterministic logic for real-time reliability
Async backend for low latency
Modular architecture for future ML upgrades
CORS-enabled secure frontend-backend communication


🔮 Future Scope

LSTM-based driver fatigue prediction
Edge deployment for in-vehicle systems
Fleet-level analytics
Mobile app integration
Advanced behavior modeling
