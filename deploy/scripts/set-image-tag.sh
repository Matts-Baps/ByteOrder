#!/bin/sh
# Pins one ByteOrder service to an image tag in a Helm values file (#70).
#
#   set-image-tag.sh <values-file> <service> <tag>
#
# Sets images.<service>.tag and leaves the rest of the file, including
# comments, as it was. CI uses it to deploy a newly built image through
# ArgoCD. Needs mikefarah yq v4.

set -eu

if [ "$#" -ne 3 ]; then
    echo "usage: $0 <values-file> <service> <tag>" >&2
    exit 2
fi

file=$1
service=$2
tag=$3

[ -f "$file" ] || { echo "no such file: $file" >&2; exit 1; }

case "$service" in
    '' | -* | *[!a-z0-9-]*) echo "invalid service name: $service" >&2; exit 1 ;;
esac

# Image tags allow letters, digits, '_', '.', '-' (max 128, not starting with
# '.' or '-'). sha- tags must be hex, as docker/metadata-action makes them.
case "$tag" in
    '' | .* | -* | *[!A-Za-z0-9_.-]*) echo "invalid image tag: $tag" >&2; exit 1 ;;
    sha-*)
        case "${tag#sha-}" in
            '' | *[!0-9a-f]*) echo "invalid sha tag: $tag" >&2; exit 1 ;;
        esac
        ;;
esac
[ "${#tag}" -le 128 ] || { echo "image tag too long: $tag" >&2; exit 1; }

current=$(SERVICE="$service" yq '.images[strenv(SERVICE)].tag // ""' "$file")
if [ "$current" = "$tag" ]; then
    echo "$service already at $tag, unchanged"
    exit 0
fi

SERVICE="$service" TAG="$tag" yq -i '.images[strenv(SERVICE)].tag = strenv(TAG)' "$file"
echo "$service: ${current:-unset} -> $tag"
