"""Raw SQL for the initial schema (used by Alembic and by tests)."""
from __future__ import annotations

SCHEMA = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user NOLOGIN;
  END IF;
END $$;

CREATE TABLE academic_program (
  id serial PRIMARY KEY, code text UNIQUE NOT NULL, name text NOT NULL);

CREATE TABLE host_org (id serial PRIMARY KEY, name text NOT NULL);

CREATE TABLE user_account (
  id serial PRIMARY KEY,
  email text UNIQUE,
  display_name text NOT NULL,
  credits int, academic_level int, completed_courses text[] DEFAULT '{}');

CREATE TABLE role_assignment (
  id serial PRIMARY KEY,
  user_id int NOT NULL REFERENCES user_account(id),
  role text NOT NULL CHECK (role IN ('STUDENT','HOST_ORG_MEMBER','WORKPLACE_SUPERVISOR',
        'FACULTY_SUPERVISOR','PROGRAM_COORDINATOR','EXPERIENTIAL_COORDINATOR','LEGAL_REVIEWER')),
  program_id int REFERENCES academic_program(id),
  host_org_id int REFERENCES host_org(id),
  UNIQUE NULLS NOT DISTINCT (user_id, role, program_id, host_org_id));

CREATE TABLE invitation (
  id serial PRIMARY KEY,
  email text NOT NULL,
  host_org_id int NOT NULL REFERENCES host_org(id),
  role text NOT NULL CHECK (role IN ('HOST_ORG_MEMBER','WORKPLACE_SUPERVISOR')),
  token_hash text NOT NULL UNIQUE,
  created_by int REFERENCES user_account(id),
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE policy_version (
  id serial PRIMARY KEY, policy_key text NOT NULL, version_no int NOT NULL,
  conditions jsonb NOT NULL, effective_from timestamptz NOT NULL DEFAULT now(),
  created_by int REFERENCES user_account(id), UNIQUE (policy_key, version_no));

CREATE TABLE opportunity (
  id serial PRIMARY KEY, host_org_id int NOT NULL REFERENCES host_org(id),
  program_id int NOT NULL REFERENCES academic_program(id), title text NOT NULL,
  state text NOT NULL DEFAULT 'PUBLISHED');

CREATE TABLE application (
  id serial PRIMARY KEY, opportunity_id int NOT NULL REFERENCES opportunity(id),
  student_id int NOT NULL REFERENCES user_account(id),
  state text NOT NULL, policy_version_id int REFERENCES policy_version(id),
  eligibility_result jsonb);

CREATE TABLE placement (
  id serial PRIMARY KEY,
  application_id int NOT NULL UNIQUE REFERENCES application(id),
  state text NOT NULL CHECK (state IN ('PENDING_ACADEMIC_APPROVAL','REJECTED','DOCUMENTATION_PENDING',
        'ACTIVE','COMPLETED','CLOSED','CANCELLED')),
  activation_requirements_instantiated boolean NOT NULL DEFAULT false,
  completion_requirements_instantiated boolean NOT NULL DEFAULT false,
  current_version_id int);

CREATE TABLE placement_version (
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  version_no int NOT NULL, workplace_supervisor_id int REFERENCES user_account(id),
  start_date date NOT NULL, end_date date NOT NULL, location text NOT NULL, responsibilities text NOT NULL,
  status text NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','APPROVED','REJECTED')),
  decided_by int REFERENCES user_account(id), UNIQUE (placement_id, version_no));
ALTER TABLE placement ADD CONSTRAINT fk_current_version
  FOREIGN KEY (current_version_id) REFERENCES placement_version(id);

CREATE TABLE supervisor_assignment (
  placement_id int NOT NULL REFERENCES placement(id), user_id int NOT NULL REFERENCES user_account(id),
  kind text NOT NULL CHECK (kind IN ('FACULTY')), PRIMARY KEY (placement_id, user_id, kind));

CREATE TABLE checklist_item (
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL, mandatory boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'REQUIRED' CHECK (status IN ('REQUIRED','SUBMITTED','APPROVED','REJECTED')),
  UNIQUE (placement_id, kind));

CREATE TABLE completion_requirement (
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL, mandatory boolean NOT NULL DEFAULT true,
  satisfied boolean NOT NULL DEFAULT false, threshold numeric,
  UNIQUE (placement_id, kind));

CREATE VIEW v_placement_activation_compliance AS
SELECT p.id AS placement_id,
       (p.state = 'ACTIVE' AND EXISTS (
          SELECT 1 FROM checklist_item ci
          WHERE ci.placement_id = p.id AND ci.mandatory AND ci.status <> 'APPROVED')) AS activation_noncompliant
FROM placement p;

CREATE TABLE progress_entry (
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  student_id int NOT NULL REFERENCES user_account(id), hours numeric NOT NULL CHECK (hours > 0),
  created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE audit_event (
  id bigserial PRIMARY KEY, occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  actor_id int, action text NOT NULL, subject_type text NOT NULL, subject_id int NOT NULL,
  before_state jsonb, after_state jsonb, correlation_id text NOT NULL);

CREATE FUNCTION trg_placement_gate() RETURNS trigger AS $$
DECLARE n int;
BEGIN
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    IF NEW.state = 'ACTIVE' THEN
      IF OLD.state <> 'DOCUMENTATION_PENDING' THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> ACTIVE', OLD.state; END IF;
      IF NOT NEW.activation_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: activation requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
    ELSIF NEW.state = 'COMPLETED' THEN
      IF OLD.state <> 'ACTIVE' THEN RAISE EXCEPTION 'GATE: illegal transition % -> COMPLETED', OLD.state; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      IF NOT NEW.completion_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: completion requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM completion_requirement
        WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
    ELSIF NEW.state = 'CLOSED' THEN
      IF OLD.state <> 'COMPLETED' THEN RAISE EXCEPTION 'GATE: illegal transition % -> CLOSED', OLD.state; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      SELECT count(*) INTO n FROM completion_requirement
        WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_placement_gate BEFORE UPDATE OF state ON placement
  FOR EACH ROW EXECUTE FUNCTION trg_placement_gate();

CREATE FUNCTION trg_progress_gate() RETURNS trigger AS $$
BEGIN
  IF (SELECT state FROM placement WHERE id = NEW.placement_id) <> 'ACTIVE' THEN
    RAISE EXCEPTION 'GATE: progress/hours require an ACTIVE placement'; END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_progress_gate BEFORE INSERT ON progress_entry
  FOR EACH ROW EXECUTE FUNCTION trg_progress_gate();

CREATE FUNCTION trg_version_immutable() RETURNS trigger AS $$
BEGIN
  IF (NEW.placement_id, NEW.version_no, NEW.workplace_supervisor_id, NEW.start_date, NEW.end_date,
      NEW.location, NEW.responsibilities)
     IS DISTINCT FROM
     (OLD.placement_id, OLD.version_no, OLD.workplace_supervisor_id, OLD.start_date, OLD.end_date,
      OLD.location, OLD.responsibilities) THEN
    RAISE EXCEPTION 'IMMUTABLE: placement_version content cannot change'; END IF;
  IF OLD.status <> 'PROPOSED' AND NEW.status <> OLD.status THEN
    RAISE EXCEPTION 'IMMUTABLE: decided version status cannot change'; END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_version_immutable BEFORE UPDATE ON placement_version
  FOR EACH ROW EXECUTE FUNCTION trg_version_immutable();

CREATE FUNCTION trg_audit_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'IMMUTABLE: audit_event is append-only'; END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON audit_event
  FOR EACH ROW EXECUTE FUNCTION trg_audit_immutable();

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
REVOKE UPDATE ON audit_event FROM app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
"""

# Upgrade from the immutable 0001 schema. Kept separate from SCHEMA so the initial
# Alembic revision remains a faithful record of the schema it originally created.
UPGRADE_0002_SQL = """
ALTER TABLE placement
  ADD COLUMN IF NOT EXISTS activation_policy_version_id int REFERENCES policy_version(id),
  ADD COLUMN IF NOT EXISTS completion_policy_version_id int REFERENCES policy_version(id);

ALTER TABLE checklist_item
  ADD COLUMN IF NOT EXISTS current_submission_id bigint,
  ADD COLUMN IF NOT EXISTS current_review_reason text;

CREATE TABLE IF NOT EXISTS document_submission (
  id bigserial PRIMARY KEY,
  checklist_item_id int NOT NULL REFERENCES checklist_item(id),
  revision int NOT NULL CHECK (revision > 0),
  submitted_by int NOT NULL REFERENCES user_account(id),
  original_filename text NOT NULL,
  content_type text NOT NULL,
  content bytea NOT NULL,
  byte_size int NOT NULL CHECK (byte_size > 0 AND byte_size <= 10485760),
  sha256 text NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (checklist_item_id, revision),
  UNIQUE (id, checklist_item_id));

CREATE TABLE IF NOT EXISTS document_review (
  id bigserial PRIMARY KEY,
  checklist_item_id int NOT NULL,
  submission_id bigint,
  reviewer_id int NOT NULL REFERENCES user_account(id),
  decision text NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
  reason text NOT NULL CHECK (length(trim(reason)) > 0),
  reviewed_at timestamptz NOT NULL DEFAULT now());

CREATE OR REPLACE FUNCTION trg_policy_version_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'IMMUTABLE: policy_version is append-only'; END $$ LANGUAGE plpgsql;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_checklist_current_submission') THEN
    ALTER TABLE checklist_item ADD CONSTRAINT fk_checklist_current_submission
      FOREIGN KEY (current_submission_id, id)
      REFERENCES document_submission(id, checklist_item_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='document_review_submission_item_fkey') THEN
    ALTER TABLE document_review ADD CONSTRAINT document_review_submission_item_fkey
      FOREIGN KEY (submission_id, checklist_item_id)
      REFERENCES document_submission(id, checklist_item_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_policy_version_immutable'
                 AND tgrelid='policy_version'::regclass) THEN
    CREATE TRIGGER trg_policy_version_immutable BEFORE UPDATE OR DELETE ON policy_version
      FOR EACH ROW EXECUTE FUNCTION trg_policy_version_immutable();
  END IF;
END $$;

GRANT SELECT, INSERT, UPDATE ON document_submission, document_review TO app_user;
GRANT USAGE, SELECT ON SEQUENCE document_submission_id_seq, document_review_id_seq TO app_user;
"""

UPGRADE_0003_SQL = """
ALTER TABLE user_account
  ADD COLUMN IF NOT EXISTS username text,
  ADD COLUMN IF NOT EXISTS password_hash text,
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;

-- Existing rows keep their IDs, roles, and relationships, but must be claimed and
-- assigned a password by an operator before they can authenticate.
UPDATE user_account SET username='legacy-' || id::text, is_active=false
  WHERE username IS NULL;
ALTER TABLE user_account ALTER COLUMN username SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS user_account_username_lower_uidx
  ON user_account (lower(username));
CREATE UNIQUE INDEX IF NOT EXISTS user_account_email_lower_uidx
  ON user_account (lower(email)) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS auth_session (
  jti text PRIMARY KEY,
  user_id int NOT NULL REFERENCES user_account(id),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS auth_session_user_active_idx
  ON auth_session(user_id, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS auth_password_reset (
  token_hash text PRIMARY KEY,
  user_id int NOT NULL REFERENCES user_account(id),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  used_at timestamptz
);
CREATE INDEX IF NOT EXISTS auth_password_reset_user_active_idx
  ON auth_password_reset(user_id, expires_at) WHERE used_at IS NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON auth_session, auth_password_reset TO app_user;
"""

UPGRADE_0004_SQL = """
-- Serialize activation/completion gates with changes to mandatory checklist state.
CREATE OR REPLACE FUNCTION trg_placement_gate() RETURNS trigger AS $$
DECLARE n int;
BEGIN
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    -- Acquire the parent row before reading checklist/evidence requirements. The
    -- checklist trigger below takes the same lock when its state changes.
    PERFORM 1 FROM placement WHERE id = NEW.id FOR UPDATE;
    IF NEW.state = 'ACTIVE' THEN
      IF OLD.state <> 'DOCUMENTATION_PENDING' THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> ACTIVE', OLD.state; END IF;
      IF NOT NEW.activation_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: activation requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
    ELSIF NEW.state = 'COMPLETED' THEN
      IF OLD.state <> 'ACTIVE' THEN RAISE EXCEPTION 'GATE: illegal transition % -> COMPLETED', OLD.state; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      IF NOT NEW.completion_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: completion requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM completion_requirement
        WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
    ELSIF NEW.state = 'CLOSED' THEN
      IF OLD.state <> 'COMPLETED' THEN RAISE EXCEPTION 'GATE: illegal transition % -> CLOSED', OLD.state; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      SELECT count(*) INTO n FROM completion_requirement
        WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE FUNCTION trg_checklist_parent_lock() RETURNS trigger AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status THEN
    PERFORM 1 FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_checklist_parent_lock BEFORE UPDATE OF status ON checklist_item
  FOR EACH ROW EXECUTE FUNCTION trg_checklist_parent_lock();
"""

UPGRADE_0005_SQL = """
-- Persist follow-up records and final evidence as append-only source data.
CREATE TABLE placement_progress_report (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  revision int NOT NULL CHECK (revision > 0),
  author_id int NOT NULL REFERENCES user_account(id),
  content text NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 5000),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, revision)
);

CREATE TABLE placement_evaluation (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL CHECK (kind IN ('MIDTERM','FINAL')),
  revision int NOT NULL CHECK (revision > 0),
  evaluator_id int NOT NULL REFERENCES user_account(id),
  narrative text NOT NULL CHECK (length(trim(narrative)) BETWEEN 1 AND 8000),
  submitted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, kind, revision)
);

CREATE TABLE placement_incident (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL CHECK (kind IN ('INCIDENT','CHANGE')),
  revision int NOT NULL CHECK (revision > 0),
  reporter_id int NOT NULL REFERENCES user_account(id),
  summary text NOT NULL CHECK (length(trim(summary)) BETWEEN 1 AND 160),
  description text NOT NULL CHECK (length(trim(description)) BETWEEN 1 AND 5000),
  reported_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, revision)
);

