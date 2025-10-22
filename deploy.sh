#!/bin/bash
# Tempest Weather Overlay Deployment Script
# Run this on your Raspberry Pi to deploy updates

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  🚀 Deploying Tempest Weather Overlay Updates                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="tempest-overlay"
IMAGE_NAME="tempest-overlay"
DEFAULT_PORT=8036

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ Error: .env file not found!${NC}"
    echo "Please create .env with TEMPEST_API_KEY and TEMPEST_STATION_ID"
    exit 1
fi

echo -e "${YELLOW}Step 1: Pulling latest changes from GitHub...${NC}"
git pull origin main
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Git pull successful${NC}"
else
    echo -e "${RED}✗ Git pull failed${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 2: Stopping existing container...${NC}"
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✓ Stopped and removed old container${NC}"
else
    echo -e "${GREEN}✓ No existing container to stop${NC}"
fi
echo ""

echo -e "${YELLOW}Step 3: Building new Docker image...${NC}"
docker build -t "$IMAGE_NAME" .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker build successful${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 4: Starting new container...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --network host \
    --env-file .env \
    "$IMAGE_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Container started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start container${NC}"
    exit 1
fi
echo ""

# Wait a moment for container to start
sleep 2

echo -e "${YELLOW}Step 5: Checking container status...${NC}"
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "Showing logs:"
    docker logs "$CONTAINER_NAME"
    exit 1
fi
echo ""

# Get the port from .env or use default
PORT=$(grep FLASK_PORT .env 2>/dev/null | cut -d= -f2 || echo "$DEFAULT_PORT")

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYMENT COMPLETE!                                         ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 Tempest Weather Overlay is now running!"
echo ""
echo "📍 Available endpoints:"
echo "   http://localhost:${PORT}/overlay.png      - Original (headers + tide)"
echo "   http://localhost:${PORT}/overlay/current  - Current conditions"
echo "   http://localhost:${PORT}/overlay/daily    - Daily forecast"
echo "   http://localhost:${PORT}/overlay/5day     - 5-day forecast"
echo "   http://localhost:${PORT}/overlay/5hour    - 5-hour forecast"
echo ""
echo "📋 Useful commands:"
echo "   docker logs $CONTAINER_NAME           - View logs"
echo "   docker logs -f $CONTAINER_NAME        - Follow logs"
echo "   docker restart $CONTAINER_NAME        - Restart container"
echo "   docker stop $CONTAINER_NAME           - Stop container"
echo ""
echo "🔄 To deploy future updates, just run: ./deploy.sh"
echo ""

# Show recent logs
echo -e "${YELLOW}Recent logs:${NC}"
docker logs --tail 10 "$CONTAINER_NAME"

