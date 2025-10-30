const express = require('express');
const Anthropic = require('@anthropic-ai/sdk').default;

const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse JSON
app.use(express.json());

// Initialize Anthropic client
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// /build POST route
app.post('/build', async (req, res) => {
  try {
    const { name, spec, tenant_id } = req.body;

    // Validate required fields
    if (!name || !spec || !tenant_id) {
      return res.status(400).json({
        error: 'Missing required fields: name, spec, tenant_id'
      });
    }

    console.log('Processing build request:', { name, tenant_id, spec: spec.substring(0, 100) + '...' });

    // Call Anthropic API
    const message = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 1024,
      messages: [{
        role: 'user',
        content: `Build specification for "${name}":
        
Tenant ID: ${tenant_id}
Specification: ${spec}

Please provide a JSON response with build details and implementation plan.`
      }]
    });

    // Extract the text content from Anthropic response
    const responseText = message.content[0]?.text || '';
    
    // Try to parse as JSON, fallback to structured response
    let jsonResponse;
    try {
      jsonResponse = JSON.parse(responseText);
    } catch (parseError) {
      jsonResponse = {
        name,
        tenant_id,
        spec,
        anthropic_response: responseText,
        build_status: 'processed',
        timestamp: new Date().toISOString()
      };
    }

    console.log('Build request completed successfully');
    res.json(jsonResponse);

  } catch (error) {
    console.error('Build route error:', error.message);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Health check route
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    anthropic_configured: !!process.env.ANTHROPIC_API_KEY
  });
});

// Root route
app.get('/', (req, res) => {
  res.json({ 
    message: 'Express.js Build Server',
    endpoints: [
      'POST /build - Create build with Anthropic AI',
      'GET /health - Health check'
    ]
  });
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`Express server running on port ${port}`);
  console.log(`Anthropic API Key configured: ${!!process.env.ANTHROPIC_API_KEY}`);
});

module.exports = app;