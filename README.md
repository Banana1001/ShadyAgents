# ShadyAgents
Repository for bunq hackathon 6.0

## Project Structure
This project consists of two main components:
- `backend/`: FastAPI-based backend server
- `web-app/`: Next.js web application

## Backend Setup
1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn fast_server:app --reload --port 8000
```

## Web App Setup
1. Navigate to the web-app directory:
```bash
cd web-app
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The web application will be available at `http://localhost:3000`

## Technologies Used
- Backend:
  - FastAPI
  - Python
  - Uvicorn

- Frontend:
  - Next.js
  - TypeScript
  - Tailwind CSS

## Development
- Backend API runs on port 8000
- Frontend development server runs on port 3000
- API documentation is available at `http://localhost:8000/docs` when the backend server is running
