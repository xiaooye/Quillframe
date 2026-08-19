ALTER TABLE project_projection_target_ownership
  ADD COLUMN authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0);
