
FROM apache/airflow:2.11.0

USER root

# Install Git for dbt and create a separate ETL Python environment.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/retailflow-venv \
    && chown -R airflow:0 /opt/retailflow-venv

USER airflow

COPY --chown=airflow:0 requirements-etl.txt /tmp/requirements-etl.txt

# Install ETL and dbt dependencies without changing Airflow's environment.
RUN /opt/retailflow-venv/bin/python -m pip install \
    --no-cache-dir \
    -r /tmp/requirements-etl.txt

RUN /opt/retailflow-venv/bin/python -m pip check
