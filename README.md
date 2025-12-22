# ELD Logs - Trip Planning & HOS Compliance

A full-stack application that takes trip details as inputs and outputs route instructions with compliant ELD (Electronic Logging Device) logs. Built with Django REST Framework backend and Next.js frontend.

## Table of Contents

- [ELD Logs - Trip Planning \& HOS Compliance](#eld-logs---trip-planning--hos-compliance)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Feat**Route Calculation**: Optimal routing using OSRM (Open Source Routing Mac**HOS Compliance**: Automatic compliance with 70hrs/8days regula**ELD Log Generation**: Automated daily log sheet creation with proper grid dr**Fuel Stop Planning**: Automatic fuel stops every 1,000 **Pickup/Dropoff Handling**: 1-hour allocation for**Real-time Progress**: WebSocket-based progress tra**Responsive UI**: Modern Next.js frontend with dark theme](#featroute-calculation-optimal-routing-using-osrm-open-source-routing-machos-compliance-automatic-compliance-with-70hrs8days-regulaeld-log-generation-automated-daily-log-sheet-creation-with-proper-grid-drfuel-stop-planning-automatic-fuel-stops-every-1000-pickupdropoff-handling-1-hour-allocation-forreal-time-progress-websocket-based-progress-traresponsive-ui-modern-nextjs-frontend-with-dark-theme)
  - [Tech Stack](#tech-stack)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Local Setup (Backend)](#local-setup-backend)
    - [Local Setup (Frontend)](#local-setup-frontend)
    - [Docker Setup](#docker-setup)
  - [Usage](#usage)
    - [Local Development](#local-development)
    - [Docker Development](#docker-development)
    - [Full Stack Development](#full-stack-development)
  - [API Documentation](#api-documentation)
    - [Endpoints](#endpoints)
    - [WebSocket](#websocket)
  - [Testing](#testing)
    - [Backend Testing](#backend-testing)
    - [Frontend Testing](#frontend-testing)
    - [Docker Testing](#docker-testing)
  - [Deployment](#deployment)
    - [Docker Production Deployment](#docker-production-deployment)
    - [Environment Variables](#environment-variables)
  - [HOS Regulations Summary](#hos-regulations-summary)
    - [Key Limits](#key-limits)
    - [Application Assumptions](#application-assumptions)
    - [Duty Status Types](#duty-status-types)
  - [Makefile Commands](#makefile-commands)
    - [Setup Commands](#setup-commands)
    - [Running Commands](#running-commands)
    - [Testing \& Quality Commands](#testing--quality-commands)
    - [Docker Commands](#docker-commands)
    - [Utility Commands](#utility-commands)
  - [Project Structure](#project-structure)
  - [Technical Justifications](#technical-justifications)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Infrastructure](#infrastructure)
  - [References](#references)
    - [FMCSA Regulations](#fmcsa-regulations)
    - [Technical Documentation](#technical-documentation)
    - [ELD Specifications](#eld-specifications)
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

## Feat**Route Calculation**: Optimal routing using OSRM (Open Source Routing Mac**HOS Compliance**: Automatic compliance with 70hrs/8days regula**ELD Log Generation**: Automated daily log sheet creation with proper grid dr**Fuel Stop Planning**: Automatic fuel stops every 1,000 **Pickup/Dropoff Handling**: 1-hour allocation for**Real-time Progress**: WebSocket-based progress tra**Responsive UI**: Modern Next.js frontend with dark theme

## Tech Stack
   
**Backend:**
- Python 3.12+
- Django 5.x with Django REST Framework
- Django Channels (WebSocket support)
- Celery (Background task processing)
- PostgreSQL (Database)
- Redis (Caching & Message Broker)
- OSRM (Route calculation)
- Pillow (ELD log image generation)

**Frontend:**
- Next.js 16 (App Router)
- React 19
- TypeScript
- TanStack Query (Data fetching)
- TanStack Form (Form handling)
- Tailwind CSS 4
- shadcn/ui (UI components)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Reverse proxy)
- Gunicorn + Uvicorn (ASGI server)

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
   cd eld-logs
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

   **Linux:**

   ```bash
   sudo -u postgres psql -c 'CREATE DATABASE eld_db;'
   sudo -u postgres psql -c 'CREATE USER eld_user WITH PASSWORD "your_password";'
   sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON DATABASE eld_db TO eld_user;'
   ```

   **macOS (with Postgres.app):**

   ```bash
   psql -c 'CREATE DATABASE eld_db;'
   psql -c 'CREATE USER eld_user WITH PASSWORD "your_password";'
   psql -c 'GRANT ALL PRIVILEGES ON DATABASE eld_db TO eld_user;'
   ```

6. **Run migrations:**

   ```bash
   python manage.py migrate
   ```

7. **Collect static files:**

   ```bash
   python manage.py collectstatic --noinput
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
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
   echo "NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws" >> .env.local
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

4. **Create superuser (optional):**

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

## Usage

### Local Development

1. **Start Redis (required for Celery):**

   ```bash
   redis-server
   ```

2. **Start the backend (Terminal 1):**

   ```bash
   make run-asgi
   # Or: uvicorn eld_logs.asgi:application --host 0.0.0.0 --port 8000 --reload
   ```

3. **Start Celery workers (Terminal 2):**

   ```bash
   make run-celery
   # Or: celery -A eld_logs worker -l INFO -Q default,maps -c 2
   ```

4. **Start the frontend (Terminal 3):**

   ```bash
   make run-frontend
   # Or: cd eld_logs_frontend && npm run dev
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/
   - API Documentation: http://localhost:8000/api/docs/
   - Django Admin: http://localhost:8000/admin/

### Docker Development

1. **Start all services:**

   ```bash
   make run-docker
   ```

2. **View logs:**

   ```bash
   make logs
   ```

3. **Stop services:**

   ```bash
   make stop-docker
   ```

### Full Stack Development

**Using tmux (recommended):**

```bash
make dev-tmux
```

**Or run services manually in separate terminals:**

```bash
# Terminal 1: Backend API
make run-asgi

# Terminal 2: Celery Workers
make run-celery

# Terminal 3: Frontend
make run-frontend
```

## API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/trips/calculate/` | Calculate a new trip route |
| GET | `/api/trips/` | List all trips (paginated) |
| GET | `/api/trips/{id}/` | Get trip details |
| GET | `/api/trips/{id}/result/` | Get trip calculation result |
| GET | `/api/trips/{id}/status/` | Get trip processing status |
| GET | `/api/trips/{id}/summary/` | Get trip summary |
| GET | `/api/trips/{id}/logs/` | List daily logs for a trip |
| GET | `/api/trips/{id}/download-log/?day={n}` | Download daily log image |
| GET | `/api/trips/{id}/download-map/` | Download route map image |
| POST | `/api/trips/{id}/retry-map/` | Retry failed map generation |
| DELETE | `/api/trips/{id}/` | Delete a trip |

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
  "websocket_url": "/ws/trips/1/progress/",
  "polling_url": "/api/trips/1/status/"
}
```

### WebSocket

Connect to real-time progress updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/trips/{trip_id}/progress/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.overall_progress);
  console.log('Status:', data.status);
  console.log('Map Status:', data.map_status);
};
```

**WebSocket Message Types:**
- `progress` - Progress update during calculation
- `status` - Status change notification
- `error` - Error notification
- `pong` - Response to ping

## Testing

### Backend Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run tests without slow tests
make test-fast

# Run tests in watch mode
make test-watch
```

### Frontend Testing

```bash
# Run frontend linting
make lint-frontend

# Run TypeScript type checking
make type-check-frontend

# Format frontend code
make format-frontend
```

### Docker Testing

```bash
# Run backend tests in Docker
make test-docker

# Run all quality checks in Docker
make quality-docker
```

## Deployment

### Docker Production Deployment

1. **Configure production environment:**

   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Build and deploy:**

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

3. **Run migrations:**

   ```bash
   docker compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `False` |
| `SECRET_KEY` | Django secret key | Required |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `OSRM_SERVER_URL` | OSRM routing server URL | `http://router.project-osrm.org` |
| `NOMINATIM_USER_AGENT` | User agent for geocoding | `eld-logs-app` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |

**Frontend Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |

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

### Setup Commands

| Command | Description |
|---------|-------------|
| `make install-all` | Install all dependencies (backend + frontend) |
| `make setup-all` | Full setup for both backend and frontend |
| `make setup-local` | Setup backend local development |
| `make setup-frontend` | Setup frontend with environment file |
| `make setup-docker` | Setup Docker environment |

### Running Commands

| Command | Description |
|---------|-------------|
| `make run` | Run Django development server |
| `make run-asgi` | Run with uvicorn (ASGI mode for WebSockets) |
| `make run-celery` | Run Celery worker |
| `make run-frontend` | Run frontend development server |
| `make dev-all` | Show instructions for running all services |
| `make dev-tmux` | Run full stack in tmux session |
| `make docker-all` | Start backend in Docker + frontend locally |

### Testing & Quality Commands

| Command | Description |
|---------|-------------|
| `make test` | Run backend tests |
| `make test-cov` | Run tests with coverage |
| `make lint` | Run backend linters |
| `make lint-frontend` | Run frontend linter |
| `make format` | Format backend code |
| `make format-frontend` | Format frontend code |
| `make quality-all` | Run all quality checks |

### Docker Commands

| Command | Description |
|---------|-------------|
| `make build` | Build Docker images |
| `make run-docker` | Start all Docker services |
| `make stop-docker` | Stop all Docker services |
| `make logs` | View Docker logs |
| `make migrate-docker` | Run migrations in Docker |

### Utility Commands

| Command | Description |
|---------|-------------|
| `make clean-all` | Clean both backend and frontend |
| `make info` | Show project information |
| `make ports` | Check if required ports are available |
| `make generate-secret` | Generate a new Django secret key |

For a complete list of commands, run:

```bash
make help
```

## Project Structure

```
eld-logs/
├── eld_logs/                      # Django project configuration
│   ├── eld_logs/                  # Main project package
│   │   ├── __init__.py
│   │   ├── asgi.py                # ASGI configuration
│   │   ├── celery.py              # Celery configuration
│   │   ├── urls.py                # URL routing
│   │   └── wsgi.py                # WSGI configuration
│   ├── route_calculator/          # Main Django app
│   │   ├── migrations/            # Database migrations
│   │   ├── services/              # Business logic
│   │   │   ├── hos_calculator.py  # HOS compliance logic
│   │   │   ├── log_generator.py   # ELD log image generation
│   │   │   ├── map_generator.py   # Route map generation
│   │   │   └── route_service.py   # Route calculation
│   │   ├── tests/                 # Test suite
│   │   │   ├── test_hos_calculator.py
│   │   │   ├── test_log_generator.py
│   │   │   ├── test_map_generator.py
│   │   │   └── test_route_service.py
│   │   ├── __init__.py
│   │   ├── admin.py               # Django admin configuration
│   │   ├── apps.py                # App configuration
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── models.py              # Database models
│   │   ├── routing.py             # WebSocket routing
│   │   ├── serializers.py         # DRF serializers
│   │   ├── tasks.py               # Celery tasks
│   │   ├── urls.py                # App URL routing
│   │   └── views.py               # API views
│   ├── static/                    # Static files
│   ├── staticfiles/               # Collected static files
│   ├── .env                       # Environment variables
│   ├── .env.example               # Environment template
│   ├── .gitignore                 # Git ignore rules
│   ├── .python-version            # Python version specification
│   ├── db.sqlite3                 # SQLite database (dev)
│   ├── manage.py                  # Django management script
│   ├── pyproject.toml             # Python dependencies (uv)
│   ├── README.md                  # This file
│   ├── requirements.txt           # Python dependencies
│   └── uv.lock                    # Dependency lock file
├── eld_logs_frontend/             # Next.js frontend
│   ├── app/                       # App router pages
│   ├── components/                # React components
│   │   ├── trip-progress.tsx      # Progress tracking component
│   │   └── ...                    # Other components
│   ├── hooks/                     # Custom React hooks
│   │   ├── use-mobile.ts          # Mobile detection hook
│   │   ├── use-toast.ts           # Toast notification hook
│   │   └── use-trip-progress.ts   # Trip progress hook
│   ├── lib/                       # Utilities and API client
│   │   ├── api/                   # API client
│   │   ├── websocket/             # WebSocket utilities
│   │   ├── utils.ts               # Utility functions
│   │   └── node_modules           # Node.js dependencies
│   ├── public/                    # Public assets
│   ├── services/                  # Service layer
│   │   └── tripProgressService.ts # Trip progress service
│   ├── styles/                    # CSS styles
│   ├── .gitignore                 # Git ignore rules
│   ├── bun.lock                   # Bun lock file
│   ├── components.json            # shadcn/ui configuration
│   ├── next.config.mjs            # Next.js configuration
│   ├── package.json               # Node.js dependencies
│   ├── postcss.config.js          # PostCSS configuration
│   └── tsconfig.json              # TypeScript configuration
├── nginx/                         # Nginx configuration
│   └── Dockerfile                 # Nginx Dockerfile
├── docker-compose.yml             # Development Docker Compose
├── docker-compose.prod.yml        # Production Docker Compose
├── Dockerfile                     # Backend Dockerfile
├── Makefile                       # Development commands
└── README.md                      # Main documentation
```

## Technical Justifications

### Backend

**Django REST Framework**: Industry-standard toolkit for building Web APIs in Python. Provides serialization, authentication, and browsable API out of the box.

**Django Channels**: Enables WebSocket support for real-time progress updates during trip calculation. Essential for providing responsive user experience.

**Celery**: Distributed task queue for handling long-running operations (route calculation, map generation) asynchronously. Prevents API timeouts and improves scalability.

**PostgreSQL**: Robust, ACID-compliant relational database. Handles complex queries and provides excellent performance for geospatial data.

**Redis**: In-memory data store used for Celery message broker, Django Channels layer, and caching. Provides low-latency communication between services.

**OSRM (Open Source Routing Machine)**: High-performance routing engine for shortest paths in road networks. Open-source alternative to commercial routing APIs.

**Pillow**: Python Imaging Library for generating ELD log sheet images with precise grid drawing and text rendering.

### Frontend

**Next.js 16 (App Router)**: React framework with server-side rendering, automatic code splitting, and excellent developer experience. App Router provides modern React features.

**TanStack Query**: Powerful data-fetching library with caching, background updates, and optimistic updates. Replaces complex Redux/state management for server state.

**TanStack Form**: Headless form library with built-in validation, type safety, and excellent performance. Integrates seamlessly with Zod for schema validation.

**Tailwind CSS 4**: Utility-first CSS framework enabling rapid UI development with consistent design tokens.

**shadcn/ui**: High-quality, accessible UI components built on Radix UI primitives. Not a component library - components are copied into the project for full customization.

### Infrastructure

**Docker**: Containerization ensures consistent environments across development, testing, and production. Simplifies deployment and scaling.

**Nginx**: High-performance reverse proxy and static file server. Handles SSL termination, load balancing, and WebSocket proxying.

## References

### FMCSA Regulations

- [Hours of Service Regulations - 49 CFR Part 395](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations)
- [Summary of Hours of Service Regulations](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations)
- [Interstate Truck Driver's Guide to Hours of Service](https://www.fmcsa.dot.gov/sites/fmcsa.dot.gov/files/docs/Drivers%20Guide%20to%20HOS%202015_508.pdf)

### Technical Documentation

- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Next.js Documentation](https://nextjs.org/docs)
- [TanStack Query](https://tanstack.com/query/latest)
- [TanStack Form](https://tanstack.com/form/latest)
- [OSRM API Documentation](http://project-osrm.org/docs/v5.24.0/api/)
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)

### ELD Specifications

- [ELD Technical Specifications (Appendix A)](https://www.fmcsa.dot.gov/regulations/rulemaking/2015-24014)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This application is intended for educational and planning purposes. Always verify compliance with current FMCSA regulations and consult with a qualified transportation compliance professional for official recordkeeping.