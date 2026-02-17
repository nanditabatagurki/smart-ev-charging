#!/bin/bash

# Smart EV Charging Setup Script
# This script helps you set up and test your smart charging system

set -e

echo "=================================================="
echo "  Smart EV Charging Controller - Setup Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check if Docker is installed
echo "Step 1: Checking prerequisites..."
echo ""

if command -v docker &> /dev/null; then
    print_success "Docker is installed"
    docker --version
else
    print_error "Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    print_success "Docker Compose is available"
else
    print_error "Docker Compose is not available"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo ""
echo "Step 2: Checking configuration..."
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    print_success ".env file exists"
    
    # Check if required variables are set
    source .env
    
    if [ -z "$VEHICLE_VIN" ] || [ "$VEHICLE_VIN" == "your-vin" ]; then
        print_warning "VEHICLE_VIN needs to be configured in .env"
    else
        print_success "VEHICLE_VIN is configured"
    fi
    
    if [ -z "$ONSTAR_DEVICEID" ]; then
        print_warning "ONSTAR_DEVICEID needs to be configured in .env"
    else
        print_success "ONSTAR_DEVICEID is configured"
    fi
    
    if [ -z "$ONSTAR_USERNAME" ]; then
        print_warning "ONSTAR_USERNAME needs to be configured in .env"
    else
        print_success "ONSTAR_USERNAME is configured"
    fi
    
else
    print_warning ".env file not found"
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    print_success "Created .env file from template"
    echo ""
    print_warning "Please edit .env file with your configuration before proceeding"
    echo ""
    echo "Required settings:"
    echo "  - VEHICLE_VIN"
    echo "  - ONSTAR_DEVICEID"
    echo "  - ONSTAR_USERNAME"
    echo "  - ONSTAR_PASSWORD"
    echo "  - ONSTAR_PIN"
    echo ""
    exit 1
fi

echo ""
echo "Step 3: Testing ComEd API..."
echo ""

if command -v python3 &> /dev/null; then
    pip3 install -q requests 2>/dev/null || true
    python3 test_comed_api.py
else
    print_warning "Python3 not found - skipping API test"
fi

echo ""
echo "Step 4: Building Docker containers..."
echo ""

docker-compose build

print_success "Containers built successfully"

echo ""
echo "Step 5: Starting services..."
echo ""

docker-compose up -d

print_success "Services started"

echo ""
echo "Waiting for services to initialize (10 seconds)..."
sleep 10

echo ""
echo "Step 6: Checking service status..."
echo ""

docker-compose ps

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Monitor the logs:"
echo "   docker-compose logs -f smart-charging"
echo ""
echo "2. Test MQTT connection:"
echo "   docker run -it --rm --network ev-network -v \$(pwd):/app python:3.9-slim bash -c 'cd /app && pip install paho-mqtt && python test_mqtt_connection.py'"
echo ""
echo "3. View all logs:"
echo "   docker-compose logs -f"
echo ""
echo "4. Stop services:"
echo "   docker-compose down"
echo ""
echo "For troubleshooting, see README.md"
echo ""
