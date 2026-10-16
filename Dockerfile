# For MCP directories' automated checks (Glama and the like): builds the server and runs it over stdio.
# On Linux the file tools work (project_read, project_write, config, profile); the live link to FL and
# fl_install need Windows with FL Studio, so they answer with an error there. To use it, install on
# Windows: INSTALL.md.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
WORKDIR /app
COPY . .
RUN uv sync --locked --no-dev --python /usr/local/bin/python3
ENV PATH="/app/.venv/bin:$PATH"
CMD ["kuruitsugizaki"]
