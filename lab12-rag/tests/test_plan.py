import copy
import unittest

from scripts.check_plan import EXPECTED_JOBS, check_plan


class DeploymentPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"plan_version": 2, "plan": {
            key: {"action": "update", "remote_state": {"job_id": job_id}}
            for key, job_id in EXPECTED_JOBS.items()
        }}

    def test_existing_job_updates_are_accepted(self):
        self.assertEqual(len(check_plan(self.plan)), 2)

    def test_unchanged_existing_jobs_are_accepted(self):
        for resource in self.plan["plan"].values():
            resource["action"] = "skip"
        self.assertEqual(len(check_plan(self.plan)), 2)

    def test_creation_deletion_and_replacement_are_rejected(self):
        for action in ("create", "delete", "replace"):
            with self.subTest(action=action):
                plan = copy.deepcopy(self.plan)
                plan["plan"]["resources.jobs.rag_qa"]["action"] = action
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_different_job_identity_is_rejected(self):
        self.plan["plan"]["resources.jobs.rag_smoke"]["remote_state"]["job_id"] = 123
        with self.assertRaises(ValueError):
            check_plan(self.plan)

    def test_missing_or_additional_resources_are_rejected(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                plan = copy.deepcopy(self.plan)
                if extra:
                    plan["plan"]["resources.schemas.other"] = {"action": "create"}
                else:
                    del plan["plan"]["resources.jobs.rag_qa"]
                with self.assertRaises(ValueError):
                    check_plan(plan)


if __name__ == "__main__":
    unittest.main()