CREATE TABLE completion_evidence (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL,
  kind text NOT NULL CHECK (kind = 'FINAL_REPORT'),
  revision int NOT NULL CHECK (revision > 0),
  submitted_by int NOT NULL REFERENCES user_account(id),
  original_filename text NOT NULL,
  content_type text NOT NULL,
  content bytea NOT NULL,
  byte_size int NOT NULL CHECK (byte_size > 0 AND byte_size <= 10485760),
  sha256 text NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, kind, revision),
  FOREIGN KEY (placement_id, kind)
    REFERENCES completion_requirement(placement_id, kind)
);

CREATE INDEX placement_progress_report_lookup_idx
  ON placement_progress_report(placement_id, revision DESC);
CREATE INDEX placement_evaluation_lookup_idx
  ON placement_evaluation(placement_id, kind, revision DESC);
CREATE INDEX placement_incident_lookup_idx
  ON placement_incident(placement_id, revision DESC);
CREATE INDEX completion_evidence_lookup_idx
  ON completion_evidence(placement_id, kind, revision DESC);

CREATE FUNCTION trg_placement_record_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'IMMUTABLE: lifecycle records are append-only';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_progress_report_immutable BEFORE UPDATE OR DELETE ON placement_progress_report
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();
CREATE TRIGGER trg_evaluation_immutable BEFORE UPDATE OR DELETE ON placement_evaluation
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();
CREATE TRIGGER trg_incident_immutable BEFORE UPDATE OR DELETE ON placement_incident
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();
CREATE TRIGGER trg_completion_evidence_immutable BEFORE UPDATE OR DELETE ON completion_evidence
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

CREATE FUNCTION trg_active_placement_record() RETURNS trigger AS $$
DECLARE
  current_state text;
  student_id int;
  assigned_supervisor_id int;
  v_host_org_id int;
  v_student_program_id int;
BEGIN
  SELECT state INTO current_state FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  IF current_state IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'PLACEMENT_NOT_ACTIVE: lifecycle records require an active placement';
  END IF;
  IF TG_TABLE_NAME = 'placement_progress_report' THEN
    SELECT a.student_id INTO student_id FROM placement p
      JOIN application a ON a.id=p.application_id WHERE p.id=NEW.placement_id;
    IF NEW.author_id <> student_id THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the placement student may submit this record';
    END IF;
  ELSIF TG_TABLE_NAME = 'completion_evidence' THEN
    SELECT a.student_id INTO student_id FROM placement p
      JOIN application a ON a.id=p.application_id WHERE p.id=NEW.placement_id;
    IF NEW.submitted_by <> student_id THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the placement student may submit this record';
    END IF;
  ELSIF TG_TABLE_NAME = 'placement_evaluation' THEN
    SELECT pv.workplace_supervisor_id INTO assigned_supervisor_id FROM placement p
      JOIN placement_version pv ON pv.id=p.current_version_id WHERE p.id=NEW.placement_id;
    SELECT o.host_org_id INTO v_host_org_id FROM placement p
      JOIN application a ON a.id=p.application_id
      JOIN opportunity o ON o.id=a.opportunity_id WHERE p.id=NEW.placement_id;
    IF NEW.evaluator_id IS DISTINCT FROM assigned_supervisor_id OR NOT EXISTS (
      SELECT 1 FROM role_assignment ra WHERE ra.user_id=NEW.evaluator_id
        AND ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=v_host_org_id
    ) THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the currently assigned workplace supervisor may evaluate';
    END IF;
  ELSIF TG_TABLE_NAME = 'placement_incident' THEN
    SELECT a.student_id, o.host_org_id INTO student_id, v_host_org_id FROM placement p
      JOIN application a ON a.id=p.application_id
      JOIN opportunity o ON o.id=a.opportunity_id WHERE p.id=NEW.placement_id;
    SELECT ra.program_id INTO v_student_program_id FROM role_assignment ra
      WHERE ra.user_id=student_id AND ra.role='STUDENT' ORDER BY ra.id LIMIT 1;
    IF NEW.reporter_id IS DISTINCT FROM student_id AND NOT EXISTS (
      SELECT 1 FROM role_assignment ra WHERE ra.user_id=NEW.reporter_id AND (
        (ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=v_host_org_id AND EXISTS (
          SELECT 1 FROM placement p JOIN placement_version pv ON pv.id=p.current_version_id
           WHERE p.id=NEW.placement_id AND pv.workplace_supervisor_id=ra.user_id
        )) OR
        (ra.role='FACULTY_SUPERVISOR' AND EXISTS (
          SELECT 1 FROM supervisor_assignment sa WHERE sa.placement_id=NEW.placement_id
            AND sa.user_id=ra.user_id AND sa.kind='FACULTY'
        )) OR
        (ra.role='PROGRAM_COORDINATOR' AND ra.program_id=v_student_program_id) OR
        ra.role='EXPERIENTIAL_COORDINATOR'
      )
    ) THEN
      RAISE EXCEPTION 'RELATIONSHIP: reporter is not an authorized participant in this placement';
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_progress_report_active BEFORE INSERT ON placement_progress_report
  FOR EACH ROW EXECUTE FUNCTION trg_active_placement_record();
CREATE TRIGGER trg_evaluation_active BEFORE INSERT ON placement_evaluation
  FOR EACH ROW EXECUTE FUNCTION trg_active_placement_record();
