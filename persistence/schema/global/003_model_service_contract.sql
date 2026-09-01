ALTER TABLE model_services ADD COLUMN protocol_family TEXT NOT NULL DEFAULT 'openai_chat_completions'
  CHECK(protocol_family IN ('openai_chat_completions','openai_responses','anthropic_messages'));
ALTER TABLE model_services ADD COLUMN allow_loopback_http INTEGER NOT NULL DEFAULT 0
  CHECK(allow_loopback_http IN (0,1));
ALTER TABLE model_services ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK(version >= 1);
