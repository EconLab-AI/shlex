FROM python:3.12-bookworm

# Create dev user
RUN groupadd -g 1000 dev 2>/dev/null || true && \
    usermod -aG dev node 2>/dev/null || true

# Minimal deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# SSH config
RUN echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config && \
    mkdir /var/run/sshd

# Obsidian CLI
RUN npm install -g obsidian-cli || true

WORKDIR /workspace