CREATE TRIGGER trg_incident_active BEFORE INSERT ON placement_incident
  FOR EACH ROW EXECUTE FUNCTION trg_active_placement_record();
CREATE TRIGGER trg_completion_evidence_active BEFORE INSERT ON completion_evidence
  FOR EACH ROW EXECUTE FUNCTION trg_active_placement_record();

GRANT SELECT, INSERT ON placement_progress_report, placement_evaluation,
  placement_incident, completion_evidence TO app_user;
GRANT USAGE, SELECT ON SEQUENCE placement_progress_report_id_seq,
  placement_evaluation_id_seq, placement_incident_id_seq,
  completion_evidence_id_seq TO app_user;

-- Recompute completion gates from source rows. Cached flags cannot stand in for evidence.
CREATE OR REPLACE FUNCTION trg_placement_gate() RETURNS trigger AS $$
DECLARE n int;
BEGIN
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    PERFORM 1 FROM placement WHERE id = NEW.id FOR UPDATE;
    IF NEW.state = 'ACTIVE' THEN
      IF OLD.state <> 'DOCUMENTATION_PENDING' THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> ACTIVE', OLD.state; END IF;
      IF NOT NEW.activation_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: activation requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
    ELSIF NEW.state IN ('COMPLETED','CLOSED') THEN
      IF (NEW.state = 'COMPLETED' AND OLD.state <> 'ACTIVE') OR
         (NEW.state = 'CLOSED' AND OLD.state <> 'COMPLETED') THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> %', OLD.state, NEW.state;
      END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      IF NOT NEW.completion_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: completion requirements not instantiated'; END IF;
      SELECT count(*) INTO n
        FROM completion_requirement cr
       WHERE cr.placement_id = NEW.id AND cr.mandatory AND (
         (cr.kind = 'MIN_HOURS' AND
           (cr.threshold IS NULL OR (SELECT coalesce(sum(pe.hours),0) FROM progress_entry pe
             WHERE pe.placement_id = NEW.id) < cr.threshold)) OR
         (cr.kind = 'FINAL_REPORT' AND NOT EXISTS (
           SELECT 1 FROM completion_evidence ce WHERE ce.placement_id = NEW.id AND ce.kind = cr.kind)) OR
         (cr.kind = 'FINAL_EVALUATION' AND NOT EXISTS (
           SELECT 1 FROM placement_evaluation ev WHERE ev.placement_id = NEW.id AND ev.kind = 'FINAL')) OR
         (cr.kind NOT IN ('MIN_HOURS','FINAL_REPORT','FINAL_EVALUATION') AND NOT cr.satisfied)
       );
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
"""

UPGRADE_0006_SQL = """
CREATE OR REPLACE FUNCTION trg_progress_gate() RETURNS trigger AS $$
DECLARE v_state text;
BEGIN
  SELECT state INTO v_state FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  IF v_state IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'GATE: progress/hours require an ACTIVE placement';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
"""

DOWNGRADE_0006_SQL = """
CREATE OR REPLACE FUNCTION trg_progress_gate() RETURNS trigger AS $$
BEGIN
  IF (SELECT state FROM placement WHERE id = NEW.placement_id) <> 'ACTIVE' THEN
    RAISE EXCEPTION 'GATE: progress/hours require an ACTIVE placement';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
"""

UPGRADE_0007_SQL = """
-- Persist workplace-supervisor work-plan assignments as auditable lifecycle records.
CREATE TABLE placement_work_plan_item (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  revision int NOT NULL CHECK (revision > 0),
  assigned_by int NOT NULL REFERENCES user_account(id),
  title text NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 160),
  description text NOT NULL CHECK (length(trim(description)) BETWEEN 1 AND 3000),
  assigned_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, revision)
);

CREATE INDEX placement_work_plan_lookup_idx
  ON placement_work_plan_item(placement_id, revision);

CREATE FUNCTION trg_work_plan_assignment_guard() RETURNS trigger AS $$
DECLARE
  v_supervisor_id int;
  v_host_org_id int;
  v_expected_revision int;
BEGIN
  SELECT pv.workplace_supervisor_id, o.host_org_id
    INTO v_supervisor_id, v_host_org_id
    FROM placement p
    JOIN application a ON a.id = p.application_id
    JOIN opportunity o ON o.id = a.opportunity_id
    LEFT JOIN placement_version pv ON pv.id = p.current_version_id
    WHERE p.id = NEW.placement_id
    FOR UPDATE OF p;

  IF v_supervisor_id IS NULL OR NEW.assigned_by <> v_supervisor_id OR NOT EXISTS (
    SELECT 1 FROM role_assignment ra
    WHERE ra.user_id = NEW.assigned_by AND ra.role = 'WORKPLACE_SUPERVISOR'
      AND ra.host_org_id = v_host_org_id
  ) THEN
    RAISE EXCEPTION 'RELATIONSHIP: only the currently assigned workplace supervisor may assign work-plan activities';
  END IF;

  SELECT coalesce(max(revision), 0) + 1 INTO v_expected_revision
    FROM placement_work_plan_item WHERE placement_id = NEW.placement_id;
  IF NEW.revision <> v_expected_revision THEN
    RAISE EXCEPTION 'REVISION: work-plan activity revision must be sequential';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_work_plan_assignment_guard
  BEFORE INSERT ON placement_work_plan_item
  FOR EACH ROW EXECUTE FUNCTION trg_work_plan_assignment_guard();
CREATE TRIGGER trg_work_plan_item_immutable
  BEFORE UPDATE OR DELETE ON placement_work_plan_item
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

GRANT SELECT, INSERT ON placement_work_plan_item TO app_user;
GRANT USAGE, SELECT ON SEQUENCE placement_work_plan_item_id_seq TO app_user;
"""

UPGRADE_0008_SQL = """
-- Reported is the only defined incident state until an institutional review
-- and resolution process is approved. Existing immutable rows receive this
-- truthful status; no review or resolution is inferred.
ALTER TABLE placement_incident
  ADD COLUMN status text NOT NULL DEFAULT 'REPORTED'
  CHECK (status = 'REPORTED');
"""

UPGRADE_0009_SQL = """
-- Serialize work-plan assignments with closure and reject inserts after CLOSED.
CREATE OR REPLACE FUNCTION trg_work_plan_assignment_guard() RETURNS trigger AS $$
DECLARE
  v_supervisor_id int;
  v_host_org_id int;
  v_expected_revision int;
  v_placement_state text;
BEGIN
  SELECT pv.workplace_supervisor_id, o.host_org_id, p.state
    INTO v_supervisor_id, v_host_org_id, v_placement_state
    FROM placement p
    JOIN application a ON a.id = p.application_id
    JOIN opportunity o ON o.id = a.opportunity_id
    LEFT JOIN placement_version pv ON pv.id = p.current_version_id
    WHERE p.id = NEW.placement_id
    FOR UPDATE OF p;

  IF v_placement_state = 'CLOSED' THEN
    RAISE EXCEPTION 'GATE: work-plan assignments are not allowed after placement closure';
  END IF;

  IF v_supervisor_id IS NULL OR NEW.assigned_by <> v_supervisor_id OR NOT EXISTS (
    SELECT 1 FROM role_assignment ra
    WHERE ra.user_id = NEW.assigned_by AND ra.role = 'WORKPLACE_SUPERVISOR'
      AND ra.host_org_id = v_host_org_id
  ) THEN
    RAISE EXCEPTION 'RELATIONSHIP: only the currently assigned workplace supervisor may assign work-plan activities';
  END IF;

  SELECT coalesce(max(revision), 0) + 1 INTO v_expected_revision
    FROM placement_work_plan_item WHERE placement_id = NEW.placement_id;
  IF NEW.revision <> v_expected_revision THEN
    RAISE EXCEPTION 'REVISION: work-plan activity revision must be sequential';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
"""

UPGRADE_0010_SQL = """
-- Durable, recipient-scoped notifications created atomically from lifecycle audit events.
CREATE TABLE user_notification (
  id bigserial PRIMARY KEY,
  recipient_id int NOT NULL REFERENCES user_account(id),
  source_event_id bigint NOT NULL REFERENCES audit_event(id),
  category text NOT NULL CHECK (category IN (
    'APPLICATION_SUBMITTED','APPLICATION_SELECTED','DOCUMENT_ACTIVITY',
    'PLACEMENT_ACTIVATED','PROGRESS_REPORTED','EVALUATION_SUBMITTED',
    'INCIDENT_REPORTED','CHANGE_REPORTED','PLACEMENT_COMPLETED','PLACEMENT_CLOSED','MESSAGE_RECEIVED'
  )),
  placement_id int REFERENCES placement(id),
  opportunity_id int REFERENCES opportunity(id),
  created_at timestamptz NOT NULL,
  read_at timestamptz,
  UNIQUE (recipient_id, source_event_id),
  CHECK (placement_id IS NOT NULL OR opportunity_id IS NOT NULL)
);
CREATE INDEX user_notification_inbox_idx
  ON user_notification(recipient_id, created_at DESC, id DESC);
CREATE INDEX user_notification_unread_idx
  ON user_notification(recipient_id, id) WHERE read_at IS NULL;
GRANT SELECT, INSERT, UPDATE ON user_notification TO app_user;
GRANT USAGE, SELECT ON SEQUENCE user_notification_id_seq TO app_user;

-- One persisted conversation per placement and audience. Workplace supervisors
-- can use JOINT only; ACADEMIC excludes them at the authorization boundary.
CREATE TABLE placement_conversation (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  audience text NOT NULL CHECK (audience IN ('JOINT','ACADEMIC')),
  created_by int NOT NULL REFERENCES user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, audience)
);
CREATE TABLE placement_message (
  id bigserial PRIMARY KEY,
  conversation_id bigint NOT NULL REFERENCES placement_conversation(id),
  author_id int NOT NULL REFERENCES user_account(id),
  content text NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 4000),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX placement_message_history_idx
  ON placement_message(conversation_id, id);
