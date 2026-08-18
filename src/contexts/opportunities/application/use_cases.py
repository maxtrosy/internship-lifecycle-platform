from uuid import UUID

from sqlalchemy.orm import Session

from src.contexts.opportunities.domain.models import HostOrganization, InternshipOpportunity
from src.shared.events import DomainEventName, EventEnvelope, InProcessEventBus


class PublishOpportunity:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def execute(self, opportunity_id: UUID) -> InternshipOpportunity:
        opportunity = self.session.get(InternshipOpportunity, opportunity_id)
        if opportunity is None:
            raise LookupError("Opportunity not found.")

        host_org = self.session.get(HostOrganization, opportunity.host_org_id)
        if host_org is None:
            raise LookupError("Host organization not found.")

        opportunity.publish(host_org)
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.OPPORTUNITY_PUBLISHED,
                aggregate_type="InternshipOpportunity",
                aggregate_id=opportunity.id,
                payload={"host_org_id": str(opportunity.host_org_id)},
            )
        )
        return opportunity
