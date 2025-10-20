#!/bin/bash

# Test script for Tempest overlay endpoints
# This script tests all three endpoints to ensure they're working correctly

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Tempest Overlay Endpoint Test"
echo "========================================="
echo ""

# Check if container is running
if ! curl -s http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to http://localhost:8080${NC}"
    echo "Make sure the Docker container is running:"
    echo "  docker run -p 8080:8080 -e TEMPEST_API_KEY=your_key -e TEMPEST_STATION_ID=your_id tempest-overlay"
    exit 1
fi

echo -e "${GREEN}✓ Server is running${NC}"
echo ""

# Test 1: Index page
echo "Test 1: Index page"
echo "==================="
RESPONSE=$(curl -s http://localhost:8080/)
if [[ $RESPONSE == *"Available endpoints"* ]]; then
    echo -e "${GREEN}✓ Index page responds correctly${NC}"
else
    echo -e "${RED}✗ Index page did not respond as expected${NC}"
fi
echo ""

# Test 2: Daily forecast overlay
echo "Test 2: Daily forecast overlay"
echo "================================"
HTTP_CODE=$(curl -s -o /tmp/daily_test.png -w "%{http_code}" "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial")
if [ "$HTTP_CODE" = "200" ]; then
    FILE_SIZE=$(wc -c < /tmp/daily_test.png)
    if [ "$FILE_SIZE" -gt 1000 ]; then
        echo -e "${GREEN}✓ Daily forecast endpoint returned PNG (${FILE_SIZE} bytes)${NC}"
        echo "  Saved to: /tmp/daily_test.png"
    else
        echo -e "${YELLOW}⚠ Daily forecast endpoint returned small file (${FILE_SIZE} bytes)${NC}"
        echo "  This might indicate an error image"
    fi
else
    echo -e "${RED}✗ Daily forecast endpoint failed (HTTP ${HTTP_CODE})${NC}"
fi
echo ""

# Test 3: 5-day forecast overlay
echo "Test 3: 5-Day forecast overlay"
echo "================================"
HTTP_CODE=$(curl -s -o /tmp/5day_test.png -w "%{http_code}" "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial")
if [ "$HTTP_CODE" = "200" ]; then
    FILE_SIZE=$(wc -c < /tmp/5day_test.png)
    if [ "$FILE_SIZE" -gt 1000 ]; then
        echo -e "${GREEN}✓ 5-day forecast endpoint returned PNG (${FILE_SIZE} bytes)${NC}"
        echo "  Saved to: /tmp/5day_test.png"
    else
        echo -e "${YELLOW}⚠ 5-day forecast endpoint returned small file (${FILE_SIZE} bytes)${NC}"
        echo "  This might indicate an error image"
    fi
else
    echo -e "${RED}✗ 5-day forecast endpoint failed (HTTP ${HTTP_CODE})${NC}"
fi
echo ""

# Test 4: Current conditions overlay (may not work without local Tempest station)
echo "Test 4: Current conditions overlay (original)"
echo "==============================================="
HTTP_CODE=$(curl -s -o /tmp/current_test.png -w "%{http_code}" "http://localhost:8080/overlay.png?width=800&height=200&theme=dark&units=imperial")
if [ "$HTTP_CODE" = "200" ]; then
    FILE_SIZE=$(wc -c < /tmp/current_test.png)
    if [ "$FILE_SIZE" -gt 1000 ]; then
        echo -e "${GREEN}✓ Current conditions endpoint returned PNG (${FILE_SIZE} bytes)${NC}"
        echo "  Saved to: /tmp/current_test.png"
    else
        echo -e "${YELLOW}⚠ Current conditions endpoint returned small file (${FILE_SIZE} bytes)${NC}"
        echo "  This is expected if no local Tempest station is broadcasting"
    fi
else
    echo -e "${RED}✗ Current conditions endpoint failed (HTTP ${HTTP_CODE})${NC}"
fi
echo ""

# Test 5: Theme variations
echo "Test 5: Theme variations (light theme)"
echo "========================================"
HTTP_CODE=$(curl -s -o /tmp/daily_light.png -w "%{http_code}" "http://localhost:8080/overlay/daily?width=800&height=200&theme=light&units=imperial")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Light theme works${NC}"
    echo "  Saved to: /tmp/daily_light.png"
else
    echo -e "${RED}✗ Light theme failed${NC}"
fi
echo ""

# Test 6: Unit variations
echo "Test 6: Unit variations (metric)"
echo "=================================="
HTTP_CODE=$(curl -s -o /tmp/daily_metric.png -w "%{http_code}" "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=metric")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Metric units work${NC}"
    echo "  Saved to: /tmp/daily_metric.png"
else
    echo -e "${RED}✗ Metric units failed${NC}"
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Generated test images are in /tmp:"
echo "  - /tmp/daily_test.png (dark, imperial)"
echo "  - /tmp/daily_light.png (light, imperial)"
echo "  - /tmp/daily_metric.png (dark, metric)"
echo "  - /tmp/5day_test.png (dark, imperial)"
echo "  - /tmp/current_test.png (original endpoint)"
echo ""
echo "To view images on Mac:"
echo "  open /tmp/daily_test.png"
echo "  open /tmp/5day_test.png"
echo ""
echo -e "${GREEN}Testing complete!${NC}"

