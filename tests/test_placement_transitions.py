import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from src.contexts.placements.api.router import TransitionPlacementRequest, transition_placement


class _FailingTransitionPlacement:
    def __init__(self, session: object) -> None:
        self.session = session

    def mark_ready_to_activate(self, placement_id: uuid.UUID, employer_selection_confirmed: bool) -> None:
        raise ValueError("Placement no puede entrar a ReadyToActivate con documentos obligatorios sin Approved.")


class PlacementTransitionTests(unittest.TestCase):
    def test_ready_to_activate_without_complete_documents_returns_409(self) -> None:
        with patch("src.contexts.placements.api.router.TransitionPlacement", _FailingTransitionPlacement):
            with self.assertRaises(HTTPException) as raised:
                transition_placement(
                    placement_id=uuid.uuid4(),
                    request=TransitionPlacementRequest(
                        transition="mark_ready_to_activate",
                        employer_selection_confirmed=True,
                    ),
                    session=object(),
                )

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
