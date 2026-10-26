FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.14-slim-trixie AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/bin/node /usr/local/bin/node
COPY ml_model/requirements.txt ./ml_model/requirements.txt
RUN pip install --no-cache-dir -r ml_model/requirements.txt && pip check && python -m pip uninstall --yes pip
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
COPY ml_model/*.py ./ml_model/
COPY ml_model/models/model_bundle.pkl ./ml_model/models/model_bundle.pkl
COPY ml_model/models/hybrid_bundle.pkl ./ml_model/models/hybrid_bundle.pkl
COPY ml_model/models/hybrid_manifest.json ./ml_model/models/hybrid_manifest.json
RUN chown -R 10001:10001 /app/.next
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=8080 PYTHON_EXECUTABLE=python PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "server.js"]
