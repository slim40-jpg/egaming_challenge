# agent_software/Dockerfile.simple

FROM alpine:latest

WORKDIR /app

# Copy pre-built Windows executable
COPY gaming_agent.exe /app/gaming_agent.exe

# Make it executable
RUN chmod +x /app/gaming_agent.exe

# Run the agent
CMD ["/app/gaming_agent.exe"]s