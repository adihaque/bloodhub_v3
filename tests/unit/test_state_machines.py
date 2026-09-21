import unittest
from bloodhub.domain.state_machines import RequestStateMachine, DonorStateMachine, StateTransitionError

class TestStateMachines(unittest.TestCase):
    def test_valid_request_lifecycle(self):
        RequestStateMachine.validate_transition("ACTIVE", "MATCHING")
        RequestStateMachine.validate_transition("MATCHING", "AWAITING_DONOR")
        RequestStateMachine.validate_transition("AWAITING_DONOR", "ASSIGNED")
        RequestStateMachine.validate_transition("ASSIGNED", "CONFIRMED")
        RequestStateMachine.validate_transition("CONFIRMED", "COMPLETED")

    def test_invalid_request_transition(self):
        # Cannot jump from DRAFT straight to COMPLETED
        with self.assertRaises(StateTransitionError):
            RequestStateMachine.validate_transition("DRAFT", "COMPLETED")

        # Cannot modify a CANCELLED or COMPLETED request
        with self.assertRaises(StateTransitionError):
            RequestStateMachine.validate_transition("COMPLETED", "MATCHING")
        with self.assertRaises(StateTransitionError):
            RequestStateMachine.validate_transition("CANCELLED", "ASSIGNED")

    def test_donor_transitions(self):
        DonorStateMachine.validate_transition("AVAILABLE", "OFFERED")
        DonorStateMachine.validate_transition("OFFERED", "ASSIGNED")
        DonorStateMachine.validate_transition("ASSIGNED", "AVAILABLE")

if __name__ == '__main__':
    unittest.main()
