#!/bin/bash
# Start Jupyter Lab in the background
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --token="" --password="" &
# Start Streamlit app in the background
cd /app/streamlit_app_dev
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &
# Keep container running
wait