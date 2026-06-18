import sys
import os
import subprocess
import shlex

BUILTINS = ["echo", "exit", "type", "pwd", "cd"]


def find_executable(command):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:
        full_path = os.path.join(directory, command)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def write_output(text, stdout_file=None, append=False):
    if stdout_file:
        mode = "a" if append else "w"

        with open(stdout_file, mode) as f:
            f.write(text + "\n")
    else:
        print(text)


def write_error(text, stderr_file=None, append=False):
    if stderr_file:
        mode = "a" if append else "w"

        with open(stderr_file, mode) as f:
            f.write(text + "\n")
    else:
        print(text)


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input().strip()

        try:
            parts = shlex.split(command)
        except ValueError:
            continue

        if not parts:
            continue

        stdout_file = None
        stderr_file = None
        append_stdout = False
        append_stderr = False

        if ">>" in parts:
            idx = parts.index(">>")
            stdout_file = parts[idx + 1]
            append_stdout = True
            parts = parts[:idx]

        elif "1>>" in parts:
            idx = parts.index("1>>")
            stdout_file = parts[idx + 1]
            append_stdout = True
            parts = parts[:idx]

        elif "2>>" in parts:
            idx = parts.index("2>>")
            stderr_file = parts[idx + 1]
            append_stderr = True
            parts = parts[:idx]

        elif ">" in parts:
            idx = parts.index(">")
            stdout_file = parts[idx + 1]
            parts = parts[:idx]

        elif "1>" in parts:
            idx = parts.index("1>")
            stdout_file = parts[idx + 1]
            parts = parts[:idx]

        elif "2>" in parts:
            idx = parts.index("2>")
            stderr_file = parts[idx + 1]
            parts = parts[:idx]

        if stderr_file and not append_stderr:
            open(stderr_file, "w").close()

        if not parts:
            continue

        cmd = parts[0]

        if cmd == "exit":
            break

        elif cmd == "echo":
            write_output(
                " ".join(parts[1:]),
                stdout_file,
                append_stdout
            )

        elif cmd == "pwd":
            write_output(
                os.getcwd(),
                stdout_file,
                append_stdout
            )

        elif cmd == "cd":
            path = os.path.expanduser(parts[1])

            if os.path.isdir(path):
                os.chdir(path)
            else:
                write_error(
                    f"cd: {parts[1]}: No such file or directory",
                    stderr_file,
                    append_stderr
                )

        elif cmd == "type":
            target = parts[1]

            if target in BUILTINS:
                write_output(
                    f"{target} is a shell builtin",
                    stdout_file,
                    append_stdout
                )
            else:
                executable = find_executable(target)

                if executable:
                    write_output(
                        f"{target} is {executable}",
                        stdout_file,
                        append_stdout
                    )
                else:
                    write_output(
                        f"{target}: not found",
                        stdout_file,
                        append_stdout
                    )

        else:
            executable = find_executable(cmd)

            if executable:

                if stdout_file:
                    mode = "a" if append_stdout else "w"

                    with open(stdout_file, mode) as f:
                        subprocess.run(
                            [cmd] + parts[1:],
                            stdout=f
                        )

                elif stderr_file:
                    mode = "a" if append_stderr else "w"

                    with open(stderr_file, mode) as f:
                        subprocess.run(
                            [cmd] + parts[1:],
                            stderr=f
                        )

                else:
                    subprocess.run([cmd] + parts[1:])

            else:
                write_error(
                    f"{command}: command not found",
                    stderr_file,
                    append_stderr
                )


if __name__ == "__main__":
    main()