CREATE TRIGGER placement_message_immutable
  BEFORE UPDATE OR DELETE ON placement_message
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();
GRANT SELECT, INSERT ON placement_conversation, placement_message TO app_user;
GRANT USAGE, SELECT ON SEQUENCE placement_conversation_id_seq, placement_message_id_seq TO app_user;
"""

UPGRADE_0011_SQL = """
-- New opportunities begin as drafts. Existing published rows stay published;
-- no reviewer or publisher authority is inferred by this data migration.
ALTER TABLE opportunity ALTER COLUMN state SET DEFAULT 'DRAFT';
ALTER TABLE opportunity ADD CONSTRAINT opportunity_state_check
  CHECK (state IN ('DRAFT','IN_REVIEW','APPROVED','PUBLISHED','CLOSED'));

CREATE FUNCTION trg_opportunity_state_guard() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF current_user = 'app_user' AND NEW.state <> 'DRAFT' THEN
      RAISE EXCEPTION 'GATE: opportunities created by the application must begin as DRAFT';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.state IS DISTINCT FROM OLD.state AND NOT (
       (OLD.state = 'DRAFT' AND NEW.state IN ('IN_REVIEW','CLOSED'))
    OR (OLD.state = 'IN_REVIEW' AND NEW.state IN ('APPROVED','CLOSED'))
    OR (OLD.state = 'APPROVED' AND NEW.state IN ('PUBLISHED','CLOSED'))
    OR (OLD.state = 'PUBLISHED' AND NEW.state = 'CLOSED')
  ) THEN
    RAISE EXCEPTION 'GATE: invalid opportunity state transition % -> %', OLD.state, NEW.state;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER opportunity_state_guard BEFORE INSERT OR UPDATE OF state ON opportunity
  FOR EACH ROW EXECUTE FUNCTION trg_opportunity_state_guard();

ALTER TABLE user_notification DROP CONSTRAINT user_notification_category_check;
ALTER TABLE user_notification ADD CONSTRAINT user_notification_category_check
  CHECK (category IN (
    'APPLICATION_SUBMITTED','APPLICATION_SELECTED','DOCUMENT_ACTIVITY',
    'PLACEMENT_ACTIVATED','PROGRESS_REPORTED','EVALUATION_SUBMITTED',
    'INCIDENT_REPORTED','CHANGE_REPORTED','PLACEMENT_COMPLETED','PLACEMENT_CLOSED',
    'MESSAGE_RECEIVED','OPPORTUNITY_REVIEW','OPPORTUNITY_PUBLISHED','OPPORTUNITY_CLOSED'
  ));
"""

UPGRADE_0012_SQL = """
-- Append-only history for faculty assignment changes. Existing current assignments
-- remain as-is; no historical actor or timestamp is fabricated for them.
CREATE TABLE placement_faculty_assignment_history (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  faculty_user_id int NOT NULL REFERENCES user_account(id),
  actor_id int NOT NULL REFERENCES user_account(id),
  action text NOT NULL CHECK (action IN ('ASSIGNED','UNASSIGNED')),
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX placement_faculty_assignment_history_idx
  ON placement_faculty_assignment_history(placement_id, id);
CREATE TRIGGER placement_faculty_assignment_history_immutable
  BEFORE UPDATE OR DELETE ON placement_faculty_assignment_history
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

CREATE FUNCTION trg_supervisor_assignment_history() RETURNS trigger AS $$
DECLARE
  v_actor_id int;
  v_placement_id int;
  v_placement_state text;
BEGIN
  v_placement_id := coalesce(NEW.placement_id, OLD.placement_id);
  SELECT state INTO v_placement_state FROM placement WHERE id=v_placement_id FOR UPDATE;
  IF v_placement_state IN ('COMPLETED','CLOSED','REJECTED','CANCELLED') THEN
    RAISE EXCEPTION 'GATE: faculty assignment cannot change after placement completion';
  END IF;
  IF current_user = 'app_user' THEN
    v_actor_id := nullif(current_setting('dh05.actor_id', true), '')::int;
    IF v_actor_id IS NULL THEN
      RAISE EXCEPTION 'AUDIT: supervisor assignment requires a command actor';
    END IF;
    INSERT INTO placement_faculty_assignment_history(placement_id, faculty_user_id, actor_id, action)
      VALUES (v_placement_id,
              coalesce(NEW.user_id, OLD.user_id), v_actor_id,
              CASE WHEN TG_OP='INSERT' THEN 'ASSIGNED' ELSE 'UNASSIGNED' END);
  END IF;
  IF TG_OP='INSERT' THEN RETURN NEW; ELSE RETURN OLD; END IF;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER supervisor_assignment_history
  AFTER INSERT OR DELETE ON supervisor_assignment
  FOR EACH ROW EXECUTE FUNCTION trg_supervisor_assignment_history();

GRANT SELECT, INSERT, DELETE ON supervisor_assignment TO app_user;
GRANT SELECT, INSERT ON placement_faculty_assignment_history TO app_user;
GRANT USAGE, SELECT ON SEQUENCE placement_faculty_assignment_history_id_seq TO app_user;
"""

UPGRADE_0013_SQL = """
-- Replace the historical broad table/sequence grants with the least privileges
-- used by the application services. Keep app_user NOLOGIN; runtime logins must
-- receive SET (not ADMIN) membership in this role separately.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM app_user;

-- Application reads are scoped by service authorization and projection. The
-- migration ledger is intentionally reserved for the migration owner.
GRANT SELECT ON academic_program, application, audit_event, auth_password_reset,
  auth_session, checklist_item, completion_evidence, completion_requirement,
  document_review, document_submission, host_org, invitation, opportunity,
  placement, placement_conversation, placement_evaluation,
  placement_faculty_assignment_history, placement_incident, placement_message,
  placement_progress_report, placement_version, placement_work_plan_item,
  policy_version, progress_entry, role_assignment, supervisor_assignment,
  user_account, user_notification, v_placement_activation_compliance TO app_user;

GRANT INSERT ON application, audit_event, auth_password_reset, auth_session,
  checklist_item, completion_evidence, completion_requirement, document_review,
  document_submission, invitation, opportunity, placement, placement_conversation,
  placement_evaluation, placement_faculty_assignment_history, placement_incident,
  placement_message, placement_progress_report, placement_version,
  placement_work_plan_item, policy_version, progress_entry, role_assignment,
  supervisor_assignment, user_account, user_notification TO app_user;

GRANT UPDATE ON application, auth_password_reset, auth_session, checklist_item,
  completion_requirement, invitation, opportunity, placement, placement_version,
  user_account, user_notification TO app_user;

GRANT DELETE ON auth_password_reset, auth_session, supervisor_assignment TO app_user;

-- USAGE supports default nextval() and currval(); SELECT/UPDATE sequence rights
-- are not required by application code.
GRANT USAGE ON SEQUENCE application_id_seq, audit_event_id_seq,
  checklist_item_id_seq, completion_evidence_id_seq, completion_requirement_id_seq,
  document_review_id_seq, document_submission_id_seq, invitation_id_seq,
  opportunity_id_seq, placement_conversation_id_seq, placement_evaluation_id_seq,
  placement_faculty_assignment_history_id_seq, placement_id_seq,
  placement_incident_id_seq, placement_message_id_seq, placement_progress_report_id_seq,
  placement_version_id_seq, placement_work_plan_item_id_seq, policy_version_id_seq,
  progress_entry_id_seq, role_assignment_id_seq, user_account_id_seq,
  user_notification_id_seq TO app_user;

"""

UPGRADE_0014_SQL = """
-- Add a distinct notification category for manual eligibility review requests
-- and decisions. No existing notifications or application records are rewritten.
ALTER TABLE user_notification DROP CONSTRAINT user_notification_category_check;
ALTER TABLE user_notification ADD CONSTRAINT user_notification_category_check
  CHECK (category IN (
    'APPLICATION_SUBMITTED','APPLICATION_SELECTED','ELIGIBILITY_REVIEW','DOCUMENT_ACTIVITY',
    'PLACEMENT_ACTIVATED','PROGRESS_REPORTED','EVALUATION_SUBMITTED',
    'INCIDENT_REPORTED','CHANGE_REPORTED','PLACEMENT_COMPLETED','PLACEMENT_CLOSED',
    'MESSAGE_RECEIVED','OPPORTUNITY_REVIEW','OPPORTUNITY_PUBLISHED','OPPORTUNITY_CLOSED'
  ));
"""

UPGRADE_0015_SQL = """
-- Preserve the approved placement version that was in force when each
-- post-activation record was written. Existing rows remain NULL because their
-- historical version context is not reconstructed retroactively.
ALTER TABLE progress_entry
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);
ALTER TABLE placement_progress_report
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);
ALTER TABLE placement_work_plan_item
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);
ALTER TABLE placement_evaluation
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);
ALTER TABLE placement_incident
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);
ALTER TABLE completion_evidence
  ADD COLUMN IF NOT EXISTS placement_version_id int REFERENCES placement_version(id);

CREATE INDEX IF NOT EXISTS progress_entry_version_lookup_idx
  ON progress_entry(placement_id, placement_version_id, id);
CREATE INDEX IF NOT EXISTS placement_progress_report_version_lookup_idx
  ON placement_progress_report(placement_id, placement_version_id, revision);
CREATE INDEX IF NOT EXISTS placement_work_plan_version_lookup_idx
  ON placement_work_plan_item(placement_id, placement_version_id, revision);
CREATE INDEX IF NOT EXISTS placement_evaluation_version_lookup_idx
  ON placement_evaluation(placement_id, placement_version_id, kind, revision);
CREATE INDEX IF NOT EXISTS placement_incident_version_lookup_idx
  ON placement_incident(placement_id, placement_version_id, revision);
