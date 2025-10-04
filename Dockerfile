# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for ontology work
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for ontology development
RUN pip install --no-cache-dir \
    jupyterlab \
    streamlit \
    owlready2 \
    rdflib \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    networkx

# Expose ports for Jupyter Lab and Streamlit
EXPOSE 8888 8501

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set Jupyter password
RUN mkdir -p /root/.jupyter && \
    python -c "from jupyter_server.auth import passwd; print(passwd('gao123'))" > /tmp/hash.txt && \
    echo "c.ServerApp.password = '$(cat /tmp/hash.txt)'" >> /root/.jupyter/jupyter_server_config.py

# Set default command
CMD ["/app/start.sh"]