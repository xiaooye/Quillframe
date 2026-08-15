#!/usr/bin/env python3
from pathlib import Path

path = Path('.github/workflows/studio-cloud.yml')
text = path.read_text(encoding='utf-8')

old_comment = '''          # A Pages custom subdomain requires an exact CNAME to the production
          # project host. This is main-only infrastructure mutation. We create
          # the record only when the hostname is completely unused and refuse
          # to overwrite or reinterpret any existing DNS record.
'''
new_comment = '''          # A Pages custom subdomain requires an exact CNAME to the production
          # project host. Studio intentionally keeps this record DNS-only:
          # ordinary Cloudflare Bot Fight Mode is zone-wide and cannot be
          # skipped per hostname, while Pages supports DNS-only custom domains.
          # This is main-only infrastructure mutation. We refuse to overwrite
          # or reinterpret any conflicting DNS record.
'''
if text.count(old_comment) != 1:
    raise SystemExit('expected one Studio CNAME comment block')
text = text.replace(old_comment, new_comment)

old_create = '''              '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:true}')
'''
new_create = '''              '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:false}')
'''
if text.count(old_create) != 1:
    raise SystemExit('expected one proxied=true Studio CNAME create payload')
text = text.replace(old_create, new_create)

old_existing = '''          elif [ "${record_count}" = "1" ]; then
            existing_type=$(jq -r '.result[0].type' /tmp/studio-dns-records.json)
            existing_content=$(jq -r '.result[0].content' /tmp/studio-dns-records.json)
            if [ "${existing_type}" != "CNAME" ] || [ "${existing_content%.}" != "${dns_target%.}" ]; then
              echo "Refusing to overwrite conflicting DNS at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
              cat /tmp/studio-dns-records.json >&2
              exit 1
            fi
'''
new_existing = '''          elif [ "${record_count}" = "1" ]; then
            existing_type=$(jq -r '.result[0].type' /tmp/studio-dns-records.json)
            existing_content=$(jq -r '.result[0].content' /tmp/studio-dns-records.json)
            existing_proxied=$(jq -r '.result[0].proxied' /tmp/studio-dns-records.json)
            existing_id=$(jq -r '.result[0].id // empty' /tmp/studio-dns-records.json)
            if [ "${existing_type}" != "CNAME" ] || [ "${existing_content%.}" != "${dns_target%.}" ]; then
              echo "Refusing to overwrite conflicting DNS at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
              cat /tmp/studio-dns-records.json >&2
              exit 1
            fi
            if [ "${existing_proxied}" != "false" ]; then
              test -n "${existing_id}"
              dns_status=$(curl --silent --show-error --output /tmp/studio-dns-updated.json --write-out "%{http_code}" \\
                --request PATCH \\
                --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \\
                --header "Content-Type: application/json" \\
                --data '{"proxied":false}' \\
                "${dns_base}/${existing_id}")
              [ "${dns_status}" = "200" ] || { cat /tmp/studio-dns-updated.json; exit 1; }
              jq -e '.success == true and .result.proxied == false' /tmp/studio-dns-updated.json >/dev/null
            fi
'''
if text.count(old_existing) != 1:
    raise SystemExit('expected one existing Studio CNAME branch')
text = text.replace(old_existing, new_existing)

needle = '''          else
            echo "Refusing ambiguous DNS state at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
            cat /tmp/studio-dns-records.json >&2
            exit 1
          fi

          active=false
'''
replacement = '''          else
            echo "Refusing ambiguous DNS state at ${CLOUDFLARE_CUSTOM_DOMAIN}" >&2
            cat /tmp/studio-dns-records.json >&2
            exit 1
          fi

          curl --silent --show-error --fail --get \\
            --header "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \\
            --data-urlencode "name=${CLOUDFLARE_CUSTOM_DOMAIN}" \\
            "${dns_base}" > /tmp/studio-dns-final.json
          jq -e --arg target "${dns_target}" '\
            .success == true and (.result | length) == 1 and\
            .result[0].type == "CNAME" and\
            (.result[0].content | rtrimstr(".")) == ($target | rtrimstr(".")) and\
            .result[0].proxied == false\
          ' /tmp/studio-dns-final.json >/dev/null

          active=false
'''
if text.count(needle) != 1:
    raise SystemExit('expected one post-DNS verification insertion point')
text = text.replace(needle, replacement)

assert text.count('proxied:false') == 1
assert text.count("--data '{\"proxied\":false}'") == 1
assert 'Bot Fight Mode is zone-wide and cannot be' in text
path.write_text(text, encoding='utf-8')
print('patched Studio Pages DNS handling to DNS-only, fail-closed')
