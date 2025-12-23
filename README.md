# ELD Logs - Trip Planning & HOS Compliance

A full-stack application that takes trip details as inputs and outputs route instructions with compliant ELD (Electronic Logging Device) logs. Built with Django REST Framework backend and Next.js frontend.

## Live Demo

- **Frontend**: [https://eld-logs-spotter.vercel.app](https://eld-logs-spotter.vercel.app)
- **Backend API**: [https://eld-logs.onrender.com/api/](https://eld-logs.onrender.com/api/)
- **API Documentation**: [https://eld-logs.onrender.com/api/docs/](https://eld-logs.onrender.com/api/docs/)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [HOS Regulations Summary](#hos-regulations-summary)
- [Makefile Commands](#makefile-commands)
- [Project Structure](#project-structure)
- [Technical Justifications](#technical-justifications)
- [References](#references)
- [License](#license)

## Overview

ELD Logs is a comprehensive trip planning application designed for property-carrying commercial motor vehicle (CMV) drivers. The application calculates optimal routes while ensuring compliance with Federal Motor Carrier Safety Administration (FMCSA) Hours of Service (HOS) regulations.

**Inputs:**
- Current location
- Pickup location
- Dropoff location
- Current Cycle Used (Hours)

**Outputs:**
- Interactive map showing route with stops and rest locations
- Daily ELD log sheets (automatically filled out and drawn)
- Multiple log sheets for longer trips
- Route summary with distance, duration, and fuel stops

## Features

- **Route Calculation**: Optimal routing using OpenRouteService API
- **HOS Compliance**: Automatic compliance with 70hrs/8days regulations
- **ELD Log Generation**: Automated daily log sheet creation with proper grid drawing
- **Fuel Stop Planning**: Automatic fuel stops every 1,000 miles
- **Pickup/Dropoff Handling**: 1-hour allocation for loading/unloading
- **Real-time Progress**: WebSocket-based progress tracking
- **Map Generation**: Static route map with markers for all stops
- **Cloud Storage**: Maps stored on Cloudinary for reliable delivery
- **Responsive UI**: Modern Next.js frontend with dark theme

## Tech Stack

**Backend:**
- Python 3.14+
- Django 6.x with Django REST Framework
- Django Channels (WebSocket support)
- Celery (Background task processing)
- PostgreSQL (Database)
- Redis (Caching & Message Broker)
- OpenRouteService (Route calculation & Geocoding)
- Pillow (ELD log image generation)
- Cloudinary (Media storage)

**Frontend:**
- Next.js 15 (App Router)
- React 19
- TypeScript
- TanStack Query (Data fetching)
- TanStack Form (Form handling)
- Tailwind CSS 4
- shadcn/ui (UI components)

**Infrastructure:**
- Render.com (Backend hosting)
- Vercel (Frontend hosting)
- Cloudinary (Media storage)
- Docker & Docker Compose (Local development)

## Installation

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Setup (Backend)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/eld-logs.git
   cd eld-logs/eld_logs
   ```

2. **Install uv (Python package manager):**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Create environment file:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Setup PostgreSQL database:**

   ```bash
   # macOS (with Postgres.app or Homebrew)
   psql -c 'CREATE DATABASE eld_db;'
   psql -c "CREATE USER eld_user WITH PASSWORD 'your_password';"
   psql -c 'GRANT ALL PRIVILEGES ON DATABASE eld_db TO eld_user;'
   
   # Linux
   sudo -u postgres psql -c 'CREATE DATABASE eld_db;'
   sudo -u postgres psql -c "CREATE USER eld_user WITH PASSWORD 'your_password';"
   sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON DATABASE eld_db TO eld_user;'
   ```

6. **Run migrations:**

   ```bash
   uv run python manage.py migrate
   ```

7. **Collect static files:**

   ```bash
   uv run python manage.py collectstatic --noinput
   ```

### Local Setup (Frontend)

1. **Navigate to frontend directory:**

   ```bash
   cd eld_logs_frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Create environment file:**

   ```bash
   cat > .env.local << EOF
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
   EOF
   ```

### Docker Setup

1. **Create environment file:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and start all services:**

   ```bash
   docker compose up -d --build
   ```

3. **Run migrations:**

   ```bash
   docker compose exec web python manage.py migrate
   ```

## Usage

### Local Development

1. **Start Redis (required for Celery & Channels):**

   ```bash
   redis-server
   ```

2. **Start the backend (Terminal 1):**

   ```bash
   make run-asgi
   # Or: uv run uvicorn eld_logs.asgi:application --host 0.0.0.0 --port 8000 --reload
   ```

3. **Start Celery workers (Terminal 2):**

   ```bash
   make run-celery
   # Or: uv run celery -A eld_logs worker -l INFO -Q default,maps -c 2
   ```

4. **Start the frontend (Terminal 3):**

   ```bash
   cd eld_logs_frontend && npm run dev
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/
   - API Documentation: http://localhost:8000/api/docs/

### Using tmux (Recommended)

```bash
make dev-tmux
```

## API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/trips/calculate/` | Calculate a new trip route |
| GET | `/api/trips/` | List all trips (paginated) |
| GET | `/api/trips/{id}/` | Get trip details |
| GET | `/api/trips/{id}/status/` | Get trip processing status |
| GET | `/api/trips/{id}/logs/` | List daily logs for a trip |
| GET | `/api/trips/{id}/download-log/?day={n}` | Download daily log image |
| GET | `/api/trips/{id}/download-map/` | Download route map image |
| POST | `/api/trips/{id}/retry-map/` | Retry failed map generation |

**Calculate Trip Request:**

```json
{
  "current_location": "Los Angeles, CA",
  "pickup_location": "Phoenix, AZ",
  "dropoff_location": "Dallas, TX",
  "current_cycle_used": 10
}
```

**Calculate Trip Response:**

```json
{
  "id": 1,
  "status": "processing",
  "message": "Trip calculation started",
  "websocket_url": "wss://eld-logs.onrender.com/ws/trips/1/progress/",
  "polling_url": "/api/trips/1/status/"
}
```

### WebSocket

Connect to real-time progress updates:

```javascript
const ws = new WebSocket('wss://eld-logs.onrender.com/ws/trips/{trip_id}/progress/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.overall_progress);
  console.log('Status:', data.status);
  console.log('Map Status:', data.map_status);
};
```

**WebSocket Message Types:**
- `status` - Current trip status
- `progress` - Progress update during calculation
- `error` - Error notification
- `pong` - Response to ping

## Testing

### Backend Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
uv run pytest route_calculator/tests/test_hos_calculator.py -v
```

### Frontend Testing

```bash
cd eld_logs_frontend

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Deployment

### Backend Deployment (Render.com)

1. **Create a new Web Service on Render:**
   - Connect your GitHub repository
   - Set Root Directory to `eld_logs`
   - Set Build Command: `uv sync`
   - Set Start Command: `uv run gunicorn eld_logs.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

2. **Create a Background Worker for Celery:**
   - Create another service in Render
   - Set Type to "Background Worker"
   - Set Root Directory to `eld_logs`
   - Set Build Command: `uv sync`
   - Set Start Command: `uv run celery -A eld_logs worker -l INFO -Q default,maps -c 2`

3. **Create a PostgreSQL Database:**
   - Create a new PostgreSQL database in Render
   - Copy the Internal Database URL

4. **Create a Redis Instance:**
   - Create a new Redis instance in Render
   - Copy the Internal Redis URL

5. **Set Environment Variables** (for both Web Service and Background Worker):

   | Variable | Value |
   |----------|-------|
   | `DJANGO_SETTINGS_MODULE` | `eld_logs.settings.production` |
   | `SECRET_KEY` | Generate a secure key |
   | `DEBUG` | `False` |
   | `DATABASE_ENGINE` | `postgresql` |
   | `DATABASE_NAME` | From Render PostgreSQL |
   | `DATABASE_USERNAME` | From Render PostgreSQL |
   | `DATABASE_PASSWORD` | From Render PostgreSQL |
   | `DATABASE_HOST` | From Render PostgreSQL |
   | `DATABASE_PORT` | `5432` |
   | `REDIS_URL` | From Render Redis |
   | `ALLOWED_HOSTS` | `eld-logs.onrender.com,.onrender.com` |
   | `CORS_ALLOWED_ORIGINS` | `https://eld-logs-spotter.vercel.app` |
   | `CSRF_TRUSTED_ORIGINS` | `https://eld-logs-spotter.vercel.app,https://eld-logs.onrender.com` |
   | `OPENROUTESERVICE_API_KEY` | Your ORS API key |
   | `CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name |
   | `CLOUDINARY_API_KEY` | Your Cloudinary API key |
   | `CLOUDINARY_API_SECRET` | Your Cloudinary API secret |
   | `STORAGE_BACKEND` | `cloudinary` |

### Frontend Deployment (Vercel)

1. **Import project to Vercel:**
   - Connect your GitHub repository
   - Set Root Directory to `eld_logs_frontend`
   - Framework Preset: Next.js

2. **Set Environment Variables:**

   | Variable | Value |
   |----------|-------|
   | `NEXT_PUBLIC_API_URL` | `https://eld-logs.onrender.com/api` |
   | `NEXT_PUBLIC_WS_URL` | `wss://eld-logs.onrender.com/ws` |

3. **Deploy:**
   - Vercel will automatically deploy on push to main branch

### Cloudinary Setup

1. **Create a Cloudinary account** at [cloudinary.com](https://cloudinary.com)

2. **Get your credentials** from the Dashboard:
   - Cloud Name
   - API Key
   - API Secret

3. **Configure upload presets** (optional):
   - Go to Settings → Upload
   - Create an unsigned upload preset for maps

### Environment Variables Reference

**Backend (Production):**

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (False in production) | Yes |
| `DATABASE_*` | PostgreSQL connection details | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | Yes |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | Yes |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated CSRF trusted origins | Yes |
| `OPENROUTESERVICE_API_KEY` | OpenRouteService API key | Yes |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | Yes |
| `CLOUDINARY_API_KEY` | Cloudinary API key | Yes |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | Yes |
| `STORAGE_BACKEND` | Storage backend (`local` or `cloudinary`) | No |

**Frontend:**

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | Yes |

## HOS Regulations Summary

This application implements FMCSA Hours of Service regulations for property-carrying CMV drivers (49 CFR Part 395).

### Key Limits

| Regulation | Limit | Description |
|------------|-------|-------------|
| Driving Limit | 11 hours | Maximum driving time after 10 consecutive hours off duty |
| Driving Window | 14 hours | Maximum on-duty period in which driving is permitted |
| Rest Break | 30 minutes | Required break after 8 hours of cumulative driving |
| Weekly Limit | 70 hours/8 days | Maximum on-duty time in any 8-day period |
| Off-Duty Requirement | 10 hours | Minimum consecutive off-duty time between shifts |

### Application Assumptions

- Property-carrying driver (not passenger-carrying)
- 70-hour/8-day schedule
- No adverse driving conditions
- Fueling required at least once every 1,000 miles
- 1 hour allocated for pickup operations
- 1 hour allocated for dropoff operations

### Duty Status Types

| Status | Code | Description |
|--------|------|-------------|
| Off Duty | OFF | Driver is relieved of all duty |
| Sleeper Berth | SB | Time spent in sleeper berth |
| Driving | D | Time spent driving CMV |
| On Duty (Not Driving) | ON | Working but not driving |

## Makefile Commands

### Common Commands

| Command | Description |
|---------|-------------|
| `make install` | Install backend dependencies |
| `make run-asgi` | Run backend with ASGI (WebSocket support) |
| `make run-celery` | Run Celery worker |
| `make test` | Run backend tests |
| `make test-cov` | Run tests with coverage |
| `make lint` | Run linters |
| `make format` | Format code |
| `make dev-tmux` | Run full stack in tmux session |

For all commands:

```bash
make help
```

## Project Structure

```
eld-logs/
├── eld_logs/                      # Django backend
│   ├── eld_logs/                  # Project configuration
│   │   ├── settings/              # Settings modules
│   │   │   ├── base.py            # Base settings
│   │   │   ├── local.py           # Local development
│   │   │   └── production.py      # Production settings
│   │   ├── asgi.py                # ASGI configuration
│   │   ├── celery.py              # Celery configuration
│   │   └── urls.py                # URL routing
│   ├── route_calculator/          # Main Django app
│   │   ├── services/              # Business logic
│   │   │   ├── hos_calculator.py  # HOS compliance
│   │   │   ├── log_generator.py   # ELD log generation
│   │   │   ├── map_generator.py   # Route map generation
│   │   │   ├── route_service.py   # Route calculation
│   │   │   └── storage_service.py # Cloud storage
│   │   ├── consumers.py           # WebSocket consumers
│   │   ├── models.py              # Database models
│   │   ├── serializers.py         # API serializers
│   │   ├── tasks.py               # Celery tasks
│   │   └── views.py               # API views
│   ├── manage.py
│   └── pyproject.toml
├── eld_logs_frontend/             # Next.js frontend
│   ├── app/                       # App router pages
│   ├── components/                # React components
│   ├── hooks/                     # Custom hooks
│   ├── lib/                       # Utilities
│   ├── services/                  # Service layer
│   └── package.json
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── README.md
```

## Technical Justifications

### Backend

- **Django REST Framework**: Industry-standard for Python APIs
- **Django Channels**: WebSocket support for real-time updates
- **Celery**: Async task processing for route calculation and map generation
- **PostgreSQL**: Robust relational database
- **Redis**: Message broker and channel layer backend
- **OpenRouteService**: Open-source routing API with geocoding
- **Cloudinary**: Reliable CDN for map image delivery

### Frontend

- **Next.js 15**: React framework with App Router
- **TanStack Query**: Server state management with caching
- **TanStack Form**: Type-safe form handling
- **Tailwind CSS**: Utility-first styling
- **shadcn/ui**: Accessible, customizable components

### Infrastructure

- **Render.com**: Managed platform with WebSocket support
- **Vercel**: Optimized Next.js hosting
- **Cloudinary**: Global CDN for media assets

## References

### FMCSA Regulations

- [Hours of Service Regulations - 49 CFR Part 395](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations)
- [Interstate Truck Driver's Guide to Hours of Service](https://www.fmcsa.dot.gov/sites/fmcsa.dot.gov/files/docs/Drivers%20Guide%20to%20HOS%202015_508.pdf)

### Technical Documentation

- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Next.js Documentation](https://nextjs.org/docs)
- [OpenRouteService API](https://openrouteservice.org/dev/#/api-docs)
- [Cloudinary Documentation](https://cloudinary.com/documentation)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This application is intended for educational and planning purposes. Always verify compliance with current FMCSA regulations and consult with a qualified transportation compliance professional for official recordkeeping.