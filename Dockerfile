FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.14-slim-bookworm AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/bin/node /usr/local/bin/node
COPY ml_model/requirements.txt ./ml_model/requirements.txt
RUN pip install --no-cache-dir -r ml_model/requirements.txt
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
COPY ml_model/*.py ./ml_model/
COPY ml_model/models/model_bundle.pkl ./ml_model/models/model_bundle.pkl
COPY ml_model/models/hybrid_bundle.pkl ./ml_model/models/hybrid_bundle.pkl
COPY ml_model/models/hybrid_manifest.json ./ml_model/models/hybrid_manifest.json
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=8080 PYTHON_EXECUTABLE=python PYTHONUTF8=1 OMP_NUM_THREADS=1
EXPOSE 8080
CMD ["node", "server.js"]
