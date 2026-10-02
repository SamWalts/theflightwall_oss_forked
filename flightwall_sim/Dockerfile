FROM python:3.12-slim

WORKDIR /app

COPY flightwall_sim/simulator.py flightwall_sim/sample_aircraft.json ./

ENV FLIGHTWALL_SIM_HOST=0.0.0.0 \
    FLIGHTWALL_SIM_PORT=8090 \
    PI_ENRICHMENT_BASE_URL=http://pi-enrichment:8080 \
    SIM_INPUT_PATH=/app/sample_aircraft.json \
    SIM_POLL_SECONDS=5

EXPOSE 8090

CMD ["python", "/app/simulator.py"]
