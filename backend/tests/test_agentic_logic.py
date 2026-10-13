import unittest
from types import SimpleNamespace
from unittest.mock import patch

from triage import logic
from triage.agent import fallback_question_answer, fallback_turn_analysis
from triage.stages import TriageStage


def base_state():
    return {
        "stage": TriageStage.GREETING.value,
        "messages": [],
        "patient_data": {
            "name": None,
            "age": None,
            "gender": None,
            "phone": None,
            "is_existing": False,
        },
        "symptom_data": {
            "symptom": None,
            "body_part": None,
            "duration": None,
            "severity": None,
            "red_flags": [],
        },
        "patient_id": None,
        "department": None,
        "icd_code": None,
        "ai_impression": None,
        "doctor_options": [],
        "selected_doctor_id": None,
        "hospital_id": 1,
        "kiosk_id": 1,
    }


class AgenticTriageLogicTests(unittest.TestCase):
    def test_local_fallback_extracts_symptoms_without_treating_severity_as_doctor_choice(self):
        analysis = fallback_turn_analysis(
            "I have had a mild headache for two days. The pain is 5 out of 10.", base_state()
        )

        self.assertEqual(analysis["symptom_updates"]["symptom"], "headache")
        self.assertEqual(analysis["symptom_updates"]["body_part"], "head")
        self.assertEqual(analysis["symptom_updates"]["duration"], "for two days")
        self.assertEqual(analysis["symptom_updates"]["severity"], 5)
        self.assertIsNone(analysis["doctor_selection_number"])

    def test_local_fallback_allows_numbered_doctor_choice_after_options_are_shown(self):
        state = base_state()
        state["doctor_options"] = [{"id": 1, "name": "Asha Rao"}, {"id": 2, "name": "Vikram Shah"}]

        analysis = fallback_turn_analysis("Please choose doctor 2", state)

        self.assertEqual(analysis["doctor_selection_number"], 2)

    def test_local_fallback_answers_common_department_questions(self):
        self.assertIn("General Medicine", fallback_question_answer("What does General Medicine cover?"))

    def test_question_is_answered_without_losing_triage_flow(self):
        state = base_state()
        analysis = {
            "patient_updates": {"name": None, "age": None, "gender": None, "phone": None},
            "symptom_updates": {"symptom": None, "body_part": None, "duration": None, "severity": None},
            "doctor_selection_number": None,
            "doctor_selection_name": None,
            "wants_doctor_change": False,
            "wants_finalize": False,
            "question": "What is cardiology?",
            "question_type": "medical",
            "needs_urgent_attention": False,
        }

        with patch.object(logic, "understand_turn", return_value=analysis), patch.object(
            logic, "answer_question", return_value="Cardiology focuses on heart-related care."
        ):
            result = logic.process_turn(None, state, "What is cardiology?")

        self.assertIn("Cardiology focuses on heart-related care.", result.reply)
        self.assertIn("what is bothering you", result.reply.lower())
        self.assertEqual(state["stage"], TriageStage.COLLECTING_SYMPTOMS.value)

    def test_patient_can_change_selected_doctor_by_voice(self):
        state = base_state()
        state.update(
            {
                "stage": TriageStage.READY_TO_FINALIZE.value,
                "patient_id": 10,
                "symptom_data": {
                    "symptom": "knee pain",
                    "body_part": "left knee",
                    "duration": "two days",
                    "severity": 6,
                    "red_flags": [],
                },
                "doctor_options": [{"id": 21, "name": "Asha Rao"}, {"id": 22, "name": "Vikram Shah"}],
                "selected_doctor_id": 21,
            }
        )
        analysis = {
            "patient_updates": {"name": None, "age": None, "gender": None, "phone": None},
            "symptom_updates": {"symptom": None, "body_part": None, "duration": None, "severity": None},
            "doctor_selection_number": 2,
            "doctor_selection_name": None,
            "wants_doctor_change": True,
            "wants_finalize": False,
            "question": None,
            "question_type": None,
            "needs_urgent_attention": False,
        }

        with patch.object(logic, "understand_turn", return_value=analysis):
            result = logic.process_turn(None, state, "Actually change to the second doctor")

        self.assertEqual(state["selected_doctor_id"], 22)
        self.assertEqual(state["stage"], TriageStage.READY_TO_FINALIZE.value)
        self.assertIn("Dr. Vikram Shah", result.reply)

    def test_existing_patient_can_correct_phone_number(self):
        state = base_state()
        state.update(
            {
                "stage": TriageStage.READY_TO_FINALIZE.value,
                "patient_id": 10,
                "patient_data": {
                    "name": "Aman Khan",
                    "age": 34,
                    "gender": "male",
                    "phone": "1111111111",
                    "is_existing": True,
                },
                "symptom_data": {
                    "symptom": "fever",
                    "body_part": "body",
                    "duration": "one day",
                    "severity": 4,
                    "red_flags": [],
                },
                "doctor_options": [{"id": 31, "name": "Meera Iyer"}],
                "selected_doctor_id": 31,
            }
        )
        analysis = {
            "patient_updates": {"name": None, "age": None, "gender": None, "phone": "99999 88888"},
            "symptom_updates": {"symptom": None, "body_part": None, "duration": None, "severity": None},
            "doctor_selection_number": None,
            "doctor_selection_name": None,
            "wants_doctor_change": False,
            "wants_finalize": False,
            "question": None,
            "question_type": None,
            "needs_urgent_attention": False,
        }
        updated_patient = SimpleNamespace(
            id=10,
            name="Aman Khan",
            age=34,
            gender="male",
            phone="9999988888",
        )

        with patch.object(logic, "understand_turn", return_value=analysis), patch.object(
            logic, "get_patient_by_phone", return_value=None
        ), patch.object(logic, "update_patient_details", return_value=updated_patient) as update_patient:
            result = logic.process_turn(None, state, "Actually my number is 99999 88888")

        update_patient.assert_called_once()
        self.assertEqual(state["patient_id"], 10)
        self.assertEqual(state["patient_data"]["phone"], "9999988888")
        self.assertIn("Confirm", result.reply)


if __name__ == "__main__":
    unittest.main()