CREATE INDEX IF NOT EXISTS completion_evidence_version_lookup_idx
  ON completion_evidence(placement_id, placement_version_id, kind, revision);

CREATE FUNCTION trg_lifecycle_version_context() RETURNS trigger AS $$
DECLARE
  current_version_id int;
BEGIN
  IF NEW.placement_version_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT p.current_version_id INTO current_version_id
    FROM placement p WHERE p.id = NEW.placement_id FOR UPDATE;
  IF current_version_id IS DISTINCT FROM NEW.placement_version_id
     OR NOT EXISTS (
       SELECT 1 FROM placement_version v
       WHERE v.id = NEW.placement_version_id
         AND v.placement_id = NEW.placement_id
         AND v.status = 'APPROVED'
     ) THEN
    RAISE EXCEPTION 'VERSION_CONTEXT: record must reference the approved current placement version';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER progress_entry_version_context
  BEFORE INSERT ON progress_entry
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();
CREATE TRIGGER placement_progress_report_version_context
  BEFORE INSERT ON placement_progress_report
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();
CREATE TRIGGER placement_work_plan_version_context
  BEFORE INSERT ON placement_work_plan_item
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();
CREATE TRIGGER placement_evaluation_version_context
  BEFORE INSERT ON placement_evaluation
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();
CREATE TRIGGER placement_incident_version_context
  BEFORE INSERT ON placement_incident
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();
CREATE TRIGGER completion_evidence_version_context
  BEFORE INSERT ON completion_evidence
  FOR EACH ROW EXECUTE FUNCTION trg_lifecycle_version_context();

GRANT SELECT, INSERT ON progress_entry, placement_progress_report,
  placement_work_plan_item, placement_evaluation, placement_incident,
  completion_evidence TO app_user;
"""

UPGRADE_0016_SQL = """
-- CR-05 Rotational placements and mid-placement transfers.
-- The placement keeps the academic identity (CR-05-BR-01). Each segment keeps
-- its own organization/unit, supervisor, dates, modality, responsibilities,
-- expected hours, records and status history (CR-05-BR-03).
CREATE TABLE placement_segment (
  id serial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  sequence_no int NOT NULL CHECK (sequence_no > 0),
  host_org_id int NOT NULL REFERENCES host_org(id),
  unit text CHECK (unit IS NULL OR length(trim(unit)) BETWEEN 1 AND 160),
  workplace_supervisor_id int REFERENCES user_account(id),
  start_date date NOT NULL,
  end_date date NOT NULL,
  modality text CHECK (modality IN ('ONSITE','REMOTE','HYBRID')),
  responsibilities text NOT NULL CHECK (length(trim(responsibilities)) BETWEEN 1 AND 5000),
  expected_hours numeric CHECK (expected_hours IS NULL OR expected_hours > 0),
  origin text NOT NULL CHECK (origin IN ('PLACEMENT_ACTIVATION','MIGRATED_SINGLE','ROTATION','TRANSFER')),
  status text NOT NULL DEFAULT 'PLANNED'
    CHECK (status IN ('PLANNED','ACTIVE','COMPLETED','TERMINATED_EARLY','TRANSFERRED','CANCELLED')),
  activated_at timestamptz,
  activated_by int REFERENCES user_account(id),
  ended_on date,
  ended_at timestamptz,
  ended_by int REFERENCES user_account(id),
  end_reason_shared text CHECK (end_reason_shared IS NULL OR length(trim(end_reason_shared)) BETWEEN 1 AND 1000),
  end_reason_internal text CHECK (end_reason_internal IS NULL OR length(trim(end_reason_internal)) BETWEEN 1 AND 3000),
  work_recognition text CHECK (work_recognition IN ('ACCEPTED_HOURS_RECOGNIZED','NOT_RECOGNIZED')),
  recognition_note text CHECK (recognition_note IS NULL OR length(trim(recognition_note)) BETWEEN 1 AND 1000),
  created_by int REFERENCES user_account(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placement_id, sequence_no),
  UNIQUE (id, placement_id),
  CHECK (end_date >= start_date),
  CHECK (unit IS NOT NULL OR origin IN ('PLACEMENT_ACTIVATION','MIGRATED_SINGLE')),
  CHECK (modality IS NOT NULL OR origin IN ('PLACEMENT_ACTIVATION','MIGRATED_SINGLE')),
  CHECK ((status IN ('COMPLETED','TERMINATED_EARLY','TRANSFERRED')) = (work_recognition IS NOT NULL)),
  CHECK (status NOT IN ('COMPLETED','TERMINATED_EARLY','TRANSFERRED')
         OR ended_on IS NOT NULL OR origin = 'MIGRATED_SINGLE'),
  CHECK (status NOT IN ('TERMINATED_EARLY','TRANSFERRED','CANCELLED') OR end_reason_shared IS NOT NULL)
);
-- One operational segment at a time per placement (documented default; overlap
-- of calendar dates is recorded, but simultaneous operation needs a policy).
CREATE UNIQUE INDEX placement_one_active_segment ON placement_segment(placement_id)
  WHERE status = 'ACTIVE';
CREATE INDEX placement_segment_supervisor_idx ON placement_segment(workplace_supervisor_id, status);

CREATE TABLE placement_segment_condition (
  id serial PRIMARY KEY,
  segment_id int NOT NULL REFERENCES placement_segment(id),
  kind text NOT NULL CHECK (length(trim(kind)) BETWEEN 1 AND 80),
  source_policy_version_id int REFERENCES policy_version(id),
  status text NOT NULL DEFAULT 'REQUIRED' CHECK (status IN ('REQUIRED','SATISFIED')),
  confirmed_by int REFERENCES user_account(id),
  confirmed_at timestamptz,
  reference text CHECK (reference IS NULL OR length(trim(reference)) BETWEEN 1 AND 500),
  UNIQUE (segment_id, kind),
  CHECK ((status = 'SATISFIED') = (confirmed_at IS NOT NULL))
);

