"""Example demonstrating pprint with PasswordStore.

This example shows how to pretty-print a PasswordStore with a single call -
PasswordStore's own to_presentation() already requests that its repeated
"title" column be merged, so no formatter configuration is needed.
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

hoarder.utils.pprint(p)
