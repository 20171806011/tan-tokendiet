FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="io.github.20171806011/tan-tokendiet"
LABEL org.opencontainers.image.source="https://github.com/20171806011/tan-tokendiet"
LABEL org.opencontainers.image.url="https://20171806011.github.io/tan-tokendiet/"
LABEL org.opencontainers.image.description="Audit and compact MCP tool schemas & AI agent context files to cut LLM token burn."
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY tokendiet ./tokendiet

RUN pip install --no-cache-dir --no-deps .

ENTRYPOINT ["tokendiet-mcp"]