CREATE TABLE placement_segment_status_history (
  id bigserial PRIMARY KEY,
  segment_id int NOT NULL REFERENCES placement_segment(id),
  from_status text,
  to_status text NOT NULL,
  actor_id int REFERENCES user_account(id),
  changed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX placement_segment_status_history_idx ON placement_segment_status_history(segment_id, id);

CREATE TABLE placement_transfer (
  id serial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  from_segment_id int NOT NULL,
  to_segment_id int NOT NULL UNIQUE,
  effective_date date NOT NULL,
  reason_shared text NOT NULL CHECK (length(trim(reason_shared)) BETWEEN 1 AND 1000),
  reason_internal text CHECK (reason_internal IS NULL OR length(trim(reason_internal)) BETWEEN 1 AND 3000),
  prior_work_treatment text NOT NULL CHECK (prior_work_treatment IN ('ACCEPTED_HOURS_RECOGNIZED','NOT_RECOGNIZED')),
  approved_by int NOT NULL REFERENCES user_account(id),
  approved_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (from_segment_id, placement_id) REFERENCES placement_segment(id, placement_id),
  FOREIGN KEY (to_segment_id, placement_id) REFERENCES placement_segment(id, placement_id),
  CHECK (from_segment_id <> to_segment_id)
);

CREATE TABLE progress_entry_review (
  id bigserial PRIMARY KEY,
  entry_id int NOT NULL REFERENCES progress_entry(id),
  decision text NOT NULL CHECK (decision IN ('ACCEPTED','REJECTED','DISPUTED')),
  accepted_hours numeric,
  reason_code text CHECK (reason_code IN ('DUPLICATE','OUTSIDE_SEGMENT','NOT_VERIFIABLE','OTHER')),
  reason text CHECK (reason IS NULL OR length(trim(reason)) BETWEEN 1 AND 1000),
  reviewer_id int NOT NULL REFERENCES user_account(id),
  reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK ((decision = 'ACCEPTED') = (accepted_hours IS NOT NULL)),
  CHECK (accepted_hours IS NULL OR accepted_hours > 0),
  CHECK (decision = 'ACCEPTED' OR reason IS NOT NULL)
);
CREATE INDEX progress_entry_review_lookup_idx ON progress_entry_review(entry_id, id DESC);

CREATE TABLE placement_experience_review (
  id bigserial PRIMARY KEY,
  placement_id int NOT NULL REFERENCES placement(id),
  decision text NOT NULL CHECK (decision IN ('APPROVED','CHANGES_REQUIRED')),
  rationale text NOT NULL CHECK (length(trim(rationale)) BETWEEN 1 AND 3000),
  reviewer_id int NOT NULL REFERENCES user_account(id),
  reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX placement_experience_review_idx ON placement_experience_review(placement_id, id DESC);

-- Segment context on follow-up records. NULL keeps legacy/unknown context honest.
ALTER TABLE progress_entry ADD COLUMN segment_id int;
ALTER TABLE progress_entry ADD COLUMN work_date date;
ALTER TABLE progress_entry ADD COLUMN description text
  CHECK (description IS NULL OR length(trim(description)) BETWEEN 1 AND 1000);
ALTER TABLE placement_evaluation ADD COLUMN segment_id int;
ALTER TABLE placement_work_plan_item ADD COLUMN segment_id int;
ALTER TABLE placement_progress_report ADD COLUMN segment_id int;
ALTER TABLE placement_incident ADD COLUMN segment_id int;
ALTER TABLE progress_entry ADD CONSTRAINT progress_entry_segment_fk
  FOREIGN KEY (segment_id, placement_id) REFERENCES placement_segment(id, placement_id);
ALTER TABLE placement_evaluation ADD CONSTRAINT placement_evaluation_segment_fk
  FOREIGN KEY (segment_id, placement_id) REFERENCES placement_segment(id, placement_id);
ALTER TABLE placement_work_plan_item ADD CONSTRAINT placement_work_plan_segment_fk
  FOREIGN KEY (segment_id, placement_id) REFERENCES placement_segment(id, placement_id);
ALTER TABLE placement_progress_report ADD CONSTRAINT placement_progress_report_segment_fk
  FOREIGN KEY (segment_id, placement_id) REFERENCES placement_segment(id, placement_id);
ALTER TABLE placement_incident ADD CONSTRAINT placement_incident_segment_fk
  FOREIGN KEY (segment_id, placement_id) REFERENCES placement_segment(id, placement_id);
CREATE INDEX progress_entry_segment_idx ON progress_entry(placement_id, segment_id, work_date);

-- CR-05-BR-10 compatibility: every practice that already started gets exactly
-- one segment mirroring its current approved version. Unit and modality were
-- never captured, so they stay NULL instead of being invented. No end date is
-- fabricated for practices that were already completed.
INSERT INTO placement_segment(placement_id, sequence_no, host_org_id, unit, workplace_supervisor_id,
  start_date, end_date, modality, responsibilities, origin, status, work_recognition)
SELECT p.id, 1, o.host_org_id, NULL, pv.workplace_supervisor_id, pv.start_date, pv.end_date, NULL,
       pv.responsibilities, 'MIGRATED_SINGLE',
       CASE WHEN p.state = 'ACTIVE' THEN 'ACTIVE' ELSE 'COMPLETED' END,
       CASE WHEN p.state = 'ACTIVE' THEN NULL ELSE 'ACCEPTED_HOURS_RECOGNIZED' END
FROM placement p
JOIN application a ON a.id = p.application_id
JOIN opportunity o ON o.id = a.opportunity_id
JOIN placement_version pv ON pv.id = p.current_version_id
WHERE p.state IN ('ACTIVE','COMPLETED','CLOSED');

ALTER TABLE placement_evaluation DISABLE TRIGGER trg_evaluation_immutable;
ALTER TABLE placement_work_plan_item DISABLE TRIGGER trg_work_plan_item_immutable;
ALTER TABLE placement_progress_report DISABLE TRIGGER trg_progress_report_immutable;
ALTER TABLE placement_incident DISABLE TRIGGER trg_incident_immutable;
UPDATE progress_entry r SET segment_id = s.id FROM placement_segment s
  WHERE s.placement_id = r.placement_id AND s.origin = 'MIGRATED_SINGLE';
UPDATE placement_evaluation r SET segment_id = s.id FROM placement_segment s
  WHERE s.placement_id = r.placement_id AND s.origin = 'MIGRATED_SINGLE';
UPDATE placement_work_plan_item r SET segment_id = s.id FROM placement_segment s
  WHERE s.placement_id = r.placement_id AND s.origin = 'MIGRATED_SINGLE';
UPDATE placement_progress_report r SET segment_id = s.id FROM placement_segment s
  WHERE s.placement_id = r.placement_id AND s.origin = 'MIGRATED_SINGLE';
UPDATE placement_incident r SET segment_id = s.id FROM placement_segment s
  WHERE s.placement_id = r.placement_id AND s.origin = 'MIGRATED_SINGLE';
ALTER TABLE placement_evaluation ENABLE TRIGGER trg_evaluation_immutable;
ALTER TABLE placement_work_plan_item ENABLE TRIGGER trg_work_plan_item_immutable;
ALTER TABLE placement_progress_report ENABLE TRIGGER trg_progress_report_immutable;
ALTER TABLE placement_incident ENABLE TRIGGER trg_incident_immutable;

-- Operational workplace supervisor: the ACTIVE segment once segments exist;
-- before activation, the current placement version (E3 behaviour).
CREATE FUNCTION placement_operational_supervisor(p_placement_id int)
RETURNS TABLE(supervisor_id int, host_org_id int, segment_id int) AS $$
#variable_conflict use_column
BEGIN
  IF EXISTS (SELECT 1 FROM placement_segment s WHERE s.placement_id = p_placement_id) THEN
    RETURN QUERY SELECT s.workplace_supervisor_id, s.host_org_id, s.id FROM placement_segment s
      WHERE s.placement_id = p_placement_id AND s.status = 'ACTIVE';
  ELSE
    RETURN QUERY SELECT pv.workplace_supervisor_id, o.host_org_id, NULL::int
      FROM placement p JOIN application a ON a.id = p.application_id
      JOIN opportunity o ON o.id = a.opportunity_id
      LEFT JOIN placement_version pv ON pv.id = p.current_version_id
      WHERE p.id = p_placement_id;
  END IF;
END $$ LANGUAGE plpgsql STABLE;

-- Latest review decides the state of an hour entry. Only ACCEPTED hours of
-- segments whose work is recognized count; each entry is one row, so the same
-- reported work is never summed twice (CR-05-BR-04).
CREATE FUNCTION placement_accepted_hours(p_placement_id int) RETURNS numeric AS $$
  SELECT coalesce(sum(r.accepted_hours), 0)
  FROM progress_entry pe
  JOIN LATERAL (SELECT decision, accepted_hours FROM progress_entry_review rv
                WHERE rv.entry_id = pe.id ORDER BY rv.id DESC LIMIT 1) r ON true
  LEFT JOIN placement_segment s ON s.id = pe.segment_id
  WHERE pe.placement_id = p_placement_id AND r.decision = 'ACCEPTED'
    AND s.work_recognition IS DISTINCT FROM 'NOT_RECOGNIZED'
$$ LANGUAGE sql STABLE;

CREATE FUNCTION placement_pending_hour_entries(p_placement_id int) RETURNS int AS $$
  SELECT count(*)::int
  FROM progress_entry pe
  LEFT JOIN LATERAL (SELECT decision FROM progress_entry_review rv
                     WHERE rv.entry_id = pe.id ORDER BY rv.id DESC LIMIT 1) r ON true
  LEFT JOIN placement_segment s ON s.id = pe.segment_id
  WHERE pe.placement_id = p_placement_id
    AND (r.decision IS NULL OR r.decision = 'DISPUTED')
    AND s.work_recognition IS DISTINCT FROM 'NOT_RECOGNIZED'
$$ LANGUAGE sql STABLE;

-- Supervisor/evaluator relationship now follows the active segment.
CREATE OR REPLACE FUNCTION trg_active_placement_record() RETURNS trigger AS $$
DECLARE
  current_state text;
  student_id int;
  v_sup int;
  v_org int;
  v_seg int;
  v_student_program_id int;
BEGIN
  SELECT state INTO current_state FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  IF current_state IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'PLACEMENT_NOT_ACTIVE: lifecycle records require an active placement';
  END IF;
  IF TG_TABLE_NAME = 'placement_progress_report' THEN
    SELECT a.student_id INTO student_id FROM placement p
      JOIN application a ON a.id=p.application_id WHERE p.id=NEW.placement_id;
    IF NEW.author_id <> student_id THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the placement student may submit this record';
    END IF;
  ELSIF TG_TABLE_NAME = 'completion_evidence' THEN
    SELECT a.student_id INTO student_id FROM placement p
      JOIN application a ON a.id=p.application_id WHERE p.id=NEW.placement_id;
    IF NEW.submitted_by <> student_id THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the placement student may submit this record';
    END IF;
  ELSIF TG_TABLE_NAME = 'placement_evaluation' THEN
    SELECT os.supervisor_id, os.host_org_id, os.segment_id INTO v_sup, v_org, v_seg
      FROM placement_operational_supervisor(NEW.placement_id) os;
    IF v_sup IS NULL OR NEW.evaluator_id IS DISTINCT FROM v_sup
       OR (v_seg IS NOT NULL AND NEW.segment_id IS DISTINCT FROM v_seg)
       OR NOT EXISTS (
         SELECT 1 FROM role_assignment ra WHERE ra.user_id=NEW.evaluator_id
           AND ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=v_org) THEN
      RAISE EXCEPTION 'RELATIONSHIP: only the currently assigned workplace supervisor may evaluate';
    END IF;
  ELSIF TG_TABLE_NAME = 'placement_incident' THEN
    SELECT a.student_id INTO student_id FROM placement p
      JOIN application a ON a.id=p.application_id WHERE p.id=NEW.placement_id;
    SELECT ra.program_id INTO v_student_program_id FROM role_assignment ra
      WHERE ra.user_id=student_id AND ra.role='STUDENT' ORDER BY ra.id LIMIT 1;
    IF NEW.reporter_id IS DISTINCT FROM student_id AND NOT EXISTS (
      SELECT 1 FROM role_assignment ra WHERE ra.user_id=NEW.reporter_id AND (
        (ra.role='WORKPLACE_SUPERVISOR' AND EXISTS (
          SELECT 1 FROM placement_operational_supervisor(NEW.placement_id) os
           WHERE os.supervisor_id=ra.user_id AND os.host_org_id=ra.host_org_id
        )) OR
        (ra.role='FACULTY_SUPERVISOR' AND EXISTS (
          SELECT 1 FROM supervisor_assignment sa WHERE sa.placement_id=NEW.placement_id
            AND sa.user_id=ra.user_id AND sa.kind='FACULTY'
        )) OR
        (ra.role='PROGRAM_COORDINATOR' AND ra.program_id=v_student_program_id) OR
        ra.role='EXPERIENTIAL_COORDINATOR'
      )
    ) THEN
      RAISE EXCEPTION 'RELATIONSHIP: reporter is not an authorized participant in this placement';
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION trg_work_plan_assignment_guard() RETURNS trigger AS $$
DECLARE
  v_sup int;
  v_org int;
  v_seg int;
  v_expected_revision int;
  v_placement_state text;
BEGIN
  SELECT p.state INTO v_placement_state FROM placement p WHERE p.id = NEW.placement_id FOR UPDATE;
  IF v_placement_state = 'CLOSED' THEN
    RAISE EXCEPTION 'GATE: work-plan assignments are not allowed after placement closure';
  END IF;
  SELECT os.supervisor_id, os.host_org_id, os.segment_id INTO v_sup, v_org, v_seg
    FROM placement_operational_supervisor(NEW.placement_id) os;
  IF v_sup IS NULL OR NEW.assigned_by <> v_sup
     OR (v_seg IS NOT NULL AND NEW.segment_id IS DISTINCT FROM v_seg)
     OR NOT EXISTS (
       SELECT 1 FROM role_assignment ra
       WHERE ra.user_id = NEW.assigned_by AND ra.role = 'WORKPLACE_SUPERVISOR'
         AND ra.host_org_id = v_org) THEN
    RAISE EXCEPTION 'RELATIONSHIP: only the currently assigned workplace supervisor may assign work-plan activities';
  END IF;
  SELECT coalesce(max(revision), 0) + 1 INTO v_expected_revision
    FROM placement_work_plan_item WHERE placement_id = NEW.placement_id;
  IF NEW.revision <> v_expected_revision THEN
    RAISE EXCEPTION 'REVISION: work-plan activity revision must be sequential';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

-- Records written while a segment exists must name the ACTIVE segment. Trigger
-- names start with zz_ so that E3 relationship/version guards (fired alphabetically)
-- keep reporting their own errors first.
CREATE FUNCTION trg_segment_record_context() RETURNS trigger AS $$
DECLARE
  v_seg_id int;
  v_seg_status text;
  v_seg_start date;
  v_seg_end date;
  v_day_total numeric;
BEGIN
  PERFORM 1 FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  IF NEW.segment_id IS NOT NULL THEN
    SELECT id, status, start_date, end_date INTO v_seg_id, v_seg_status, v_seg_start, v_seg_end
      FROM placement_segment WHERE id = NEW.segment_id AND placement_id = NEW.placement_id;
    IF v_seg_id IS NULL OR v_seg_status <> 'ACTIVE' THEN
      RAISE EXCEPTION 'SEGMENT_CONTEXT: records may only be attached to the active segment';
    END IF;
  ELSIF TG_TABLE_NAME IN ('progress_entry','placement_evaluation','placement_work_plan_item')
        AND EXISTS (SELECT 1 FROM placement_segment WHERE placement_id = NEW.placement_id) THEN
    RAISE EXCEPTION 'SEGMENT_CONTEXT: this record requires the active segment of the placement';
  END IF;
  IF TG_TABLE_NAME = 'progress_entry' THEN
   IF NEW.work_date IS NOT NULL THEN
    IF NEW.work_date > current_date THEN
      RAISE EXCEPTION 'HOURS_WORK_DATE_INVALID: work date cannot be in the future';
    END IF;
    IF v_seg_id IS NOT NULL AND (NEW.work_date < v_seg_start OR NEW.work_date > v_seg_end) THEN
      RAISE EXCEPTION 'HOURS_WORK_DATE_INVALID: work date is outside the segment period';
    END IF;
    SELECT coalesce(sum(pe.hours), 0) INTO v_day_total
      FROM progress_entry pe
      LEFT JOIN LATERAL (SELECT decision FROM progress_entry_review rv
                         WHERE rv.entry_id = pe.id ORDER BY rv.id DESC LIMIT 1) r ON true
      WHERE pe.placement_id = NEW.placement_id AND pe.work_date = NEW.work_date
        AND r.decision IS DISTINCT FROM 'REJECTED';
    IF v_day_total + NEW.hours > 24 THEN
      RAISE EXCEPTION 'HOURS_DAILY_LIMIT: more than 24 hours reported for the same work date';
    END IF;
   END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER zz_progress_entry_segment_context BEFORE INSERT ON progress_entry
  FOR EACH ROW EXECUTE FUNCTION trg_segment_record_context();
CREATE TRIGGER zz_placement_evaluation_segment_context BEFORE INSERT ON placement_evaluation
  FOR EACH ROW EXECUTE FUNCTION trg_segment_record_context();
CREATE TRIGGER zz_placement_work_plan_segment_context BEFORE INSERT ON placement_work_plan_item
  FOR EACH ROW EXECUTE FUNCTION trg_segment_record_context();
CREATE TRIGGER zz_placement_progress_report_segment_context BEFORE INSERT ON placement_progress_report
  FOR EACH ROW EXECUTE FUNCTION trg_segment_record_context();
CREATE TRIGGER zz_placement_incident_segment_context BEFORE INSERT ON placement_incident
  FOR EACH ROW EXECUTE FUNCTION trg_segment_record_context();

-- Segment lifecycle guard: content is immutable; transitions are explicit;
-- activation never follows automatically from completing another segment.
CREATE FUNCTION trg_placement_segment_guard() RETURNS trigger AS $$
DECLARE
  v_state text;
  v_unmet int;
BEGIN
  SELECT state INTO v_state FROM placement WHERE id = NEW.placement_id FOR UPDATE;
  IF TG_OP = 'INSERT' THEN
    IF NEW.origin IN ('ROTATION','TRANSFER') THEN
      IF NEW.status <> 'PLANNED' THEN
        RAISE EXCEPTION 'SEGMENT_GATE: new rotation/transfer segments start as PLANNED';
      END IF;
      IF v_state IS DISTINCT FROM 'ACTIVE' THEN
        RAISE EXCEPTION 'SEGMENT_GATE: segments can only be planned for an active placement';
      END IF;
    ELSIF NEW.origin = 'PLACEMENT_ACTIVATION' AND v_state IS DISTINCT FROM 'ACTIVE' THEN
      RAISE EXCEPTION 'SEGMENT_GATE: the initial segment is created by placement activation';
    END IF;
    IF NEW.workplace_supervisor_id IS NOT NULL AND NEW.origin IN ('ROTATION','TRANSFER') AND NOT EXISTS (
      SELECT 1 FROM role_assignment ra WHERE ra.user_id = NEW.workplace_supervisor_id
        AND ra.role = 'WORKPLACE_SUPERVISOR' AND ra.host_org_id = NEW.host_org_id) THEN
      RAISE EXCEPTION 'SEGMENT_SUPERVISOR_INVALID: supervisor does not belong to the segment organization';
    END IF;
    RETURN NEW;
  END IF;

  IF (NEW.placement_id, NEW.sequence_no, NEW.host_org_id, NEW.unit, NEW.workplace_supervisor_id,
      NEW.start_date, NEW.end_date, NEW.modality, NEW.responsibilities, NEW.expected_hours,
      NEW.origin, NEW.created_by, NEW.created_at)
     IS DISTINCT FROM
     (OLD.placement_id, OLD.sequence_no, OLD.host_org_id, OLD.unit, OLD.workplace_supervisor_id,
      OLD.start_date, OLD.end_date, OLD.modality, OLD.responsibilities, OLD.expected_hours,
      OLD.origin, OLD.created_by, OLD.created_at) THEN
    RAISE EXCEPTION 'IMMUTABLE: segment content cannot change';
  END IF;
  IF NEW.status = OLD.status THEN
    IF ROW(NEW.*) IS DISTINCT FROM ROW(OLD.*) THEN
      RAISE EXCEPTION 'IMMUTABLE: segment lifecycle fields change only with a status transition';
    END IF;
    RETURN NEW;
  END IF;
  IF NOT ((OLD.status = 'PLANNED' AND NEW.status IN ('ACTIVE','CANCELLED')) OR
          (OLD.status = 'ACTIVE' AND NEW.status IN ('COMPLETED','TERMINATED_EARLY','TRANSFERRED'))) THEN
    RAISE EXCEPTION 'SEGMENT_TRANSITION: % -> % is not allowed', OLD.status, NEW.status;
  END IF;
  IF NEW.status = 'ACTIVE' THEN
    IF v_state IS DISTINCT FROM 'ACTIVE' THEN
      RAISE EXCEPTION 'SEGMENT_GATE: placement must be ACTIVE to start a segment';
    END IF;
    IF NEW.workplace_supervisor_id IS NULL OR NOT EXISTS (
      SELECT 1 FROM role_assignment ra WHERE ra.user_id = NEW.workplace_supervisor_id
        AND ra.role = 'WORKPLACE_SUPERVISOR' AND ra.host_org_id = NEW.host_org_id) THEN
      RAISE EXCEPTION 'SEGMENT_GATE: segment requires a workplace supervisor of its organization';
    END IF;
    SELECT count(*) INTO v_unmet FROM placement_segment_condition
      WHERE segment_id = NEW.id AND status <> 'SATISFIED';
    IF v_unmet > 0 THEN
      RAISE EXCEPTION 'SEGMENT_GATE: % enablement condition(s) not satisfied', v_unmet;
    END IF;
    IF NEW.activated_at IS NULL THEN
      RAISE EXCEPTION 'SEGMENT_GATE: activation time is required';
    END IF;
  ELSIF NEW.status IN ('COMPLETED','TERMINATED_EARLY','TRANSFERRED') THEN
    IF NEW.ended_on IS NULL OR NEW.ended_on < NEW.start_date OR NEW.ended_at IS NULL THEN
      RAISE EXCEPTION 'SEGMENT_GATE: a valid end date is required';
    END IF;
    IF NEW.status = 'COMPLETED' AND EXISTS (
         SELECT 1 FROM completion_requirement cr
         WHERE cr.placement_id = NEW.placement_id AND cr.kind = 'FINAL_EVALUATION' AND cr.mandatory)
       AND NOT EXISTS (
         SELECT 1 FROM placement_evaluation ev
         WHERE ev.placement_id = NEW.placement_id AND ev.segment_id = NEW.id AND ev.kind = 'FINAL') THEN
      RAISE EXCEPTION 'SEGMENT_GATE: completing the segment requires its final evaluation';
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER placement_segment_guard BEFORE INSERT OR UPDATE ON placement_segment
  FOR EACH ROW EXECUTE FUNCTION trg_placement_segment_guard();

CREATE FUNCTION trg_placement_segment_history() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' OR NEW.status IS DISTINCT FROM OLD.status THEN
    INSERT INTO placement_segment_status_history(segment_id, from_status, to_status, actor_id)
    VALUES (NEW.id, CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.status END, NEW.status,
            nullif(current_setting('dh05.actor_id', true), '')::int);
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER placement_segment_history AFTER INSERT OR UPDATE OF status ON placement_segment
  FOR EACH ROW EXECUTE FUNCTION trg_placement_segment_history();
CREATE TRIGGER placement_segment_status_history_immutable
  BEFORE UPDATE OR DELETE ON placement_segment_status_history
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

CREATE FUNCTION trg_segment_condition_guard() RETURNS trigger AS $$
DECLARE v_status text;
BEGIN
  SELECT s.status INTO v_status FROM placement_segment s WHERE s.id = NEW.segment_id;
  IF v_status IS DISTINCT FROM 'PLANNED' THEN
    RAISE EXCEPTION 'SEGMENT_GATE: enablement conditions change only while the segment is planned';
  END IF;
  IF TG_OP = 'UPDATE' THEN
    IF (NEW.segment_id, NEW.kind, NEW.source_policy_version_id)
       IS DISTINCT FROM (OLD.segment_id, OLD.kind, OLD.source_policy_version_id)
       OR OLD.status <> 'REQUIRED' OR NEW.status <> 'SATISFIED' OR NEW.confirmed_by IS NULL THEN
      RAISE EXCEPTION 'IMMUTABLE: a condition can only move once from REQUIRED to SATISFIED';
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER placement_segment_condition_guard BEFORE INSERT OR UPDATE ON placement_segment_condition
  FOR EACH ROW EXECUTE FUNCTION trg_segment_condition_guard();

CREATE FUNCTION trg_placement_transfer_guard() RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM placement_segment s WHERE s.id = NEW.from_segment_id
                 AND s.status = 'TRANSFERRED' AND s.ended_on = NEW.effective_date
                 AND s.work_recognition = NEW.prior_work_treatment) THEN
    RAISE EXCEPTION 'TRANSFER_GATE: origin segment must be closed by this transfer';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM placement_segment s WHERE s.id = NEW.to_segment_id
                 AND s.status = 'PLANNED' AND s.origin = 'TRANSFER') THEN
    RAISE EXCEPTION 'TRANSFER_GATE: destination segment must be a planned transfer segment';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER placement_transfer_guard BEFORE INSERT ON placement_transfer
  FOR EACH ROW EXECUTE FUNCTION trg_placement_transfer_guard();
