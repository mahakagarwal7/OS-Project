import os
import sys
import shlex
import subprocess

BUILTINS = {"echo", "exit", "type", "pwd", "cd", "jobs"}

job_counter = 1
jobs_list = []


def get_builtin_output(cmd, args):
    out = ""
    err = ""
    if cmd == "echo":
        out = " ".join(args) + "\n"
    elif cmd == "pwd":
        out = os.getcwd() + "\n"
    elif cmd == "cd":
        target = args[0] if args else ""
        if target == "~":
            target = os.environ.get("HOME", "")
        try:
            os.chdir(target)
        except OSError:
            err = f"cd: {target}: No such file or directory\n"
    elif cmd == "jobs":
        out_lines = []
        all_ids = [j["job_id"] for j in jobs_list]
        jobs_to_remove = []
        for job in jobs_list:
            if job["process"].poll() is None:
                if job["job_id"] == max(all_ids): marker = "+"
                elif len(all_ids) >= 2 and job["job_id"] == sorted(all_ids)[-2]: marker = "-"
                else: marker = " "
                out_lines.append(f"[{job['job_id']}]{marker}  {'Running':<24}{job['command']}")
            else:
                if job["job_id"] == max(all_ids): marker = "+"
                elif len(all_ids) >= 2 and job["job_id"] == sorted(all_ids)[-2]: marker = "-"
                else: marker = " "
                c = job["command"]
                if c.endswith(" &"): c = c[:-2]
                out_lines.append(f"[{job['job_id']}]{marker}  {'Done':<24}{c}")
                jobs_to_remove.append(job)
        for job in jobs_to_remove:
            jobs_list.remove(job)
        if out_lines:
            out = "\n".join(out_lines) + "\n"
    elif cmd == "type":
        if args:
            target = args[0]
            if target in BUILTINS:
                out = f"{target} is a shell builtin\n"
            else:
                executable = find_executable(target)
                if executable: out = f"{target} is {executable}\n"
                else: out = f"{target}: not found\n"
    return out, err


def find_executable(command):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        full_path = os.path.join(directory, command)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


