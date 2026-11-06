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

CURRENT_SCHEMA = (SCHEMA + UPGRADE_0002_SQL + UPGRADE_0003_SQL + UPGRADE_0004_SQL
                  + UPGRADE_0005_SQL + UPGRADE_0006_SQL + UPGRADE_0007_SQL
                  + UPGRADE_0008_SQL + UPGRADE_0009_SQL + UPGRADE_0010_SQL + UPGRADE_0011_SQL
                  + UPGRADE_0012_SQL + UPGRADE_0013_SQL + UPGRADE_0014_SQL)
