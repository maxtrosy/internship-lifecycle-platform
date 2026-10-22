-- DH-05 PoC schema (SYNTHETIC DATA ONLY). Minimal slice to challenge ADR-003/004/005.
-- This is NOT the full domain model; see docs/evaluation-2/views/domain-model.md

CREATE ROLE app_user NOLOGIN;

CREATE TABLE academic_program (
  id serial PRIMARY KEY, code text UNIQUE NOT NULL, name text NOT NULL);

CREATE TABLE host_org (id serial PRIMARY KEY, name text NOT NULL);

CREATE TABLE user_account (
  id serial PRIMARY KEY,
  display_name text NOT NULL,
  role text NOT NULL CHECK (role IN ('STUDENT','HOST_ORG_MEMBER','WORKPLACE_SUPERVISOR',
        'FACULTY_SUPERVISOR','PROGRAM_COORDINATOR','EXPERIENTIAL_COORDINATOR','LEGAL_REVIEWER')),
  program_id int REFERENCES academic_program(id),
  host_org_id int REFERENCES host_org(id),
  -- synthetic academic profile (simulated Student Records); sensitive: never exposed to external roles
  credits int, academic_level int, completed_courses text[] DEFAULT '{}');

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

-- Requirement INSTANCES materialised from a policy version (ADR-001/ADR-003)
CREATE TABLE checklist_item (   -- activation requirements: documents or conditions
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL, mandatory boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'REQUIRED' CHECK (status IN ('REQUIRED','SUBMITTED','APPROVED','REJECTED')),
  UNIQUE (placement_id, kind));

CREATE TABLE completion_requirement (  -- closure evidence
  id serial PRIMARY KEY, placement_id int NOT NULL REFERENCES placement(id),
  kind text NOT NULL, mandatory boolean NOT NULL DEFAULT true,
  satisfied boolean NOT NULL DEFAULT false, threshold numeric,
  UNIQUE (placement_id, kind));

-- BR-18 / OPEN-14 (proposal): DERIVED indicator, never stored.
-- True only for an ACTIVE placement with a mandatory activation item not APPROVED.
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

-- ===== DB-level safety nets (ADR-003 / ADR-005) =====
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
      -- BR-18: a noncompliant activation also blocks completion (and therefore closure)
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
      -- BR-18: closure also requires a compliant activation
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

-- Application role: no DELETE anywhere; audit_event is insert/select only
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
REVOKE UPDATE ON audit_event FROM app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
