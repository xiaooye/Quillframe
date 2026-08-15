#!/usr/bin/env python3
from pathlib import Path

# Retriggered after the kawaii v5 documentation baseline was registered.
path = Path('.github/workflows/studio-cloud.yml')
text = path.read_text(encoding='utf-8')

needle = '''          jq -e '.success == true' /tmp/studio-domain.json >/dev/null

          active=false
'''
insert = '''          jq -e '.success == true' /tmp/studio-domain.json >/dev/null

          # A Pages custom subdomain requires an exact CNAME to the production
          # project host. This is main-only infrastructure mutation. We create
          # the record only when the hostname is completely unused and refuse
          # to overwrite or reinterpret any existing DNS record.
          curl --silent --show-error --fail \\
            --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \\
            "${domain_api}" > /tmp/studio-domain-current.json
          zone_id=$(jq -r '.result.zone_tag // empty' /tmp/studio-domain-current.json)
          test -n "${zone_id}"
          dns_base="https://api.cloudflare.com/client/v4/zones/${zone_id}/dns_records"
          dns_target="${CLOUDFLARE_PROJECT_NAME}.pages.dev"
          curl --silent --show-error --fail --get \\
            --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \\
            --data-urlencode "name=${CLOUDFLARE_CUSTOM_DOMAIN}" \\
            "${dns_base}" > /tmp/studio-dns-records.json
          jq -e '.success == true' /tmp/studio-dns-records.json >/dev/null
          record_count=$(jq '.result | length' /tmp/studio-dns-records.json)
          if [ "${record_count}" = "0" ]; then
            payload=$(jq -nc \\
              --arg name "${CLOUDFLARE_CUSTOM_DOMAIN}" \\
              --arg content "${dns_target}" \\
              '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:true}')
            dns_status=$(curl --silent --show-error --output /tmp/studio-dns-created.json --write-out "%{http_code}" \\
              --request POST \\
              --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \\
              --header "Content-Type: application/json" \\
              --data "${payload}" \\
              "${dns_base}")
            case "${dns_status}" in 200|201) ;; *) cat /tmp/studio-dns-created.json; exit 1 ;; esac
            jq -e '.success == true' /tmp/studio-dns-created.json >/dev/null
          elif [ "${record_count}" = "1" ]; then
            existing_type=$(jq -r '.result[0].type' /tmp/studio-dns-records.json)
            existing_content=$(jq -r '.result[0].content' /tmp/studio-dns-records.json)
            if [ "${existing_type}" != "CNAME" ] || [ "${existing_content%.}" != "${dns_target%.}" ]; then
              echo "Refusing to overwrite conflicting DNS at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
              cat /tmp/studio-dns-records.json >&2
              exit 1
            fi
          else
            echo "Refusing ambiguous DNS state at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
            cat /tmp/studio-dns-records.json >&2
            exit 1
          fi

          active=false
'''

count = text.count(needle)
if count != 1:
    raise SystemExit(f'expected one production-domain insertion point, found {count}')
updated = text.replace(needle, insert)
if updated.count('dns_target="${CLOUDFLARE_PROJECT_NAME}.pages.dev"') != 1:
    raise SystemExit('DNS ensure block did not land exactly once')
path.write_text(updated, encoding='utf-8')
print('patched .github/workflows/studio-cloud.yml with fail-closed CNAME ensure')
