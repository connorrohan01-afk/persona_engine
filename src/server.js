import express from "express";
import n8nRouter from "./routes/n8n.js";

const app = express();

// ✅ fixed internal port (do not use process.env.PORT)
const PORT = 3000;

app.use("/api/v1/n8n", n8nRouter);

app.listen(PORT, () => {
  console.log(`Express running on :${PORT}`);
});