# -----------------------------------------------------------------------------
# Stage 1: Build - Create an optimized Keycloak build
# -----------------------------------------------------------------------------
FROM quay.io/keycloak/keycloak:26.0 as builder

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

# Configure database vendor to PostgreSQL
ENV KC_DB=postgres

# Run the build command to optimize the image for these settings
RUN /opt/keycloak/bin/kc.sh build

# -----------------------------------------------------------------------------
# Stage 2: Runtime - The actual image that will run
# -----------------------------------------------------------------------------
FROM quay.io/keycloak/keycloak:26.0

# Copy the optimized build from the previous stage
COPY --from=builder /opt/keycloak/ /opt/keycloak/

# Expose the default Keycloak port
EXPOSE 8080

# ENTRYPOINT Configuration:
# start-optimized         : Uses the build options from Stage 1
# --http-enabled=true     : Required because we are behind an ALB (TLS termination happens at ALB)
# --hostname-strict=false : Disables strict hostname checking (simplifies Dev setup)
# --proxy-headers=xforwarded : Trusts headers from the ALB (X-Forwarded-For, etc.)
ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start-optimized", "--http-enabled=true", "--hostname-strict=false", "--proxy-headers=xforwarded"]
