import faker
import pathlib
import random
import string
import os

import faker.providers.python
import faker.providers.file


fk = faker.Faker()
fk.add_provider(faker.providers.python.BaseProvider)
fk.add_provider(faker.providers.file.BaseProvider)

parens = ["[]", "()"]

def weird_string(l):
    p = "".join([fk.random_choices(string.ascii_uppercase + string.ascii_lowercase + string.digits + "_!. ") for _ in range(l)])
    print(p)
    return p

def generate_random_tree(max_items: int, root: str | pathlib.Path, max_depth=5):
    root = pathlib.Path(root)
    for _ in range(max_items):
        if fk.pybool():
            first = fk.random_choices(parens)
            first = first[0] + weird_string(8) + first[1]
            second = fk.random_choices(parens)
            second = second[0] + weird_string(8) + second[1]

            dirname = first + fk.file_name(category="image", extension="") + fk.file_name(category="image", extension="") + second
            #os.mkdir(root / dirname)
            print(str(root / dirname))
            generate_random_tree(max_items-1, root / dirname, max_depth-1)
        else:
            dirname = fk.file_name(category="image")
            print(str(root / dirname))

generate_random_tree(6, os.getcwd(), 4)