CREATE TRIGGER placement_transfer_immutable BEFORE UPDATE OR DELETE ON placement_transfer
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

CREATE FUNCTION trg_progress_entry_review_guard() RETURNS trigger AS $$
DECLARE
  v_entry record;
  v_state text;
BEGIN
  SELECT * INTO v_entry FROM progress_entry WHERE id = NEW.entry_id;
  SELECT state INTO v_state FROM placement WHERE id = v_entry.placement_id FOR UPDATE;
  IF v_state IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'PLACEMENT_NOT_ACTIVE: hours are reviewed only while the placement is active';
  END IF;
  IF NEW.accepted_hours IS NOT NULL AND NEW.accepted_hours > v_entry.hours THEN
    RAISE EXCEPTION 'HOURS_REVIEW_INVALID: accepted hours exceed reported hours';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER progress_entry_review_guard BEFORE INSERT ON progress_entry_review
  FOR EACH ROW EXECUTE FUNCTION trg_progress_entry_review_guard();
CREATE TRIGGER progress_entry_review_immutable BEFORE UPDATE OR DELETE ON progress_entry_review
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();
CREATE TRIGGER placement_experience_review_immutable BEFORE UPDATE OR DELETE ON placement_experience_review
  FOR EACH ROW EXECUTE FUNCTION trg_placement_record_immutable();

