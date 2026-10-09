from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand

from problems import judge

CASES = [SimpleNamespace(input_data="2 3", expected_output="5", is_hidden=False)]
C_SUM = '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d\\n",a+b);return 0;}\n'
PY_SUM = "a, b = map(int, input().split())\nprint(a + b)\n"
CHECKS = [  # (name, language, code, expected verdict)
    ("C correct program", "c", C_SUM, "AC"),
    ("Python correct program", "python", PY_SUM, "AC"),
    ("Wrong answer", "python", "print(0)\n", "WA"),
    ("C compile error", "c", "int main( {\n", "CE"),
    ("Runtime error", "python", "print(1/0)\n", "RE"),
    ("Infinite loop", "python", "while True:\n    pass\n", "TLE"),
]


class Command(BaseCommand):
    help = "Runs six tiny programs through the configured judge and checks the verdicts."

    def handle(self, *args, **options):
        self.stdout.write(f"Judge backend: {settings.JUDGE_BACKEND}")
        failures = 0
        for name, language, code, expected in CHECKS:
            result = judge.evaluate(code, language, CASES, 1)
            ok = result["verdict"] == expected
            failures += not ok
            line = f"{'OK  ' if ok else 'FAIL'} {name}: expected {expected}, got {result['verdict']}"
            if not ok and result["message"]:
                line += f"  ({result['message'][:150]})"
            self.stdout.write(line)
        self.stdout.write("All checks passed." if not failures else f"{failures} check(s) failed.")
