const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Acts as a proxy server between frontend and FastAPI backend
app.use(cors());
app.use(express.json());

// FastAPI backend URL
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    const response = await axios.get(`${FASTAPI_URL}/health`);
    res.json(response.data);
  } catch (error) {
    res.status(503).json({
      status: 'error',
      message: 'FastAPI backend is not available',
      error: error.message
    });
  }
});

// Chat endpoint - proxy to FastAPI
app.post('/api/chat', async (req, res) => {
  try {
    //receive prompt and model from frontend
    const { prompt, model } = req.body;

    if (!prompt) {
      return res.status(400).json({
        success: false,
        error: 'Prompt is required' //prompt is mandatory
      });
    }

    //forward request to FastAPI (axious POST)
    const response = await axios.post(`${FASTAPI_URL}/api/chat`, {
      prompt,
      model: model || 'openai/gpt-4o-mini' //default model if not provided
    });
    // Sends to: FastAPI on port 8000 (default)
    // Endpoint: http://localhost:8000/api/chat
    // Method: POST
    // Payload: Same as received from frontend

    // if FastAPI responds with 200
    res.json(response.data); // response is captured here from FastAPI and sent back to frontend (200)
  } catch (error) {
    if (error.response) {
      // FastAPI returned an error (403 or 503 - Jailbreak detected or any other error)
      res.status(error.response.status).json(error.response.data); //forwards error from FastAPI to frontend
    } else {
      // Network or other error (503) or server down
      res.status(503).json({
        success: false,
        error: 'Failed to connect to AI service',
        message: error.message
      });
    }
  }
});

// Scan endpoint - proxy to FastAPI
app.post('/api/scan', async (req, res) => {
  try {
    const { prompt } = req.body;

    if (!prompt) {
      return res.status(400).json({
        error: 'Prompt is required'
      });
    }

    const response = await axios.post(`${FASTAPI_URL}/api/scan`, { prompt });
    res.json(response.data);
  } catch (error) {
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(503).json({
        error: 'Failed to scan prompt',
        message: error.message
      });
    }
  }
});

// Stats endpoint - proxy to FastAPI
app.get('/api/stats', async (req, res) => {
  try {
    const response = await axios.get(`${FASTAPI_URL}/api/stats`);
    res.json(response.data);
  } catch (error) {
    res.status(503).json({
      error: 'Failed to get stats',
      message: error.message
    });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: err.message
  });
});

app.listen(PORT, () => {
  console.log('='.repeat(80));
  console.log('🚀 Node.js Backend Server Started');
  console.log('='.repeat(80));
  console.log(`✓ Server running on port ${PORT}`);
  console.log(`✓ FastAPI backend: ${FASTAPI_URL}`);
  console.log('✓ Endpoints:');
  console.log(`  - GET  http://localhost:${PORT}/health`);
  console.log(`  - POST http://localhost:${PORT}/api/chat`);
  console.log(`  - POST http://localhost:${PORT}/api/scan`);
  console.log(`  - GET  http://localhost:${PORT}/api/stats`);
  console.log('='.repeat(80));
});