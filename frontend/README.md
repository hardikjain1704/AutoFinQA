# AutoFinQA Frontend

Modern web interface for AutoFinQA Financial Document Intelligence system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run development server:
```bash
npm run dev
```

The frontend will open automatically at `http://localhost:3000`

## Backend

Make sure your backend is running:
```bash
uvicorn auto_finQA.router.main:app --port=8000
```

## Build for Production

```bash
npm run build
npm run preview
```
