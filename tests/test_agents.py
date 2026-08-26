"""Agent construction tests."""

import unittest

from agents.case_study_agent import create_case_study_agent
from agents.final_editor import create_final_editor
from agents.requirement_analyzer import create_requirement_analyzer
from agents.reviewer import create_reviewer_agent
from agents.writer import create_writer_agent


class AgentConstructionTests(unittest.TestCase):
    def test_agents_use_supported_task_mode(self) -> None:
        agents = [
            create_requirement_analyzer(),
            create_case_study_agent(),
            create_writer_agent(),
            create_reviewer_agent(),
            create_final_editor(),
        ]

        self.assertTrue(all(agent.mode == "task" for agent in agents))


if __name__ == "__main__":
    unittest.main()
