#!/bin/sh
# Switches browser telemetry on or off when the container starts (#62).
#
# The browser sends its telemetry to /otel/v1/{traces,logs} on its own site,
# and nginx forwards it to the OpenTelemetry collector. Any credentials in
# OTEL_EXPORTER_OTLP_HEADERS are added here, so they never reach the browser.
#
# Browser telemetry is on only when BROWSER_TELEMETRY_ENABLED=true and
# OTEL_EXPORTER_OTLP_ENDPOINT points at an OTLP/HTTP endpoint. If anything is
# wrong it stays off and says why, rather than stopping nginx from starting.

set -eu

HTML_DIR=/usr/share/nginx/html
SNIPPET_DIR=/etc/nginx/byteorder
ZONE_FILE=/etc/nginx/conf.d/00-byteorder-otel-zone.conf

log() {
    echo "byteorder-browser-telemetry: $*" >&2
}

write_runtime_config() {
    printf 'window.__BYTEORDER__ = { "telemetry": %s }\n' "$1" > "$HTML_DIR/runtime-config.js"
}

off() {
    log "$* Browser telemetry is off."
    exit 0
}

# Start from "off", so a restart with different settings never keeps stale config.
mkdir -p "$SNIPPET_DIR"
rm -f "$SNIPPET_DIR/otel.conf" "$ZONE_FILE"
write_runtime_config '{ "enabled": false }'

[ "${BROWSER_TELEMETRY_ENABLED:-false}" = "true" ] || exit 0

endpoint=${OTEL_EXPORTER_OTLP_ENDPOINT:-}
[ -n "$endpoint" ] || off "BROWSER_TELEMETRY_ENABLED is true but OTEL_EXPORTER_OTLP_ENDPOINT is not set."

protocol=${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}
case "$protocol" in
    http/*) ;;
    *) off "Browsers can only send OTLP over HTTP, but OTEL_EXPORTER_OTLP_PROTOCOL is $protocol." ;;
esac

endpoint=${endpoint%/}
case "$endpoint" in
    http://* | https://*) ;;
    *) off "OTEL_EXPORTER_OTLP_ENDPOINT must start with http:// or https://." ;;
esac
case "$endpoint" in
    *[!A-Za-z0-9.:/_-]*) off "OTEL_EXPORTER_OTLP_ENDPOINT contains characters that aren't allowed in a URL here." ;;
esac

# nginx resolves the collector's name when it loads its config, and won't
# start if that fails, so check first.
host=${endpoint#*://}
host=${host%%/*}
host=${host%%:*}
getent hosts "$host" > /dev/null || off "Cannot resolve the collector host $host."

sample_rate=${BROWSER_TELEMETRY_SAMPLE_RATE:-100}
case "$sample_rate" in
    '' | *[!0-9]*) off "BROWSER_TELEMETRY_SAMPLE_RATE must be a whole number from 0 to 100." ;;
esac
[ "$sample_rate" -le 100 ] || off "BROWSER_TELEMETRY_SAMPLE_RATE must be a whole number from 0 to 100."

session_replay=${BROWSER_TELEMETRY_SESSION_REPLAY:-false}
case "$session_replay" in
    true | false) ;;
    *) off "BROWSER_TELEMETRY_SESSION_REPLAY must be true or false." ;;
esac

service_name=${OTEL_SERVICE_NAME:-byteorder-frontend}
case "$service_name" in
    '' | *[!A-Za-z0-9._-]*) off "OTEL_SERVICE_NAME may only contain letters, digits, '.', '_' and '-'." ;;
esac

# OTEL_EXPORTER_OTLP_HEADERS is "key=value,key=value" with URL-encoded values.
# Without an Authorization header, an empty one stops the browser's dummy token
# going any further.
header_lines=""
has_auth=false
if [ -n "${OTEL_EXPORTER_OTLP_HEADERS:-}" ]; then
    old_ifs=$IFS
    IFS=,
    for pair in $OTEL_EXPORTER_OTLP_HEADERS; do
        IFS=$old_ifs
        name=${pair%%=*}
        value=${pair#*=}
        name=$(printf '%s' "$name" | tr -d ' ')
        case "$name" in
            '' | *[!A-Za-z0-9-]*) off "OTEL_EXPORTER_OTLP_HEADERS has an invalid header name." ;;
        esac
        # Decode %XX escapes.
        value=$(printf '%b' "$(printf '%s' "$value" | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g')")
        case "$value" in
            *[\"\\\$\;]* | *[[:cntrl:]]*) off "OTEL_EXPORTER_OTLP_HEADERS has a value nginx can't pass on safely." ;;
        esac
        [ "$(printf '%s' "$name" | tr 'A-Z' 'a-z')" = "authorization" ] && has_auth=true
        header_lines="$header_lines        proxy_set_header $name \"$value\";
"
    done
    IFS=$old_ifs
fi
[ "$has_auth" = true ] || header_lines="$header_lines        proxy_set_header Authorization \"\";
"

# Shared by all browsers when nginx sits behind an ingress, since they all
# arrive from the ingress's address. That still caps what can reach the collector.
cat > "$ZONE_FILE" <<EOF
limit_req_zone \$binary_remote_addr zone=byteorder_otel:1m rate=20r/s;
EOF

{
    for signal in traces logs; do
        cat <<EOF
    location = /otel/v1/$signal {
        limit_except POST { deny all; }
        limit_req zone=byteorder_otel burst=40 nodelay;
        limit_req_status 429;
        client_max_body_size 1m;
        proxy_http_version 1.1;
        proxy_ssl_server_name on;
        proxy_set_header Host \$proxy_host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Cookie "";
$header_lines        proxy_pass $endpoint/v1/$signal;
    }
EOF
    done
} > "$SNIPPET_DIR/otel.conf"

write_runtime_config "{ \"enabled\": true, \"serviceName\": \"$service_name\", \"sampleRate\": $sample_rate, \"sessionReplay\": $session_replay }"
log "Forwarding browser telemetry to $endpoint."
