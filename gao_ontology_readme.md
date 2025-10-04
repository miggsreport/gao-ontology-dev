# GAO Ontology Project

## Overview
Ontology development environment using Docker, JupyterLab, and Streamlit for interactive ontology work, taxonomy mapping, and visualization.

## Project Structure

```
gao-ontology/
├── notebooks/                        # Jupyter notebooks for ontology development
│   └── gao_ontology_work.ipynb      # Main ontology work notebook
├── ontology_taxonomy_mapping/       # Taxonomy mapping scripts and data
│   ├── ontology_mapper.py           # Main mapping script
│   ├── data/                        # Input data files
│   └── results/                     # Mapping output results
├── streamlit_app_dev/               # Streamlit app development
│   ├── app.py                       # Main Streamlit application
│   └── [ontology files]             # TTL, RDF, JSON-LD files
├── ontologies/                      # Working ontology files
├── ontologies_master-files/         # Master/reference ontology files
├── docker-compose.yml               # Docker services configuration
├── Dockerfile                       # Container image definition
├── start.sh                         # Container startup script
└── README.txt                       # This file
```

## Quick Start

### Start Development Environment
```bash
cd C:\projects\gao-ontology
docker-compose up -d
```

Access points:
- **JupyterLab:** http://localhost:8888 (password: `gao123`)
- **Streamlit:** http://localhost:8501

### Stop Development Environment
```bash
docker-compose down
```

## Volume Mounting (File Sync)

All directories sync automatically between local machine and Docker container:
- Changes in JupyterLab appear instantly on local machine
- Changes made locally appear instantly in JupyterLab
- All work persists on local machine (not lost when container stops)

Synced directories:
- `notebooks/` ↔ `/app/notebooks`
- `ontology_taxonomy_mapping/` ↔ `/app/ontology_taxonomy_mapping`
- `streamlit_app_dev/` ↔ `/app/streamlit_app_dev`
- `ontologies/` ↔ `/app/ontologies`
- `ontologies_master-files/` ↔ `/app/ontologies_master-files`

## Git Workflow

Git repository https://github.com/miggsreport/gao-ontology-dev

Standard workflow for version control:

```bash
git status                          # Check what changed
git add .                           # Stage all changes
git commit -m "Description"         # Commit with message
git push                            # Push to remote
```

## Rebuilding Container

After modifying Dockerfile or for fresh container:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Note: Password `gao123` is baked into the image and persists across rebuilds.

## Deployment Workflow

Production Streamlit app is managed separately at:
`C:\projects\gao-ontology_streamlit public app\`

Deployment process:
1. Develop and test in `streamlit_app_dev/` (http://localhost:8501)
2. When ready, copy finalized changes to public app directory
3. Deploy to Streamlit Cloud from public app directory

Keep development and production separate to avoid accidental deployments.

## Useful Commands

### View logs
```bash
docker logs ontology_development           # All logs
docker logs -f ontology_development        # Follow logs in real-time
```

### Access container shell
```bash
docker exec -it ontology_development bash
```

### Container status
```bash
docker ps                                  # Running containers
docker ps -a                               # All containers
```

### Verify volume mounts
```bash
docker inspect ontology_development --format='{{json .Mounts}}' | ConvertFrom-Json | Format-List
```

### Copy files from container (if needed)
```bash
docker cp ontology_development:/app/path/file ./local/path/
```

## Troubleshooting

### Password not working
Password is set in Dockerfile and persists across container restarts. If it stops working after a rebuild, the Dockerfile may need the password configuration re-added.

### Files not syncing
Verify mounts are active with the command above. If a directory doesn't appear in JupyterLab, check that it's listed in `docker-compose.yml` volumes section.

### Container won't start
Check logs for errors:
```bash
docker logs ontology_development
```

Common issues:
- Port 8888 or 8501 already in use
- Syntax error in docker-compose.yml (check indentation)
- Missing or corrupted start.sh file

### JupyterLab shows 403 Forbidden
Your session expired. Clear browser cookies for localhost or use an incognito window.

## Technical Notes

- Docker runs in detached mode (`-d` flag) - container runs in background
- Password hash generated during image build, stored in `/root/.jupyter/jupyter_server_config.py`
- Volume mounting configured in `docker-compose.yml`, not Dockerfile
- Dockerfile only creates base environment; directories created by volume mounts
- Git tracks local files only (container files are ephemeral except when volume-mounted)

## Project Components

**JupyterLab:** Interactive notebook environment for ontology development work

**Streamlit:** Web interface for ontology visualization and interaction

**Ontology Tools:**
- owlready2: OWL ontology manipulation
- rdflib: RDF graph processing
- Standard data science stack: pandas, numpy, matplotlib, seaborn, plotly, networkx