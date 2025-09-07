FROM elasticsearch:8.12.0

# Install required plugins
RUN elasticsearch-plugin install --batch analysis-icu
RUN elasticsearch-plugin install --batch analysis-phonetic

# Copy configuration
COPY config/elasticsearch.yml /usr/share/elasticsearch/config/

# Set permissions
USER root
RUN chown -R elasticsearch:elasticsearch /usr/share/elasticsearch/config/elasticsearch.yml
USER elasticsearch