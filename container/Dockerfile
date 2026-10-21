FROM ollama/ollama:0.40.6
LABEL org.opencontainers.image.title="Fungen Operator" \
      org.opencontainers.image.description="Ollama 0.40.6, Fungen Operator, Codex 0.155.1; external model storage"
# An allowlisted context, made by build.py, prevents private workspace material
# from entering even the build context. The same install path serves both builds.
COPY . /opt/fungen-operator/
RUN bash /opt/fungen-operator/container/install.sh
ENV PATH="/opt/python/bin:/opt/agent/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    OLLAMA_HOST="127.0.0.1:11434" OLLAMA_CONTEXT_LENGTH="32768" \
    OLLAMA_NUM_PARALLEL="1" OLLAMA_MAX_LOADED_MODELS="1" \
    OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0"
WORKDIR /workspace
ENTRYPOINT ["/opt/python/bin/python3", "/opt/fungen-operator/container/fungen.py"]
CMD ["setup"]
