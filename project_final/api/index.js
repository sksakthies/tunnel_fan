const express = require("express");
const app = express();

app.use(express.json());

// example route
app.get("/api/history", (req, res) => {
  res.json({ ok: true });
});

module.exports = app;