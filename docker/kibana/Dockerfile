FROM kibana:8.12.0

# Copy configuration
COPY config/kibana.yml /usr/share/kibana/config/

# Set permissions
USER root
RUN chown -R kibana:kibana /usr/share/kibana/config/kibana.yml
USER kibana