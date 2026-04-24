# dbdb/tool.py
import sys

import dbdb


def main(argv):
    if not (3 <= len(argv) <= 5):
        usage()
        return 1

    dbname, command = argv[1:3]
    args = argv[3:]

    db = dbdb.connect(dbname)
    try:
        if command == "get":
            if len(args) != 1:
                usage()
                return 1
            key = args[0]
            sys.stdout.write(db[key])
        elif command == "set":
            if len(args) != 2:
                usage()
                return 1
            key, value = args
            db[key] = value
            db.commit()
        elif command == "commit":
            if len(args) != 0:
                usage()
                return 1
            db.commit()
        elif command == "delete":
            if len(args) != 1:
                usage()
                return 1
            key = args[0]
            try:
                del db[key]
                db.commit()
            except KeyError:
                sys.stderr.write("Key not found\n")
                return 1
        else:
            usage()
            return 1
    finally:
        db.close()

    return 0


def usage():
    sys.stderr.write(
        "Usage: python -m dbdb.tool DBNAME [get KEY | set KEY VALUE | delete KEY]\n"
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
