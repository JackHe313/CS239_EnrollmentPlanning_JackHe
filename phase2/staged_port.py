"""Run the course port driver with one extra check on model-generated inventories."""
INVENTORY_GUIDANCE = """
The native coverage worker identifies a Python callable by its resolved source file
and qualified function name. Return exactly one boundary ID per distinct callable
you inventory. For a shared dispatcher or agent loop, describe all applicable
roles, operations, effects and observations in that one entry. The binding stage
can assign distinct actions and producers to the same boundary. Preserve every
applicable policy obligation and describe any missing observation as a gap.
"""


def require_unique_functions(inventory, original):
    seen = {}
    for boundary in inventory['boundaries']:
        location = ((original / boundary['file']).resolve(), boundary['symbol'])
        if location in seen:
            raise ValueError(
                f"Boundaries {seen[location]!r} and {boundary['id']!r} both identify "
                f"{boundary['file']}::{boundary['symbol']}. Return one ID for this "
                "callable and describe all its distinct operations in the combined entry."
            )
        seen[location] = boundary['id']


def main():
    from policyweave.policy_adder import student
    from policyweave.policy_adder.codex import CodexPort

    class EnrollmentPort(CodexPort):
        def plan(self, stage, prompt, name, **options):
            if stage == 'inventory':
                prompt += '\n' + INVENTORY_GUIDANCE
            draft = super().plan(stage, prompt, name, **options)
            if stage == 'inventory':
                require_unique_functions(draft, self.output / 'original')
            return draft

    # The pinned CLI obtains its port class from this module. Its standard
    # command still owns all stage transitions, native checks and publication.
    standard_port = student.CodexPort
    try:
        student.CodexPort = EnrollmentPort
        return student.port_main()
    finally:
        student.CodexPort = standard_port


if __name__ == '__main__':
    main()
