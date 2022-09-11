FROM python:3.8

# RUN sudo echo 'nameserver 8.8.8.8'>/etc/resolv.conf
RUN apt-get update --allow-insecure-repositories -y && apt-get install apt-file -y && apt-file update && apt-get install -y python3-dev build-essential

# Install RabbitMQ
RUN apt-get install -y erlang
RUN apt-get install -y rabbitmq-server

# Copy Swirl App to container
RUN mkdir /app
ADD ./swirl /app/swirl
ADD ./swirl_server /app/swirl_server
ADD ./requirements.txt /app/requirements.txt
ADD ./SearchProviders /app/SearchProviders
ADD ./scripts /app/scripts
ADD ./Data /app/Data
ADD ./swirl.py /app/swirl.py
ADD ./manage.py /app/manage.py

WORKDIR /app

# install requirements
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_md

EXPOSE 8000