-- Activation creates the single initial segment (no artificial rotation).
CREATE FUNCTION trg_placement_initial_segment() RETURNS trigger AS $$
DECLARE v_actor int;
BEGIN
  IF NEW.state = 'ACTIVE' AND OLD.state IS DISTINCT FROM 'ACTIVE'
     AND NOT EXISTS (SELECT 1 FROM placement_segment WHERE placement_id = NEW.id) THEN
    v_actor := nullif(current_setting('dh05.actor_id', true), '')::int;
    INSERT INTO placement_segment(placement_id, sequence_no, host_org_id, unit, workplace_supervisor_id,
      start_date, end_date, modality, responsibilities, origin, status, activated_at, activated_by, created_by)
    SELECT p.id, 1, o.host_org_id, NULL, pv.workplace_supervisor_id, pv.start_date, pv.end_date, NULL,
           pv.responsibilities, 'PLACEMENT_ACTIVATION', 'ACTIVE', clock_timestamp(), v_actor, v_actor
    FROM placement p
    JOIN application a ON a.id = p.application_id
    JOIN opportunity o ON o.id = a.opportunity_id
    JOIN placement_version pv ON pv.id = p.current_version_id
    WHERE p.id = NEW.id;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER placement_initial_segment AFTER UPDATE OF state ON placement
  FOR EACH ROW EXECUTE FUNCTION trg_placement_initial_segment();

-- Completion gate: accepted (not reported) hours, closed segments, decided
-- work, per-segment final evaluations and combined-experience review.
CREATE OR REPLACE FUNCTION trg_placement_gate() RETURNS trigger AS $$
DECLARE n int;
BEGIN
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    PERFORM 1 FROM placement WHERE id = NEW.id FOR UPDATE;
    IF NEW.state = 'ACTIVE' THEN
      IF OLD.state <> 'DOCUMENTATION_PENDING' THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> ACTIVE', OLD.state; END IF;
      IF NOT NEW.activation_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: activation requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
    ELSIF NEW.state IN ('COMPLETED','CLOSED') THEN
      IF (NEW.state = 'COMPLETED' AND OLD.state <> 'ACTIVE') OR
         (NEW.state = 'CLOSED' AND OLD.state <> 'COMPLETED') THEN
        RAISE EXCEPTION 'GATE: illegal transition % -> %', OLD.state, NEW.state;
      END IF;
      SELECT count(*) INTO n FROM checklist_item
        WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
      IF NOT NEW.completion_requirements_instantiated THEN
        RAISE EXCEPTION 'GATE: completion requirements not instantiated'; END IF;
      SELECT count(*) INTO n FROM placement_segment
        WHERE placement_id = NEW.id AND status IN ('PLANNED','ACTIVE');
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % segment(s) still planned or active', n; END IF;
      IF placement_pending_hour_entries(NEW.id) > 0 THEN
        RAISE EXCEPTION 'GATE: reported hours are pending review'; END IF;
      SELECT count(*) INTO n
        FROM completion_requirement cr
       WHERE cr.placement_id = NEW.id AND cr.mandatory AND (
         (cr.kind = 'MIN_HOURS' AND
           (cr.threshold IS NULL OR placement_accepted_hours(NEW.id) < cr.threshold)) OR
         (cr.kind = 'FINAL_REPORT' AND NOT EXISTS (
           SELECT 1 FROM completion_evidence ce WHERE ce.placement_id = NEW.id AND ce.kind = cr.kind)) OR
         (cr.kind = 'FINAL_EVALUATION' AND (NOT EXISTS (
           SELECT 1 FROM placement_evaluation ev WHERE ev.placement_id = NEW.id AND ev.kind = 'FINAL')
           OR EXISTS (
           SELECT 1 FROM placement_segment s WHERE s.placement_id = NEW.id AND s.status = 'COMPLETED'
             AND s.origin <> 'MIGRATED_SINGLE'
             AND NOT EXISTS (SELECT 1 FROM placement_evaluation ev
                             WHERE ev.segment_id = s.id AND ev.kind = 'FINAL')))) OR
         (cr.kind NOT IN ('MIN_HOURS','FINAL_REPORT','FINAL_EVALUATION') AND NOT cr.satisfied)
       );
      IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
      IF (SELECT count(*) FROM placement_segment WHERE placement_id = NEW.id AND status <> 'CANCELLED') > 1
         AND NOT EXISTS (
           SELECT 1 FROM (SELECT decision, reviewed_at FROM placement_experience_review
                          WHERE placement_id = NEW.id ORDER BY id DESC LIMIT 1) r
           WHERE r.decision = 'APPROVED' AND r.reviewed_at >= coalesce(
             (SELECT max(ended_at) FROM placement_segment WHERE placement_id = NEW.id), '-infinity')) THEN
        RAISE EXCEPTION 'GATE: combined experience requires an approved academic review';
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

GRANT SELECT, INSERT, UPDATE ON placement_segment, placement_segment_condition TO app_user;
GRANT SELECT, INSERT ON placement_segment_status_history, placement_transfer,
  progress_entry_review, placement_experience_review TO app_user;
GRANT USAGE ON SEQUENCE placement_segment_id_seq, placement_segment_condition_id_seq,
  placement_segment_status_history_id_seq, placement_transfer_id_seq,
  progress_entry_review_id_seq, placement_experience_review_id_seq TO app_user;
"""

CURRENT_SCHEMA = (SCHEMA + UPGRADE_0002_SQL + UPGRADE_0003_SQL + UPGRADE_0004_SQL
                  + UPGRADE_0005_SQL + UPGRADE_0006_SQL + UPGRADE_0007_SQL
                  + UPGRADE_0008_SQL + UPGRADE_0009_SQL + UPGRADE_0010_SQL + UPGRADE_0011_SQL
                  + UPGRADE_0012_SQL + UPGRADE_0013_SQL + UPGRADE_0014_SQL + UPGRADE_0015_SQL
                  + UPGRADE_0016_SQL)