while True:
    jobs_to_remove = []

    all_ids = [job["job_id"] for job in jobs_list]

    for job in jobs_list:
        if job["process"].poll() is not None:

            if job["job_id"] == max(all_ids):
                marker = "+"
            elif len(all_ids) >= 2 and job["job_id"] == sorted(all_ids)[-2]:
                marker = "-"
            else:
                marker = " "

            command = job["command"]
            if command.endswith(" &"):
                command = command[:-2]

            print(
                f"[{job['job_id']}]{marker}  "
                f"{'Done':<24}"
                f"{command}"
            )

            jobs_to_remove.append(job)

    for job in jobs_to_remove:
        jobs_list.remove(job)
    sys.stdout.write("$ ")
    sys.stdout.flush()

    try:
        line = input()
    except EOFError:
        break

    if not line.strip():
        continue

    try:
        parts = shlex.split(line)
    except ValueError:
        continue

    background = False

    if parts and parts[-1] == "&":
        background = True
        parts.pop()

    if "|" in parts:
        pipeline_cmds = []
        curr = []
        for p in parts:
            if p == "|":
                pipeline_cmds.append(curr)
                curr = []
            else:
                curr.append(p)
        if curr:
            pipeline_cmds.append(curr)
            
        processes = []
        prev_stdout = None
        
        for i, cmd_parts in enumerate(pipeline_cmds):
            if not cmd_parts:
                continue
                
            cmd_name = cmd_parts[0]
            is_builtin = cmd_name in BUILTINS
            executable = None if is_builtin else find_executable(cmd_name)
            
            if not is_builtin and not executable:
                sys.stderr.write(f"{cmd_name}: command not found\n")
                processes = [] # Abort pipeline
                break
                
            stdout_dest = subprocess.PIPE if i < len(pipeline_cmds) - 1 else None
            
            if is_builtin:
                if cmd_name == "exit":
                    if len(cmd_parts) > 1 and cmd_parts[1] == "0":
                        sys.exit(0)
                    sys.exit(0)
                
                out, err = get_builtin_output(cmd_name, cmd_parts[1:])
                if stdout_dest is not None:
                    r, w = os.pipe()
                    os.write(w, out.encode("utf-8"))
                    os.close(w)
                    if prev_stdout:
                        prev_stdout.close()
                    prev_stdout = os.fdopen(r, "rb")
                else:
                    if out:
                        sys.stdout.write(out)
                        sys.stdout.flush()
                    if err:
                        sys.stderr.write(err)
                        sys.stderr.flush()
                    if prev_stdout:
                        prev_stdout.close()
                    prev_stdout = None
            else:
                try:
                    p = subprocess.Popen(
                        cmd_parts,
                        executable=executable,
                        stdin=prev_stdout,
                        stdout=stdout_dest,
                    )
                    if prev_stdout:
                        prev_stdout.close()
                    processes.append(p)
                    prev_stdout = p.stdout
                except Exception:
                    pass
                
        if processes:
            if background:
                if not jobs_list:
                    job_id = 1
                else:
                    job_id = max(j["job_id"] for j in jobs_list) + 1

                jobs_list.append(
                    {
                        "job_id": job_id,
                        "pid": processes[-1].pid,
                        "process": processes[-1],
                        "command": line,
                    }
                )
                print(f"[{job_id}] {processes[-1].pid}")
            else:
                for p in processes:
                    p.wait()
        continue

    stdout_redirect = None
    stderr_redirect = None
    stdout_append = False
    stderr_append = False

    for op in ["1>>", "2>>", ">>", "2>", "1>", ">"]:
        if op in parts:
            idx = parts.index(op)

            if idx + 1 < len(parts):
                filename = parts[idx + 1]

                if op in [">", "1>"]:
                    stdout_redirect = filename

                elif op in [">>", "1>>"]:
                    stdout_redirect = filename
                    stdout_append = True

                elif op == "2>":
                    stderr_redirect = filename

                elif op == "2>>":
                    stderr_redirect = filename
                    stderr_append = True

            parts = parts[:idx]
            break

    if not parts:
        continue

    cmd = parts[0]
    args = parts[1:]

    if cmd == "exit":
        if args and args[0] == "0":
            sys.exit(0)
        break

    elif cmd == "echo":
        output = " ".join(args) + "\n"

        if stderr_redirect:
            mode = "a" if stderr_append else "w"
            open(stderr_redirect, mode).close()

        if stdout_redirect:
            mode = "a" if stdout_append else "w"
            with open(stdout_redirect, mode) as f:
                f.write(output)
        else:
            sys.stdout.write(output)

    elif cmd == "pwd":
        output = os.getcwd() + "\n"

        if stdout_redirect:
            mode = "a" if stdout_append else "w"
            with open(stdout_redirect, mode) as f:
                f.write(output)
        else:
            sys.stdout.write(output)

    elif cmd == "cd":
        target = args[0] if args else ""

        if target == "~":
            target = os.environ.get("HOME", "")

        try:
            os.chdir(target)

        except FileNotFoundError:
            error_msg = f"cd: {target}: No such file or directory\n"

            if stderr_redirect:
                mode = "a" if stderr_append else "w"
                with open(stderr_redirect, mode) as f:
                    f.write(error_msg)
            else:
                sys.stderr.write(error_msg)

    elif cmd == "jobs":
        jobs_to_remove = []

        active_jobs = [job for job in jobs_list if job["process"].poll() is None]
        active_ids = sorted(job["job_id"] for job in active_jobs)
        all_ids = [j["job_id"] for j in jobs_list]

        for job in jobs_list:
            if job["process"].poll() is None:
                if job["job_id"] == max(all_ids):
                    marker = "+"
                elif len(all_ids) >= 2 and job["job_id"] == sorted(all_ids)[-2]:
                    marker = "-"
                else:
                    marker = " "

                print(
                    f"[{job['job_id']}]{marker}  "
                    f"{'Running':<24}"
                    f"{job['command']}"
                )
            else:
                status = "Done"

                if job["job_id"] == max(all_ids):
                    marker = "+"
                elif len(all_ids) >= 2 and job["job_id"] == sorted(all_ids)[-2]:
                    marker = "-"
                else:
                    marker = " "

                command = job["command"]
                if command.endswith(" &"):
                    command = command[:-2]

                print(
                    f"[{job['job_id']}]{marker}  "
                    f"{status:<24}"
                    f"{command}"
                )

                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            jobs_list.remove(job)

    elif cmd == "type":
        if not args:
            continue

        target = args[0]

        if target in BUILTINS:
            result = f"{target} is a shell builtin"
        else:
            executable = find_executable(target)

            if executable:
                result = f"{target} is {executable}"
            else:
                result = f"{target}: not found"

        if stdout_redirect:
            mode = "a" if stdout_append else "w"
            with open(stdout_redirect, mode) as f:
                f.write(result + "\n")
        else:
            print(result)

    else:
        executable = find_executable(cmd)

        if executable:
            stdout_target = None
            stderr_target = None

            try:
                if stdout_redirect:
                    mode = "a" if stdout_append else "w"
                    stdout_target = open(stdout_redirect, mode)

                if stderr_redirect:
                    mode = "a" if stderr_append else "w"
                    stderr_target = open(stderr_redirect, mode)

                if background:
                    if not jobs_list:
                        job_id = 1
                    else:
                        job_id = max(job["job_id"] for job in jobs_list) + 1

                    process = subprocess.Popen(
                        [cmd] + args,
                        executable=executable,
                        stdout=stdout_target if stdout_target else None,
                        stderr=stderr_target if stderr_target else None,
                    )

                    jobs_list.append(
                        {
                            "job_id": job_id,
                            "pid": process.pid,
                            "process": process,
                            "command": line,
                        }
                    )

                    print(f"[{job_id}] {process.pid}")

                else:
                    subprocess.run(
                        [cmd] + args,
                        executable=executable,
                        stdout=stdout_target if stdout_target else None,
                        stderr=stderr_target if stderr_target else None,
                    )

            except Exception:
                pass

            finally:
                if stdout_target:
                    stdout_target.close()

                if stderr_target:
                    stderr_target.close()

        else:
            error_msg = f"{cmd}: command not found\n"

            if stderr_redirect:
                mode = "a" if stderr_append else "w"
                with open(stderr_redirect, mode) as f:
                    f.write(error_msg)
            else:
                sys.stderr.write(error_msg)