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
        parts = []
        
        if self.returncode is not None:
            # Case: Git command executed and returned a non-zero exit status
            parts.append(f"Command '{self.cmd_str}' returned non-zero exit status {self.returncode}.")
        else:
            # Case: Error occurred before command execution or during (e.g. timeout)
            main_message = self.args[0]  # The primary message passed to __init__
            parts.append(main_message)
            if self.cmd_str != "Unknown command" and self.cmd_str not in main_message:
                parts.append(f"(Command intended: '{self.cmd_str}')")

        # Common logic for appending stderr/stdout details
        # Ensure stderr/stdout are strings before calling .strip(), or handle if they could be other types.
        # Given subprocess contract with text=True, they should be str or None.
        stderr_content = self.stderr.strip() if isinstance(self.stderr, str) else ""
        stdout_content = self.stdout.strip() if isinstance(self.stdout, str) else ""

        if stderr_content:
            parts.append(f"Git Stderr: '{stderr_content}'")
        elif stdout_content: # Only add stdout if stderr was empty but stdout has content
            parts.append(f"Git Stdout: '{stdout_content}'")
            
        return " ".join(parts)

def pull_updates(repo_dir: str) -> str:
    """
    Pulls updates from the remote repository located at repo_dir.
    Returns stdout of the git pull command on success.
    Raises GitPullFailedError if git pull fails, with detailed stderr.
    """
    git_command = ['git', 'pull']
    cmd_str_display = ' '.join(git_command)

    if not os.path.isdir(repo_dir):
        logger.error(f"Repository directory not found: {repo_dir}")
        raise GitPullFailedError(f"Repository directory not found: {repo_dir}", cmd=git_command)

    logger.info(f"Attempting git pull in directory: '{repo_dir}' with timeout {GIT_OPERATION_TIMEOUT}s. Command: '{cmd_str_display}'")
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
            stderr_msg = process.stderr.strip() if process.stderr else 'N/A'
            stdout_msg = process.stdout.strip() if process.stdout else 'N/A'
            logger.error(
                f"Git pull failed in '{repo_dir}'. RC: {process.returncode}. "
                f"Command: '{cmd_str_display}'. "
                f"Stderr: {stderr_msg}. "
                f"Stdout: {stdout_msg}."
            )
            raise GitPullFailedError(
                message="Git pull operation failed.",
                stderr=process.stderr,
                stdout=process.stdout,
                returncode=process.returncode,
                cmd=git_command
            )
        else:
            logged_stdout = process.stdout.strip() if process.stdout else 'No output.'
            logger.info(f"Git pull successful in '{repo_dir}'. Stdout: {logged_stdout}")
            return process.stdout

    except FileNotFoundError:
        logger.error(f"Git command '{git_command[0]}' not found when trying to pull updates in '{repo_dir}'. Ensure git is installed and in PATH.")
        raise GitPullFailedError(f"Git command '{git_command[0]}' not found. Ensure git is installed and in PATH.", cmd=git_command)
    except subprocess.TimeoutExpired as e:
        stderr_on_timeout = e.stderr.strip() if isinstance(e.stderr, str) and e.stderr else "N/A"
        stdout_on_timeout = e.stdout.strip() if isinstance(e.stdout, str) and e.stdout else "N/A"
        logger.error(
            f"Git pull timed out after {GIT_OPERATION_TIMEOUT} seconds in '{repo_dir}'. Cmd: '{cmd_str_display}'. "
            f"Stderr captured: '{stderr_on_timeout}'. Stdout captured: '{stdout_on_timeout}'."
        )
        raise GitPullFailedError(
            f"Git operation timed out after {GIT_OPERATION_TIMEOUT} seconds.",
            stderr=e.stderr,
            stdout=e.stdout,
            cmd=git_command
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred during git pull in '{repo_dir}'. Cmd: '{cmd_str_display}'")
        raise GitPullFailedError(f"An unexpected error occurred during git pull: {str(e)}", cmd=git_command)
