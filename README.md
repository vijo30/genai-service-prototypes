# genai-service-prototypes


## Building and Rebuilding
- Build all services:
  ```bash
  docker-compose build
  ```
- Rebuild a specific service:
  ```bash
  docker-compose build <service_name>
  ```
- Force rebuild without cache:
  ```bash
  docker-compose build --no-cache
  ```

## Starting and Stopping Services
- Start all services:
  ```bash
  docker-compose up
  ```
- Start in detached mode:
  ```bash
  docker-compose up -d
  ```
- Stop all services:
  ```bash
  docker-compose down
  ```
- Restart a specific service:
  ```bash
  docker-compose restart <service_name>
  ```

## Viewing Logs
- Logs for all services:
  ```bash
  docker-compose logs
  ```
- Logs for a specific service:
  ```bash
  docker-compose logs <service_name>
  ```
- Stream live logs:
  ```bash
  docker-compose logs -f
  ```

## Debugging and Inspecting
- List running containers:
  ```bash
  docker ps
  ```
- Inspect a container:
  ```bash
  docker inspect <container_id_or_name>
  ```
- Access a container’s shell:
  ```bash
  docker exec -it <container_id_or_name> /bin/bash
  ```
- Check container logs:
  ```bash
  docker logs <container_id_or_name>
  ```
- List all containers (running and stopped):
  ```bash
  docker ps -a
  ```

## Managing Images
- List all Docker images:
  ```bash
  docker images
  ```
- Remove an unused image:
  ```bash
  docker rmi <image_id>
  ```
- Prune unused images and resources:
  ```bash
  docker system prune
  ```

## Volumes and Networks
- List volumes:
  ```bash
  docker volume ls
  ```
- Remove a specific volume:
  ```bash
  docker volume rm <volume_name>
  ```
- List networks:
  ```bash
  docker network ls
  ```
- Inspect a network:
  ```bash
  docker network inspect <network_name>
  ```
- Remove a network:
  ```bash
  docker network rm <network_name>
  ```

## Stopping and Removing Containers
- Stop a specific container:
  ```bash
  docker stop <container_id_or_name>
  ```
- Remove a stopped container:
  ```bash
  docker rm <container_id_or_name>
  ```
- Stop all running containers:
  ```bash
  docker stop $(docker ps -q)
  ```
- Remove all stopped containers:
  ```bash
  docker rm $(docker ps -aq)
  ```

## Miscellaneous
- Check real-time resource usage:
  ```bash
  docker stats
  ```
- Kill a running container:
  ```bash
  docker kill <container_id_or_name>
  ```
- Tag an image:
  ```bash
  docker tag <image_id> <repository_name>:<tag>
  ```
- Push an image to a repository:
  ```bash
  docker push <repository_name>:<tag>
  ```
- Pull an image from a repository:
  ```bash
  docker pull <repository_name>:<tag>
  ```

## Common Combos
- Rebuild and restart everything:
  ```bash
  docker-compose down && docker-compose build --no-cache && docker-compose up -d
  ```
- Remove all containers, images, and volumes:
  ```bash
  docker system prune -a --volumes
  ```


