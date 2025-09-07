FROM logstash:8.12.0

# Install required plugins
RUN logstash-plugin install logstash-input-http
RUN logstash-plugin install logstash-input-beats
RUN logstash-plugin install logstash-filter-json
RUN logstash-plugin install logstash-filter-mutate
RUN logstash-plugin install logstash-output-elasticsearch

# Copy configuration
COPY config/logstash.yml /usr/share/logstash/config/
COPY pipeline/ /usr/share/logstash/pipeline/

# Set permissions
USER root
RUN chown -R logstash:logstash /usr/share/logstash/config/logstash.yml /usr/share/logstash/pipeline/
USER logstash