FROM ubuntu:22.04

# Install dependencies (including make for hummingbot-api setup)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Docker (official method with compose plugin)
RUN curl -fsSL https://get.docker.com | sh

# Create sudo shim (container runs as root, but setup.sh expects sudo)
RUN echo '#!/bin/bash\n\
# Skip env var assignments, execute the actual command\n\
while [[ "$1" == *=* ]]; do export "$1"; shift; done\n\
exec "$@"' > /usr/local/bin/sudo && chmod +x /usr/local/bin/sudo

# Set USER env var (required by hummingbot-api setup.sh)
ENV USER=root

# Install Node.js (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install AI Agent CLIs
RUN npm install -g @anthropic-ai/claude-code @google/gemini-cli @openai/codex

# Copy local hummingbot-skills (build from repo root with: docker build -f evals/Dockerfile .)
COPY . /opt/hummingbot-skills

# Install skills for all AI agent CLIs
RUN mkdir -p /root/.claude/skills /root/.gemini/skills /root/.codex/skills \
    && ln -s /opt/hummingbot-skills/skills/hummingbot-deploy /root/.claude/skills/hummingbot-deploy \
    && ln -s /opt/hummingbot-skills/skills/hummingbot-deploy /root/.gemini/skills/hummingbot-deploy \
    && ln -s /opt/hummingbot-skills/skills/hummingbot-deploy /root/.codex/skills/hummingbot-deploy

# Make scripts executable
RUN chmod +x /opt/hummingbot-skills/skills/hummingbot-deploy/scripts/*.sh

WORKDIR /root

CMD ["/bin/bash"]
