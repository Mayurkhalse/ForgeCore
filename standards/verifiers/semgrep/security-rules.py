# ruff: noqa: F821
# ok: sec-sql-string-concat
cursor.execute("SELECT * FROM users WHERE email = :email", {"email": email})


# ok: sec-sql-string-concat
db.execute("SELECT * FROM items WHERE id = :id", {"id": item_id})


# ruleid: sec-sql-string-concat
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")


# ruleid: sec-sql-string-concat
cursor.execute("SELECT * FROM users WHERE email = '" + email + "'")


# ruleid: sec-sql-string-concat
db.execute(f"SELECT * FROM items WHERE id = {item_id}")


# ruleid: sec-sql-string-concat
db.execute("SELECT * FROM items WHERE name = '" + name + "'")
