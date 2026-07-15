# Multi-stage build: compile/install into a builder stage (needs a C++
# toolchain in case no prebuilt llama-cpp-python wheel matches this
# platform/Python combination -- see requirements.txt), then copy only the
# installed packages into a slim final image with no compiler in it.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

# Local-disk storage fallback (no Firebase project required to run this
# image) and the Hugging Face model cache both live under paths meant to be
# volume-mounted -- see docker-compose.yml.
ENV USE_FIREBASE=false

EXPOSE 8000

# Deliberately no --workers here: each worker would be a separate OS process
# loading its own full copy of the local LLM (~3.8GB) and embedding model
# (~1.3GB) into memory. A single worker keeps one copy of each resident,
# serialized through local_llm_client.py's lock -- see the README's
# Performance section on why concurrent inference is serialized, not
# parallelized, for a single local model instance.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
