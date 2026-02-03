FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker (official method with compose plugin)
RUN curl -fsSL https://get.docker.com | sh

# Install Node.js (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Clone hummingbot-skills and install the skill
RUN git clone --depth 1 https://github.com/hummingbot/skills.git /opt/hummingbot-skills

# Install the skill globally for Claude
RUN mkdir -p /root/.claude/skills \
    && ln -s /opt/hummingbot-skills/skills/hummingbot-deploy /root/.claude/skills/hummingbot-deploy

# Make scripts executable
RUN chmod +x /opt/hummingbot-skills/skills/hummingbot-deploy/scripts/*.sh

WORKDIR /root

CMD ["/bin/bash"]
