FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-setuptools \
    python-is-python3 \
    build-essential \
    cmake \
    g++ \
    flex \
    bison \
    && apt-get clean

COPY road_complexity_analysis.py /tools/
RUN pip install --no-cache-dir pandas matplotlib
    

# Set working directory
WORKDIR /opt

# Clone specific release tag of Fast Downward
RUN git clone --branch release-24.06.1 https://github.com/aibasel/downward.git

# Build Fast Downward
WORKDIR /opt/downward
RUN ./build.py
