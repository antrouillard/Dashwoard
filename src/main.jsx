import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import CraftingPage from "./pages/CraftingPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PersonnagesPage from "./pages/PersonnagesPage.jsx";
import TodosPage from "./pages/TodosPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<DashboardPage />} />
          <Route path="crafting" element={<CraftingPage />} />
          <Route path="personnages" element={<PersonnagesPage />} />
          <Route path="guilde" element={<PlaceholderPage title="Guilde" />} />
          <Route path="economie" element={<PlaceholderPage title="Economie" />} />
          <Route path="todos" element={<TodosPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
