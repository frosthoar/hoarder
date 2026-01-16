"""Example demonstrating TableFormatter with PasswordStore.

This example shows how to use TableFormatter to display a PasswordStore
with and without cell merging in the first column.
"""

import hoarder.passwords
import hoarder.utils

p = hoarder.passwords.PasswordStore()
p.add_password("foo", "password")
p.add_password("foo", "secret")
p.add_password("foo", "dragon")
p.add_password("bar", "guessme")
p.add_password("bar", "vampire")
p.add_password("bar", "udontkow")

a = hoarder.utils.TableFormatter()
b = hoarder.utils.TableFormatter(merge_first_column=True)
print(a.format_presentable(p))
print(b.format_presentable(p))
