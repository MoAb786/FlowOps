# FlowOps - Frontend

The frontend interface for FlowOps, built with [Astro](https://astro.build/) and [Tailwind CSS](https://tailwindcss.com/). It provides an interface for users to submit natural language requests to the FlowOps engine.

---

## 🛠️ Prerequisites

- **Node.js**: `v18.17.1` or higher (Node `v20+` recommended)
- **Package Manager**: `npm`, `pnpm`, or `yarn`

---

## 🚀 Quick Start Setup

### 1. Navigate to the frontend directory
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Start the development server
```bash
npm run dev
```

The application will be running at:
- **Local:** `http://localhost:4321`

---

## 🔗 Backend Connectivity

By default, the client submits requests to the FlowOps backend running on:
```text
http://localhost:8000/requests
```

Make sure your [Backend Server](../backend/README.md) is running prior to submitting requests through the UI.

---

## 📜 Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Starts local development server at `http://localhost:4321` |
| `npm run build` | Builds the production-ready static site into `./dist/` |
| `npm run preview` | Previews the build output locally before deploying |

---

## 📁 Project Structure

```text
frontend/
├── src/
│   ├── layouts/
│   │   └── Layout.astro     # Global layout wrapper with HTML head & meta
│   ├── pages/
│   │   └── index.astro      # Main request submission page & form handling
│   └── styles/
│       └── global.css       # Tailwind CSS & custom design tokens
├── astro.config.mjs         # Astro configuration & Vite Tailwind plugin
├── package.json             # Scripts and dependencies
└── tsconfig.json            # TypeScript configuration
```
