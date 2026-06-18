import sys
import os
import subprocess

BUILTINS = ["echo", "exit", "type", "pwd", "cd"]


def find_executable(command):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:
        full_path = os.path.join(directory, command)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


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

        elif cmd == "pwd":
            print(os.getcwd())

        elif cmd == "cd":
            path = os.path.expanduser(parts[1])

            if os.path.isdir(path):
                os.chdir(path)
            else:
                print(f"cd: {parts[1]}: No such file or directory")

        elif cmd == "type":
            target = parts[1]

            if target in BUILTINS:
                print(f"{target} is a shell builtin")
            else:
                executable = find_executable(target)

                if executable:
                    print(f"{target} is {executable}")
                else:
                    print(f"{target}: not found")

        else:
            executable = find_executable(cmd)

            if executable:
                subprocess.run([cmd] + parts[1:])
            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()