pip freeze > requirements.txt
docker build -t automower -f Dockerfile .
docker tag automower:latest docker.diskstation/automower
docker push docker.diskstation/automower:latest