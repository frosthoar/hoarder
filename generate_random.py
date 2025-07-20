import faker
import pathlib
import string
import os

import faker_file
import faker.providers.python
import faker.providers.file

fk = faker.Faker()
fk.add_provider(faker.providers.python.BaseProvider)
fk.add_provider(faker.providers.file.BaseProvider)

parens = ["[]", "()"]


def weird_string(l: int) -> str:
    p: str = "".join(
        fk.random_choices(
            string.ascii_uppercase + string.ascii_lowercase + string.digits + "_!. ",
            length=l,
        )
    )
    return p


def generate_random_tree(max_items: int, root: str | pathlib.Path, max_depth: int = 5):
    root = pathlib.Path(root)
    for _ in range(max_items):
        if fk.pybool():
            first = fk.random_element(parens)
            first = first[0] + weird_string(8) + first[1]
            second = fk.random_element(parens)
            second = second[0] + weird_string(8) + second[1]

            dirname = first + fk.file_name(extension="") + second
            os.mkdir(root / dirname)
            generate_random_tree(max_items - 1, root / dirname, max_depth - 1)
        else:
            suffix = fk.random_element(["bin", "dat", "raw"])
            fname = fk.file_name(extension=suffix)
            blob = fk.binary(length=fk.pyint(1000,2000))
            with open(root / fname, "wb") as f:
                f.write(blob)


start = pathlib.Path(os.getcwd()) / "files"
os.mkdir(start)
generate_random_tree(5, start, 3)
