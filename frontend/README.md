# AutoFinQA Frontend

## Prerequisites

- Node.js 18.x or newer 
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

## 3. Run the development server

```powershell
npm run dev
```

Vite serves the app at <http://localhost:5173>. Keep the FastAPI backend running or API calls will fail.

## 5. Production build

```powershell
npm run build
```

`npm run build` outputs optimized assets to `dist/`.

`npm run dev` to start the frontend and open it on website.
