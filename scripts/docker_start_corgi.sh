#!/bin/bash

# Start Corgi Recommender Service with Docker
# This script requires Docker to be installed

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PORT=5004
TAG="latest"
REBUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --port|-p)
      PORT="$2"
      shift
      shift
      ;;
    --tag|-t)
      TAG="$2"
      shift
      shift
      ;;
    --rebuild)
      REBUILD=true
      shift
      ;;
    --help)
      echo "Usage: ./docker_start_corgi.sh [options]"
      echo "Options:"
      echo "  --port, -p PORT      Specify port to expose (default: 5004)"
      echo "  --tag, -t TAG        Specify image tag (default: latest)"
      echo "  --rebuild            Force rebuild of the Docker image"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $key"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo -e "${RED}Error: Docker is not installed or not in PATH.${NC}"
  echo -e "${YELLOW}Please install Docker first.${NC}"
  exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
  echo -e "${RED}Error: Docker daemon is not running.${NC}"
  echo -e "${YELLOW}Please start Docker and try again.${NC}"
  exit 1
fi

# Display banner
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}Starting Corgi Recommender Service with Docker${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo

# Check if image exists
IMAGE_NAME="corgi-recommender-service:$TAG"
IMAGE_EXISTS=$(docker images -q $IMAGE_NAME 2> /dev/null)

if [ -z "$IMAGE_EXISTS" ] || [ "$REBUILD" = true ]; then
  # Build image if it doesn't exist or rebuild is requested
  if [ "$REBUILD" = true ]; then
    echo -e "${BLUE}Rebuilding Docker image...${NC}"
  else
    echo -e "${BLUE}Docker image not found. Building...${NC}"
  fi
  
  # Check if Dockerfile exists
  if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found in the current directory.${NC}"
    exit 1
  fi
  
  # Build the image
  docker build -t $IMAGE_NAME .
  
  if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build Docker image.${NC}"
    exit 1
  fi
  
  echo -e "${GREEN}Docker image built successfully.${NC}"
else
  echo -e "${GREEN}✓ Docker image found: $IMAGE_NAME${NC}"
fi

# Check if a container with the same name is already running
CONTAINER_NAME="corgi-server"
CONTAINER_RUNNING=$(docker ps -f "name=$CONTAINER_NAME" --format "{{.Names}}")

if [ -n "$CONTAINER_RUNNING" ]; then
  echo -e "${YELLOW}A container named '$CONTAINER_NAME' is already running.${NC}"
  echo -e "${YELLOW}Do you want to stop it and start a new one? [y/N]${NC}"
  read -r response
  
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}Stopping container...${NC}"
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
  else
    echo -e "${BLUE}Exiting.${NC}"
    exit 0
  fi
fi

# Start the container
echo -e "${BLUE}Starting Corgi container on port $PORT...${NC}"

docker run -d \
  --name $CONTAINER_NAME \
  -p $PORT:5004 \
  -e PORT=5004 \
  -e HOST=0.0.0.0 \
  --restart unless-stopped \
  $IMAGE_NAME

if [ $? -ne 0 ]; then
  echo -e "${RED}Error: Failed to start Docker container.${NC}"
  exit 1
fi

# Check if container started successfully
sleep 2
CONTAINER_RUNNING=$(docker ps -f "name=$CONTAINER_NAME" --format "{{.Names}}")

if [ -n "$CONTAINER_RUNNING" ]; then
  echo -e "${GREEN}✓ Corgi container started successfully.${NC}"
  echo
  echo -e "${BLUE}Container ID: $(docker ps -f "name=$CONTAINER_NAME" --format "{{.ID}}")${NC}"
  echo -e "${BLUE}Container name: $CONTAINER_NAME${NC}"
  echo -e "${BLUE}Port mapping: $PORT -> 5004${NC}"
  echo
  echo -e "${GREEN}===========================================================${NC}"
  echo -e "${GREEN}Corgi API available at: http://localhost:$PORT${NC}"
  echo -e "${GREEN}===========================================================${NC}"
  echo
  echo -e "${BLUE}To view logs:${NC}"
  echo -e "  docker logs $CONTAINER_NAME"
  echo
  echo -e "${BLUE}To stop the container:${NC}"
  echo -e "  docker stop $CONTAINER_NAME"
  echo
  echo -e "${BLUE}To restart the container:${NC}"
  echo -e "  docker restart $CONTAINER_NAME"
else
  echo -e "${RED}Error: Container started but is no longer running.${NC}"
  echo -e "${YELLOW}Check the logs for more information:${NC}"
  echo -e "  docker logs $CONTAINER_NAME"
  exit 1
fi