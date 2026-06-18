import sys

BUILTINS = ["echo", "exit", "type"]


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input().strip()

        parts = command.split()

        if not parts:
            continue

        cmd = parts[0]

        if cmd == "exit":
            break

        elif cmd == "echo":
            print(" ".join(parts[1:]))

        elif cmd == "type":
            target = parts[1]

            if target in BUILTINS:
                print(f"{target} is a shell builtin")
            else:
                print(f"{target}: not found")

        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()