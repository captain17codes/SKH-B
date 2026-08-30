# Kopargaon CRPP backend (FastAPI + stdlib sqlite3).
#
# Build context is the REPOSITORY ROOT, not backend/. This is load-bearing:
# config.py resolves REFERENCE_DIR to the parent of the backend directory and
# reads the kopargaon_*.json datasets from there, and main.py puts that same
# parent on sys.path so `import track1_engine` works. Flattening the layout
# breaks both.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first so edits to application code do not invalidate the layer.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Reference datasets, read at runtime by domain/reference.py.
COPY kopargaon_civic_service_sla_escalation_matrix_v1.json \
     kopargaon_department_workforce_skill_matrix_v1.json \
     kopargaon_water_waste_operational_rules_cost_matrix_v1.json \
     kopargaon_civic_resource_capability_evidence_v1.json \
     kopargaon_civic_contacts_and_escalation_v1.json \
     kopargaon_municipal_projects_management_pipeline_v2.json \
     citizen_en.json \
     citizen_mr.json \
     ./

COPY track1_engine/ track1_engine/
COPY backend/ backend/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Both of these must point at the mounted volume, otherwise the SQLite file and
# every uploaded photo live in the container's ephemeral layer and vanish on the
# next deploy or restart. fly.toml sets them too; duplicated here so `docker run`
# behaves the same way.
ENV CRPP_DB_PATH=/data/crpp.db \
    UPLOAD_DIR=/data/uploads \
    PORT=8080

EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
