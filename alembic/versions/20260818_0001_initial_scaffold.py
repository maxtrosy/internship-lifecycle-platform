"""initial modular monolith scaffold

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260818_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = postgresql.ENUM("Student", "HostOrgRep", "WorkplaceSupervisor", "FacultySupervisor", "ProgramCoordinator", "ExperientialCoordinator", "LegalRep", "ITAdmin", name="role", create_type=False)
    role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sso_subject", sa.String(length=255), nullable=False),
        sa.Column("roles", postgresql.ARRAY(role), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("sso_subject", name=op.f("uq_users_sso_subject")),
    )

    _create_enum("verification_status", ["Pending", "Approved", "Rejected"])
    _create_enum("modality", ["remote", "hybrid", "onsite"])
    _create_enum("compensation_type", ["paid", "unpaid", "stipend"])
    _create_enum("opportunity_status", ["Draft", "UnderReview", "Published", "Closed", "Cancelled"])
    _create_enum("application_status", ["Draft", "Submitted", "EligibilityValidated", "EligibilityRejected", "ForwardedToEmployer", "EmployerAccepted", "EmployerRejected", "Withdrawn"])
    _create_enum("document_requirement_type", ["agreement", "insurance", "confidentiality", "other"])
    _create_enum("document_review_status", ["Pending", "Submitted", "UnderLegalReview", "Approved", "Rejected"])
    _create_enum("placement_status", ["Proposed", "UnderAcademicReview", "DocumentationPending", "ReadyToActivate", "Active", "Suspended", "Interrupted", "PendingFinalEvaluation", "PendingFinalEvidence", "Rejected", "Withdrawn", "ClosedIncomplete", "Closed"])
    _create_enum("placement_change_type", ["SupervisorChange", "ScheduleChange", "LocationChange", "ResponsibilityChange", "Incident"])
    _create_enum("resolution_status", ["Open", "Resolved", "ClosedIncomplete"])
    _create_enum("evaluation_type", ["Midterm", "Final"])
    _create_enum("hours_approval_status", ["Pending", "Approved", "Rejected"])
    _create_enum("deadline_status", ["Pending", "Met", "Missed"])
    _create_enum("risk_type", ["DelayedActivation", "OverdueEvaluation", "MissingHours"])

    domain_event_name = postgresql.ENUM(
        "OpportunityPublished", "OpportunityClosed", "ApplicationSubmitted", "EligibilityValidated",
        "EligibilityRejected", "ApplicationForwardedToEmployer", "EmployerAccepted", "EmployerRejected",
        "DocumentSubmitted", "DocumentApproved", "DocumentRejected", "PlacementProposed",
        "AcademicReviewStarted", "PlacementApproved", "PlacementRejected", "PlacementActivated",
        "PlacementSuspended", "PlacementResumed", "PlacementInterrupted", "PlacementClosed",
        "PlacementClosedIncomplete", "PlacementWithdrawn", "SupervisorChanged", "ScheduleChanged",
        "LocationChanged", "IncidentReported", "WorkPlanApproved", "ProgressReportSubmitted",
        "HoursLogged", "MidtermEvaluationSubmitted", "FinalEvaluationSubmitted",
        "FinalEvidenceSubmitted", "DeadlineMissed", "RiskFlagRaised", name="domain_event_name", create_type=False
    )
    domain_event_name.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "host_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization_type", sa.String(length=120), nullable=False),
        sa.Column("institutional_verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_host_organizations")),
    )
    op.create_table(
        "internship_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("modality", postgresql.ENUM(name="modality", create_type=False), nullable=False),
        sa.Column("compensation_type", postgresql.ENUM(name="compensation_type", create_type=False), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("eligible_programs", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("status", postgresql.ENUM(name="opportunity_status", create_type=False), nullable=False),
        sa.ForeignKeyConstraint(["host_org_id"], ["host_organizations.id"], name=op.f("fk_internship_opportunities_host_org_id_host_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_internship_opportunities")),
    )
    op.create_table(
        "placements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workplace_supervisor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_supervisor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_coordinator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="placement_status", create_type=False), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_placements")),
    )
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", postgresql.ENUM(name="application_status", create_type=False), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["internship_opportunities.id"], name=op.f("fk_applications_opportunity_id_internship_opportunities")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index(
        "uq_applications_active_student_opportunity",
        "applications",
        ["student_id", "opportunity_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('EligibilityRejected', 'Withdrawn', 'EmployerRejected')"),
    )
    op.create_table("eligibility_checks", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("evaluated_criteria", sa.JSON(), nullable=False), sa.Column("result", sa.Boolean(), nullable=False), sa.Column("evaluator_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_eligibility_checks_application_id_applications")), sa.PrimaryKeyConstraint("id", name=op.f("pk_eligibility_checks")))
    op.create_table("document_checklists", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.ForeignKeyConstraint(["placement_id"], ["placements.id"], name=op.f("fk_document_checklists_placement_id_placements")), sa.PrimaryKeyConstraint("id", name=op.f("pk_document_checklists")), sa.UniqueConstraint("placement_id", name=op.f("uq_document_checklists_placement_id")))
    op.create_table("document_requirements", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("requirement_type", postgresql.ENUM(name="document_requirement_type", create_type=False), nullable=False), sa.Column("required", sa.Boolean(), nullable=False), sa.ForeignKeyConstraint(["checklist_id"], ["document_checklists.id"], name=op.f("fk_document_requirements_checklist_id_document_checklists")), sa.PrimaryKeyConstraint("id", name=op.f("pk_document_requirements")))
    op.create_table("document_statuses", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", postgresql.ENUM(name="document_review_status", create_type=False), nullable=False), sa.Column("notes", sa.String(length=500), nullable=True), sa.ForeignKeyConstraint(["checklist_id"], ["document_checklists.id"], name=op.f("fk_document_statuses_checklist_id_document_checklists")), sa.ForeignKeyConstraint(["requirement_id"], ["document_requirements.id"], name=op.f("fk_document_statuses_requirement_id_document_requirements")), sa.PrimaryKeyConstraint("id", name=op.f("pk_document_statuses")))
    op.create_table("placement_changes", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("change_type", postgresql.ENUM(name="placement_change_type", create_type=False), nullable=False), sa.Column("description", sa.String(length=2000), nullable=False), sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("resolution_status", postgresql.ENUM(name="resolution_status", create_type=False), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_placement_changes")))
    op.create_table("work_plans", sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("objectives", sa.String(length=2000), nullable=False), sa.Column("responsibilities", sa.String(length=2000), nullable=False), sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("placement_id", name=op.f("pk_work_plans")))
    op.create_table("progress_reports", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("period", sa.String(length=120), nullable=False), sa.Column("hours", sa.Float(), nullable=False), sa.Column("evidence", sa.String(length=1000), nullable=False), sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True), sa.PrimaryKeyConstraint("id", name=op.f("pk_progress_reports")))
    op.create_table("evaluations", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("evaluation_type", postgresql.ENUM(name="evaluation_type", create_type=False), nullable=False), sa.Column("evaluator_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("rubric", sa.JSON(), nullable=False), sa.Column("comments", sa.String(length=2000), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluations")))
    op.create_table("hours_logs", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("log_date", sa.Date(), nullable=False), sa.Column("hours", sa.Float(), nullable=False), sa.Column("description", sa.String(length=1000), nullable=False), sa.Column("approval_status", postgresql.ENUM(name="hours_approval_status", create_type=False), nullable=False), sa.Column("academic_program_requires_hours", sa.Boolean(), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_hours_logs")))
    op.create_table("deadlines", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("related_entity", sa.String(length=120), nullable=False), sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("deadline_type", sa.String(length=120), nullable=False), sa.Column("status", postgresql.ENUM(name="deadline_status", create_type=False), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_deadlines")))
    op.create_table("risk_flags", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("risk_type", postgresql.ENUM(name="risk_type", create_type=False), nullable=False), sa.Column("flagged_at", sa.Date(), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_flags")))
    op.create_table("domain_events", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("name", domain_event_name, nullable=False), sa.Column("aggregate_type", sa.String(length=120), nullable=False), sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_domain_events")))
    op.create_table("reporting_projections", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("projection_name", sa.String(length=120), nullable=False), sa.Column("source_event_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("data", sa.JSON(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id", name=op.f("pk_reporting_projections")))


def downgrade() -> None:
    for table in [
        "reporting_projections", "domain_events", "risk_flags", "deadlines", "hours_logs", "evaluations",
        "progress_reports", "work_plans", "placement_changes", "document_statuses", "document_requirements",
        "document_checklists", "eligibility_checks", "applications", "placements", "internship_opportunities",
        "host_organizations", "users",
    ]:
        op.drop_table(table)
    for enum_name in [
        "domain_event_name", "risk_type", "deadline_status", "hours_approval_status", "evaluation_type",
        "resolution_status", "placement_change_type", "placement_status", "document_review_status",
        "document_requirement_type", "application_status", "opportunity_status", "compensation_type",
        "modality", "verification_status", "role",
    ]:
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)


def _create_enum(name: str, values: Sequence[str]) -> None:
    postgresql.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)
