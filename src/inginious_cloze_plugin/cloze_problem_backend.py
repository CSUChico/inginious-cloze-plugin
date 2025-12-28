from inginious.common.tasks_problems import Problem

class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"        # <-- must match

    def parse_problem(self, problem_content):
        self._raw = problem_content.get("text", "")
        return problem_content

    def input_type(self):
        return dict

    def input_is_consistent(self, task_input, *_):
        return True

    def check_answer(self, task_input, language):
        return True, None, None, 0
