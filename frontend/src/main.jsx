// main.jsx — the JavaScript entry point.
// It takes our top-level <App /> component and renders it into the #root div
// from index.html. This is boilerplate you write once per app.

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
