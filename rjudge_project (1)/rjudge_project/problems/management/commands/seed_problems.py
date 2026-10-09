from django.core.management.base import BaseCommand

from problems.models import Problem, TestCase

# (title, difficulty, statement, input format, output format, sample in, sample out, [(input, output, hidden)])
PROBLEMS = [
    ("Sum of Two Integers", "Easy", "Read two integers and print their sum.",
     "One line with two integers a and b.", "One integer: a + b.", "5 7", "12",
     [("5 7", "12", False), ("-3 3", "0", False), ("0 0", "0", True), ("-5 -7", "-12", True),
      ("1000000 2000000", "3000000", True)]),
    ("Even or Odd", "Easy", "Read an integer and print Even if it is even, otherwise print Odd.",
     "One integer n.", "The word Even or Odd.", "7", "Odd",
     [("7", "Odd", False), ("10", "Even", False), ("0", "Even", True), ("-3", "Odd", True), ("-8", "Even", True)]),
    ("Largest of Three", "Easy", "Read three integers and print the largest one.",
     "One line with three integers.", "One integer.", "4 9 2", "9",
     [("4 9 2", "9", False), ("5 5 5", "5", True), ("-1 -5 -3", "-1", True), ("100 20 300", "300", True)]),
    ("Factorial", "Medium", "Read n (0 <= n <= 12) and print n!.",
     "One integer n.", "One integer: n!", "5", "120",
     [("5", "120", False), ("0", "1", True), ("1", "1", True), ("10", "3628800", True), ("12", "479001600", True)]),
]


class Command(BaseCommand):
    help = "Adds a few example problems with test cases (skips ones that already exist)."

    def handle(self, *args, **options):
        for title, diff, statement, fin, fout, sin, sout, cases in PROBLEMS:
            problem, created = Problem.objects.get_or_create(title=title, defaults=dict(
                difficulty=diff, statement=statement, input_format=fin, output_format=fout,
                sample_input=sin, sample_output=sout, is_published=True))
            if created:
                for order, (inp, out, hidden) in enumerate(cases, start=1):
                    TestCase.objects.create(problem=problem, input_data=inp, expected_output=out,
                                            is_hidden=hidden, order=order)
                self.stdout.write(f"Added: {title}")
            else:
                self.stdout.write(f"Already exists: {title}")
