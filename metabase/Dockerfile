# Debian/glibc base: the DuckDB Metabase community driver ships a native library
# built against glibc rather than Alpine/musl.
FROM eclipse-temurin:21-jre-jammy

RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG METABASE_VERSION=0.63.0
ARG DUCKDB_DRIVER_VERSION=1.5.5.0

RUN curl -fSL -o metabase.jar https://downloads.metabase.com/v${METABASE_VERSION}/metabase.jar

RUN mkdir -p /plugins \
 && curl -fSL -o /plugins/duckdb.metabase-driver.jar \
      https://github.com/motherduckdb/metabase_duckdb_driver/releases/download/${DUCKDB_DRIVER_VERSION}/duckdb.metabase-driver.jar

ENV MB_PLUGINS_DIR=/plugins

EXPOSE 3000
CMD ["java", "-jar", "metabase.jar"]
