# AutoFinQA Frontend

React + Vite interface for AutoFinQA. Since `node_modules` is ignored, your local environment must restore dependencies before running.

## Prerequisites

- Node.js 18.x or newer (20.x LTS recommended)
- npm 9+ (bundled with recent Node.js versions)
- Access to the AutoFinQA backend (defaults to `http://localhost:8000`)

## 1. Clone the repository

```powershell
git clone https://github.com/hardikjain1704/AutoFinQA.git
cd AutoFinQA/frontend
```

If you've already cloned the project, simply change into the `frontend` directory.

## 2. Install dependencies

Because `node_modules` is not committed, install packages locally:

```powershell
npm install
```

This reads `package.json` (and `package-lock.json` if present) to rebuild `node_modules`.

## 3. Configure environment (optional)

The frontend targets `http://localhost:8000` by default. To point at another backend, create a `.env` file next to this README:

```env
VITE_API_BASE_URL=https://your-backend-host
```

Restart the dev server after changing env variables so Vite picks them up.

## 4. Run the development server

```powershell
npm run dev
```

Vite serves the app at <http://localhost:5173>. Keep the FastAPI backend running or API calls will fail.

## 5. Production build (optional)

```powershell
npm run build
npm run preview
```

`npm run build` outputs optimized assets to `dist/`. `npm run preview` serves the built bundle locally for smoke testing.

## Troubleshooting

- Ensure you're on Node ≥18 if installation fails.
- Delete `node_modules` and run `npm install` again to resolve corrupted installs.
- Double-check `VITE_API_BASE_URL` if the UI reports "Network error" when talking to the backend.