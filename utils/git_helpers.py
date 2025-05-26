import subprocess
import logging
import os

logger = logging.getLogger(__name__)

# Default timeout for git operations in seconds
GIT_OPERATION_TIMEOUT = 60

class GitPullFailedError(Exception):
    def __init__(self, message, stderr=None, stdout=None, returncode=None, cmd=None):
        super().__init__(message)
        self.stderr = stderr
        self.stdout = stdout
        self.returncode = returncode
        if isinstance(cmd, list):
            self.cmd_str = " ".join(cmd)
        elif cmd is not None:
            self.cmd_str = str(cmd)
        else:
            self.cmd_str = "Unknown command"

    def __str__(self):
        if self.returncode is not None:
            # Case: Git command executed and returned a non-zero exit status
            base_msg = f"Command '{self.cmd_str}' returned non-zero exit status {self.returncode}."
            if self.stderr and self.stderr.strip():
                base_msg += f" Git Stderr: '{self.stderr.strip()}'"
            # Optionally include stdout if it might be useful for diagnostics
            # if self.stdout and self.stdout.strip():
            #     base_msg += f" Git Stdout: '{self.stdout.strip()}'"
            return base_msg
        else:
            # Case: Error occurred before command execution (e.g., dir not found, git not found) or during (e.g. timeout)
            msg = self.args[0]  # The primary message passed to __init__
            if self.cmd_str != "Unknown command" and self.cmd_str not in msg:
                msg = f"{msg} (Command intended: '{self.cmd_str}')"
            
            # Include stderr if available (e.g., from TimeoutExpired)
            if self.stderr and self.stderr.strip():
                msg += f" Git Stderr: '{self.stderr.strip()}'"
            return msg

def pull_updates(repo_dir: str):
    """
    Pulls updates from the remote repository located at repo_dir.
    Raises GitPullFailedError if git pull fails, with detailed stderr.
    """
    git_command = ['git', 'pull']

    if not os.path.isdir(repo_dir):
        logger.error(f"Repository directory not found: {repo_dir}")
        raise GitPullFailedError(f"Repository directory not found: {repo_dir}", cmd=git_command)

    logger.info(f"Attempting git pull in directory: {repo_dir} with timeout {GIT_OPERATION_TIMEOUT}s")
    try:
        process = subprocess.run(
            git_command,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,  # Manually check returncode to customize error
            timeout=GIT_OPERATION_TIMEOUT
        )

        if process.returncode != 0:
            # Log more detailed info for server logs
            logger.error(
                f"Git pull failed in '{repo_dir}'. RC: {process.returncode}. "
                f"Command: '{' '.join(git_command)}'. "
                f"Stderr: {process.stderr.strip() if process.stderr else 'N/A'}. "
                f"Stdout: {process.stdout.strip() if process.stdout else 'N/A'}."
            )
            raise GitPullFailedError(
                message="Git pull operation failed.", # Base message, __str__ provides more detail
                stderr=process.stderr,
                stdout=process.stdout,
                returncode=process.returncode,
                cmd=git_command
            )
        else:
            logger.info(f"Git pull successful in '{repo_dir}'. Stdout: {process.stdout.strip() if process.stdout else 'No output.'}")
            return process.stdout

    except FileNotFoundError:
        logger.error(f"Git command not found when trying to pull updates in '{repo_dir}'. Ensure git is installed and in PATH.")
        raise GitPullFailedError("Git command not found. Ensure git is installed and in PATH.", cmd=git_command)
    except subprocess.TimeoutExpired as e:
        logger.error(f"Git pull timed out after {GIT_OPERATION_TIMEOUT} seconds in '{repo_dir}'. Cmd: '{' '.join(git_command)}'")
        raise GitPullFailedError(
            f"Git operation timed out after {GIT_OPERATION_TIMEOUT} seconds.",
            stderr=e.stderr, # stdout/stderr are strings if text=True, even on TimeoutExpired
            stdout=e.stdout,
            cmd=git_command # returncode will be None
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred during git pull in '{repo_dir}'. Cmd: '{' '.join(git_command)}'")
        raise GitPullFailedError(f"An unexpected error occurred during git pull: {str(e)}", cmd=git_command)
