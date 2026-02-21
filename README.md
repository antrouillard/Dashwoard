# WoW Progress Hub (Front)

Dashboard front-end for the WoW Progress Hub, built with React + Vite, Tailwind, and WarcraftCN UI components.

## Requirements

- Node.js 18+ (LTS recommended)
- pnpm 10+ (preferred) or npm

## Install

```bash
pnpm install
```

If you do not have pnpm:

```bash
npm install -g pnpm
pnpm install
```

## Run (dev)

```bash
pnpm dev
```

Then open http://localhost:5173

## Build

```bash
pnpm build
pnpm preview
```

## Lint

```bash
pnpm lint
```

## Notes

- The UI uses WarcraftCN assets via CSS (border-image backgrounds). Ensure network access to warcraftcn.com.
- Mock data lives in `src/data/mockData.js`.
- Routing is handled by React Router (see `src/main.jsx`).

## Project Structure (key files)

- `src/App.jsx`: App layout + navigation
- `src/pages/DashboardPage.jsx`: Dashboard page
- `src/pages/CraftingPage.jsx`: Crafting page
- `src/components/ui/warcraftcn/*`: WarcraftCN components
- `src/index.css`: Global styles and theme tokens
