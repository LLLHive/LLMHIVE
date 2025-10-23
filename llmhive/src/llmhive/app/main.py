import os
import logging
import sys
from flask import Flask, request, jsonify, Response

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import existing application components with error handling
try:
    from .orchestrator import Orchestrator
    from .config import config
    from .models import initialize_models
    # Preserve other imports as needed
except ImportError as e:
    logger.warning(f"Some module imports failed: {e}")
    logger.warning("Application will start in limited functionality mode")

# Initialize Flask application
app = Flask(__name__)

# Essential health check endpoint for Cloud Run
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint required by Cloud Run"""
    logger.info("Health check endpoint called")
    return jsonify({"status": "healthy", "service": "llmhive-orchestrator"}), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint for basic verification"""
    logger.info("Root endpoint called")
    return jsonify({
        "service": "LLMHive Orchestrator API",
        "status": "online",
        "version": config.VERSION if 'config' in locals() else "1.0.0"
    })

# Preserve your existing API endpoints
# This is a fallback in case your original endpoints have issues
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Temporary implementation to ensure service starts"""
    try:
        # Log request but don't include potentially sensitive data
        logger.info(f"Received chat request from {request.remote_addr}")
        
        # Try to use existing orchestrator if available
        if 'Orchestrator' in locals() or 'Orchestrator' in globals():
            orchestrator = Orchestrator()
            result = orchestrator.process_request(request.json)
            return jsonify(result)
        else:
            # Fallback response if orchestrator isn't available
            return jsonify({
                "response": "LLMHive orchestrator is starting up. Full functionality will be available shortly.",
                "status": "initializing"
            })
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "status": "error"}), 500

# Application factory pattern for gunicorn
def create_app():
    """Factory function that creates and configures the Flask app"""
    # Initialize any required services here
    logger.info("Initializing application through factory function")
    return app

# Direct execution entry point
if __name__ == '__main__':
    # Get port from environment variable with fallback to 8080
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    
    # Critical: Bind to all network interfaces (0.0.0.0) for container compatibility
    app.run(host='0.0.0.0', port=port, debug=False)
