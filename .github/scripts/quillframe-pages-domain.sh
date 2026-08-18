#!/usr/bin/env bash
set -euo pipefail

project="${1:?Pages project name required}"
domain="${2:?custom domain required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required}"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is required}"

auth=(-H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}")
pages_base="https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/pages/projects/${project}"
domain_api="${pages_base}/domains/${domain}"

status=$(curl -sS -o /tmp/qf-domain.json -w '%{http_code}' "${auth[@]}" "${domain_api}")
if [[ "${status}" == "404" ]]; then
  payload=$(jq -nc --arg name "${domain}" '{name:$name}')
  status=$(curl -sS -o /tmp/qf-domain.json -w '%{http_code}' -X POST "${auth[@]}" -H 'Content-Type: application/json' --data "${payload}" "${pages_base}/domains")
fi
case "${status}" in 200|201) ;; *) cat /tmp/qf-domain.json; exit 1;; esac
jq -e '.success == true' /tmp/qf-domain.json >/dev/null

# Read the domain record again so Pages can provide the owning zone tag.
curl -fsS "${auth[@]}" "${domain_api}" -o /tmp/qf-domain-current.json
zone_id=$(jq -r '.result.zone_tag // empty' /tmp/qf-domain-current.json)
test -n "${zone_id}"

dns_base="https://api.cloudflare.com/client/v4/zones/${zone_id}/dns_records"
target="${project}.pages.dev"
curl -fsS --get "${auth[@]}" --data-urlencode "name=${domain}" "${dns_base}" -o /tmp/qf-dns.json
jq -e '.success == true' /tmp/qf-dns.json >/dev/null
count=$(jq '.result | length' /tmp/qf-dns.json)

if [[ "${count}" == "0" ]]; then
  payload=$(jq -nc --arg name "${domain}" --arg content "${target}" '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:false}')
  curl -fsS -X POST "${auth[@]}" -H 'Content-Type: application/json' --data "${payload}" "${dns_base}" -o /tmp/qf-dns-write.json
  jq -e '.success == true' /tmp/qf-dns-write.json >/dev/null
elif [[ "${count}" == "1" ]]; then
  type=$(jq -r '.result[0].type' /tmp/qf-dns.json)
  content=$(jq -r '.result[0].content' /tmp/qf-dns.json)
  proxied=$(jq -r '.result[0].proxied' /tmp/qf-dns.json)
  if [[ "${type}" != "CNAME" || "${content}" != "${target}" || "${proxied}" != "false" ]]; then
    echo "Refusing to overwrite conflicting DNS for ${domain}: type=${type} content=${content} proxied=${proxied}; expected CNAME ${target} proxied=false" >&2
    exit 1
  fi
else
  echo "Refusing ambiguous DNS mutation for ${domain}: found ${count} records" >&2
  jq '.result' /tmp/qf-dns.json >&2
  exit 1
fi

active=false
for attempt in $(seq 1 30); do
  curl -fsS "${auth[@]}" "${domain_api}" -o /tmp/qf-domain-post.json
  state=$(jq -r '.result.status // "unknown"' /tmp/qf-domain-post.json)
  if [[ "${state}" == "active" ]]; then active=true; break; fi
  sleep 4
done

if [[ "${active}" != "true" ]]; then
  echo "Pages custom domain did not become active: ${domain}" >&2
  cat /tmp/qf-domain-post.json >&2
  exit 1
fi

echo "Pages domain active: https://${domain} -> ${target}"
